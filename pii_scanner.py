import warnings
import sys
import os
from datetime import datetime, timezone

# Disable all warnings (as suggested by GLiNER owner)
warnings.filterwarnings("ignore")

# Create a more aggressive stdout suppressor
class SuppressStdoutStderr:
    def __init__(self):
        self.null_fds = [os.open(os.devnull, os.O_RDWR) for x in range(2)]
        self.save_fds = [os.dup(1), os.dup(2)]

    def __enter__(self):
        os.dup2(self.null_fds[0], 1)
        os.dup2(self.null_fds[1], 2)

    def __exit__(self, *_):
        os.dup2(self.save_fds[0], 1)
        os.dup2(self.save_fds[1], 2)
        for fd in self.null_fds + self.save_fds:
            os.close(fd)

warnings.filterwarnings("ignore", category=UserWarning)  # General UserWarnings
warnings.filterwarnings("ignore", module="gliner")  # All GLiNER warnings
warnings.filterwarnings("ignore", module="transformers")  # All transformers warnings
warnings.filterwarnings("ignore", message=".*truncate to max_length.*", category=UserWarning)  # Specific truncation warning
warnings.filterwarnings("ignore", message=".*no maximum length is provided.*", category=UserWarning)  # Another form of the warning

os.environ["ONNXRUNTIME_DISABLE_VERSION_WARNING"] = "1"
os.environ["TQDM_DISABLE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"

from docx import Document
from pptx import Presentation
from openpyxl import load_workbook
from gliner import GLiNER
from termcolor import colored
from dotenv import load_dotenv
import argparse
import logging

# Add LOG_LEVEL definition
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.path.join(os.environ.get("PROGRAMDATA", ""), "PII Scanner", "pii_scanner.log")

# Simplify logging setup
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)

# Configure logging with handler
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[handler]
)

logger = logging.getLogger(__name__)

# Disable tqdm progress bars


def get_env_file_path():
    """Get the path to the .env file based on whether running as exe or script"""
    if getattr(sys, 'frozen', False):
        # Running as exe
        return os.path.join(os.path.dirname(sys.executable), '.env')
    else:
        # Running as script
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')

# Load environment variables from .env file
env_path = get_env_file_path()
if os.path.exists(env_path):
    load_dotenv(env_path)
    logger.info(f"Loaded configuration from {env_path}")
else:
    logger.warning(f"No .env file found at {env_path}, using defaults")

def get_application_path():
    """Get the base path for the application, works in both script and exe"""
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        return os.path.dirname(sys.executable)
    else:
        # Running as script
        return os.path.dirname(os.path.abspath(__file__))

# Configuration - Pull from environment variables or use defaults
REPORT_OUTPUT_DIR = os.getenv("REPORT_OUTPUT_DIR", os.path.join(os.environ.get("PROGRAMDATA", ""),
                                           "PII Scanner",
                                           "reports"))
ALLOWED_FILE_TYPES = {".doc", ".docx", ".xlsx", ".pptx", ".txt"}
MAX_CHUNK_LENGTH = int(os.getenv("MAX_CHUNK_LENGTH", "384"))  # Changed default to 384
LITE_SCAN_LIMIT = 1024 * 1024  # 1MB limit for lite scan
PII_MODEL_NAME = os.getenv("PII_MODEL_NAME", "urchade/gliner_multi_pii-v1")

# Default PII labels if not specified in .env
DEFAULT_PII_LABELS = [
    "person", "organization", "phone number", "address", "passport number",
    "email", "credit card number", "social security number"
]

# Load PII labels from environment
PII_LABELS = os.getenv("PII_LABELS", ",".join(DEFAULT_PII_LABELS)).split(",")
PII_LABELS_FULL = os.getenv("PII_LABELS_FULL", ",".join(PII_LABELS)).split(",")

# Print configured labels
print(colored("\nConfigured PII labels:", "cyan"))
print(colored("Basic labels:", "yellow"))
for label in PII_LABELS:
    print(colored(f"  - {label}", "yellow"))

print(colored("\nFull label set available:", "green"))
print(colored(f"  Total labels: {len(PII_LABELS_FULL)}", "green"))

# Add these constants after the existing config section
EXIT_SUCCESS = 0
EXIT_PII_FOUND = 1
EXIT_FILE_NOT_FOUND = 2
EXIT_UNSUPPORTED_FILE = 3
EXIT_REPORT_ERROR = 4
EXIT_CONFIG_ERROR = 5
EXIT_TOKENIZER_INIT_ERROR = 6
EXIT_GLINER_INIT_ERROR = 7
EXIT_NLTK_INIT_ERROR = 8
EXIT_TEXT_EXTRACTION_ERROR = 9
EXIT_TEXT_CHUNKING_ERROR = 10
EXIT_PII_DETECTION_ERROR = 11
EXIT_INVALID_SCAN_TYPE = 12
EXIT_MISSING_PATH = 13
EXIT_GENERAL_ERROR = 99

# Global scan results storage
scan_results = []

def validate_config():
    """Validate configuration and environment setup."""
    try:
        # Ensure required directories exist
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)
        
        # Validate PII model configuration
        if not PII_MODEL_NAME:
            raise ValueError("PII_MODEL_NAME is not configured")
        
        # Validate chunk length
        if MAX_CHUNK_LENGTH <= 0:
            raise ValueError("MAX_CHUNK_LENGTH must be positive")
        
        logger.info("Configuration validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        return False

def store_scan_result(file_path, pii_entities, file_size, file_modified, scan_type):
    """Store scan results in memory for HTML report generation."""
    try:
        scan_result = {
            "file_path": file_path,
            "scan_time": datetime.now(timezone.utc).isoformat(),
            "file_size": file_size,
            "file_modified": file_modified,
            "scan_type": scan_type,
            "pii_entities": pii_entities,
            "pii_count": len(pii_entities) if pii_entities else 0,
            "has_pii": len(pii_entities) > 0 if pii_entities else False
        }
        scan_results.append(scan_result)
        logger.info(f"Scan result stored for: {file_path}")
        
    except Exception as e:
        logger.error(f"Error storing scan result: {e}")
        raise

def generate_html_report(scan_type, scan_path):
    """Generate a comprehensive HTML report of all scan results."""
    try:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
        report_filename = f"pii_scan_report_{scan_type}_{timestamp}.html"
        report_path = os.path.join(REPORT_OUTPUT_DIR, report_filename)
        
        # Calculate summary statistics
        total_files = len(scan_results)
        files_with_pii = sum(1 for result in scan_results if result["has_pii"])
        total_pii_entities = sum(result["pii_count"] for result in scan_results)
        
        # Group PII entities by type
        pii_by_type = {}
        for result in scan_results:
            if result["pii_entities"]:
                for entity in result["pii_entities"]:
                    label = entity["label"]
                    if label not in pii_by_type:
                        pii_by_type[label] = []
                    pii_by_type[label].append({
                        "text": entity["text"],
                        "file": result["file_path"]
                    })
        
        # Generate HTML content
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PII Scan Report - {scan_type.title()} Scan</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            border-bottom: 3px solid #007acc;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #007acc;
            margin: 0;
            font-size: 2.5em;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .summary-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}
        .summary-card h3 {{
            margin: 0 0 10px 0;
            font-size: 1.2em;
        }}
        .summary-card .number {{
            font-size: 2.5em;
            font-weight: bold;
        }}
        .pii-breakdown {{
            margin-bottom: 30px;
        }}
        .pii-type {{
            background: #f8f9fa;
            border-left: 4px solid #007acc;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 5px;
        }}
        .pii-type h3 {{
            color: #007acc;
            margin: 0 0 10px 0;
        }}
        .pii-instance {{
            background: white;
            padding: 10px;
            margin: 5px 0;
            border-radius: 5px;
            border: 1px solid #e9ecef;
        }}
        .file-details {{
            margin-bottom: 30px;
        }}
        .file-card {{
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
        }}
        .file-card.has-pii {{
            border-left: 4px solid #dc3545;
            background: #fff5f5;
        }}
        .file-card.no-pii {{
            border-left: 4px solid #28a745;
            background: #f8fff9;
        }}
        .file-path {{
            font-weight: bold;
            color: #495057;
            margin-bottom: 10px;
        }}
        .file-info {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            font-size: 0.9em;
            color: #6c757d;
        }}
        .pii-entities {{
            margin-top: 10px;
        }}
        .pii-entity {{
            background: white;
            padding: 8px;
            margin: 5px 0;
            border-radius: 5px;
            border: 1px solid #dee2e6;
        }}
        .pii-label {{
            font-weight: bold;
            color: #dc3545;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e9ecef;
            color: #6c757d;
        }}
        .scan-info {{
            background: #e3f2fd;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 PII Scanner Report</h1>
            <p>Generated on {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}</p>
        </div>
        
        <div class="scan-info">
            <h3>📋 Scan Information</h3>
            <p><strong>Scan Type:</strong> {scan_type.title()}</p>
            <p><strong>Scan Path:</strong> {scan_path}</p>
            <p><strong>Report Generated:</strong> {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}</p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>Total Files</h3>
                <div class="number">{total_files}</div>
            </div>
            <div class="summary-card">
                <h3>Files with PII</h3>
                <div class="number">{files_with_pii}</div>
            </div>
            <div class="summary-card">
                <h3>Total PII Entities</h3>
                <div class="number">{total_pii_entities}</div>
            </div>
            <div class="summary-card">
                <h3>Risk Level</h3>
                <div class="number">{'🔴 HIGH' if files_with_pii > 0 else '🟢 LOW'}</div>
            </div>
        </div>
"""
        
        # Add PII breakdown by type
        if pii_by_type:
            html_content += """
        <div class="pii-breakdown">
            <h2>📊 PII Breakdown by Type</h2>
"""
            for pii_type, instances in pii_by_type.items():
                html_content += f"""
            <div class="pii-type">
                <h3>{pii_type.title()} ({len(instances)} instances)</h3>
"""
                for instance in instances:
                    html_content += f"""
                <div class="pii-instance">
                    <strong>Text:</strong> {instance['text']}<br>
                    <strong>File:</strong> {instance['file']}
                </div>
"""
                html_content += """
            </div>
"""
            html_content += """
        </div>
"""
        
        # Add detailed file information
        html_content += """
        <div class="file-details">
            <h2>📁 File Details</h2>
"""
        
        for result in scan_results:
            css_class = "has-pii" if result["has_pii"] else "no-pii"
            status_icon = "🔴" if result["has_pii"] else "🟢"
            status_text = "PII Detected" if result["has_pii"] else "No PII Found"
            
            html_content += f"""
            <div class="file-card {css_class}">
                <div class="file-path">{status_icon} {result['file_path']}</div>
                <div class="file-info">
                    <span><strong>Size:</strong> {result['file_size']:,} bytes</span>
                    <span><strong>Modified:</strong> {result['file_modified']}</span>
                    <span><strong>Scan Type:</strong> {result['scan_type']}</span>
                    <span><strong>Status:</strong> {status_text}</span>
                </div>
"""
            
            if result["has_pii"]:
                html_content += """
                <div class="pii-entities">
                    <strong>PII Entities Found:</strong>
"""
                for entity in result["pii_entities"]:
                    html_content += f"""
                    <div class="pii-entity">
                        <span class="pii-label">{entity['label']}:</span> {entity['text']}
                    </div>
"""
                html_content += """
                </div>
"""
            
            html_content += """
            </div>
"""
        
        html_content += f"""
        </div>
        
        <div class="footer">
            <p>Report generated by PII Scanner for Veeam</p>
            <p>Scan completed at {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}</p>
        </div>
    </div>
</body>
</html>
"""
        
        # Write HTML file
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML report generated successfully: {report_path}")
        print(f"\n📊 HTML Report Generated: {report_path}")
        
        return report_path
        
    except Exception as e:
        logger.error(f"Error generating HTML report: {e}")
        raise

def init_nltk():
    """Initialize NLTK resources."""
    logger.info("NLTK initialization skipped - using GLiNER tokenizer")
    return

# Initialize GLiNER model with proper configuration
try:
    model_config = {
        'max_length': MAX_CHUNK_LENGTH,
        'padding': 'max_length',
        'truncation': True,
        'add_prefix_space': True
    }
    
    gliner_model = GLiNER.from_pretrained(
        PII_MODEL_NAME,
        **model_config
    )
    
    logger.info(f"GLiNER model '{PII_MODEL_NAME}' initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing GLiNER model: {e}")
    gliner_model = None

def extract_text_from_file(file_path, scan_type):
    """Extract text from various file types."""
    try:
        if file_path.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8") as f:
                if scan_type == "lite":
                    return f.read(LITE_SCAN_LIMIT)
                else:
                    return f.read()
                
        elif file_path.endswith((".doc", ".docx")):
            document = Document(file_path)
            text = ""
            for paragraph in document.paragraphs:
                text += paragraph.text + "\n"
                if scan_type == "lite" and len(text.encode('utf-8')) > LITE_SCAN_LIMIT:
                    # Truncate to the limit for lite scans
                    return text[:LITE_SCAN_LIMIT]
            return text
            
        elif file_path.endswith(".xlsx"):
            # Suppress openpyxl warnings during workbook load
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                workbook = load_workbook(file_path)
                text = ""
                for sheet in workbook:
                    for row in sheet.iter_rows():
                        text += " ".join([str(cell.value) if cell.value is not None else "" for cell in row]) + "\n"
                        if scan_type == "lite" and len(text.encode('utf-8')) > LITE_SCAN_LIMIT:
                            # Truncate to the limit for lite scans
                            return text[:LITE_SCAN_LIMIT]
                return text
            
        elif file_path.endswith(".pptx"):
            presentation = Presentation(file_path)
            text = ""
            for slide in presentation.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text += shape.text + "\n"
                    if scan_type == "lite" and len(text.encode('utf-8')) > LITE_SCAN_LIMIT:
                        # Truncate to the limit for lite scans
                        return text[:LITE_SCAN_LIMIT]
            return text
            
        return None
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {e}")
        return None

def chunk_text(text, max_length=MAX_CHUNK_LENGTH):
    """Split text into chunks using GLiNER's words_splitter."""
    try:
        if not text:
            return []
        
        # Get all tokens at once, extract only the token text from tuples
        tokens = [t[0] for t in gliner_model.data_processor.words_splitter(text)]
        
        # Initialize variables for chunking
        chunks = []
        current_chunk = []
        current_length = 0
        
        # Process tokens into chunks
        for token in tokens:
            if current_length + 1 > max_length - 2:  # Account for special tokens
                # Save current chunk
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                # Start new chunk
                current_chunk = [token]
                current_length = 1
            else:
                current_chunk.append(token)
                current_length += 1
        
        # Add the last chunk if not empty
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        logger.debug(f"Split text into {len(chunks)} chunks")
        return chunks
        
    except Exception as e:
        logger.warning(f"Error chunking text: {e}")
        return []

def detect_pii(text, scan_type="full"):
    """Detect PII in text using GLiNER model."""
    try:
        if not gliner_model:
            return []

        labels_to_use = PII_LABELS_FULL if scan_type == "full" else PII_LABELS
        
        # Use the new suppressor
        with SuppressStdoutStderr():
            entities = gliner_model.predict_entities(text, labels_to_use)
        
        formatted_entities = []
        for entity in entities:
            formatted_entities.append({
                "text": entity["text"],
                "label": entity["label"]
            })
            
        return formatted_entities
        
    except Exception as e:
        logger.warning(f"Error detecting PII: {e}")
        return []

def scan_file_for_pii(file_path, scan_type):
    """Scan a file for PII entities."""
    try:
        text = extract_text_from_file(file_path, scan_type)
        if not text:
            logger.error(f"Failed to extract text from {file_path}")
            return []

        chunks = chunk_text(text, MAX_CHUNK_LENGTH)
        all_pii_entities = []

        logger.info(f"Processing chunks for file: {file_path} ({scan_type})")
        for i, chunk in enumerate(chunks):
            logger.debug(f"Processing chunk {i + 1}/{len(chunks)}")
            pii_entities = detect_pii(chunk, scan_type)
            if pii_entities:
                all_pii_entities.extend(pii_entities)

        if all_pii_entities:
            # Get unique labels
            labels = ", ".join(sorted(set(entity['label'] for entity in all_pii_entities)))
            
            # Log detailed message
            log_message = f"PII data potentially exposed in {file_path} ({scan_type}):"
            for entity in all_pii_entities:
                log_message += f"\n  - {entity['label']}: {entity['text']}"
            logger.warning(log_message)
            
            # Print messages for Veeam detection
            print("PII data potentially exposed")  # For Veeam regex match
            print(f"PII_DETECTED: {labels}")  # For structured output
            
        return all_pii_entities
    except Exception as e:
        logger.error(f"Error scanning file {file_path}: {e}")
        # Return empty list instead of exiting to allow scanning to continue
        return []

def process_file(file_path, scan_type):
    """Process a single file for PII scanning."""
    logger.info(f"\nProcessing file: {file_path}")
    
    file_extension = os.path.splitext(file_path)[1].lower()
    if file_extension not in ALLOWED_FILE_TYPES:
        logger.warning(f"Skipping unsupported file type: {file_extension}")
        return

    file_size = os.path.getsize(file_path)
    file_modified = datetime.fromtimestamp(os.path.getmtime(file_path), tz=timezone.utc).isoformat()
    
    logger.info(f"File size: {file_size:,} bytes")
    logger.info(f"File modified: {file_modified}")

    logger.info(f"Scanning file for PII: {file_path} ({scan_type})")
    pii_entities = scan_file_for_pii(file_path, scan_type)

    logger.info("Storing results for HTML report...")
    store_scan_result(file_path, pii_entities, file_size, file_modified, scan_type)

def scan_directory(directory, scan_type):
    """Scan all supported files in a directory."""
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            process_file(file_path, scan_type)

def custom_formatwarning(message, category, filename, lineno, line=None):
    """Custom format for UserWarning, logs it as INFO."""
    logger.info(f"{filename}:{lineno}: {category.__name__}: {message}")
    return ''  # Suppress the original warning

warnings.formatwarning = custom_formatwarning

if __name__ == "__main__":
    try:
        init_nltk()
        
        parser = argparse.ArgumentParser(description="PII Scanner with Lite and Full Scan Options")
        parser.add_argument("path", help="The directory to scan")
        parser.add_argument("--scan-type", choices=["lite", "full"], default="full",
                          help="Specify 'lite' for a quick 1MB scan or 'full' for a complete scan (default: full)")
        parser.add_argument("--verbose", action="store_true", help="Enable verbose logging (DEBUG level)")

        args = parser.parse_args()
        
        if not args.path:
            logger.error("Missing file path argument")
            sys.exit(EXIT_MISSING_PATH)
            
        if args.scan_type not in ["lite", "full"]:
            logger.error("Invalid scan type specified")
            sys.exit(EXIT_INVALID_SCAN_TYPE)

        if args.verbose:
            logger.setLevel(logging.DEBUG)
            logger.debug("Verbose logging enabled")

        # Initialize models
        if gliner_model is None:
            logger.error("Failed to initialize required models")
            sys.exit(EXIT_GLINER_INIT_ERROR)

        # Validate configuration
        if not validate_config():
            sys.exit(EXIT_CONFIG_ERROR)

        # Scan directory using process_file
        pii_found = False
        scan_errors = []
        
        for root, _, files in os.walk(args.path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    if os.path.splitext(file)[1].lower() not in ALLOWED_FILE_TYPES:
                        continue
                        
                    # Use process_file instead of scan_file_for_pii directly
                    process_file(file_path, args.scan_type)
                    
                    # Check if PII was found by checking the stored results
                    for result in scan_results:
                        if result["file_path"] == file_path and result["has_pii"]:
                            pii_found = True
                            break
                        
                except FileNotFoundError:
                    error_msg = f"File not found: {file_path}"
                    logger.error(error_msg)
                    scan_errors.append(error_msg)
                except Exception as e:
                    error_msg = f"Error processing file {file_path}: {e}"
                    logger.error(error_msg)
                    scan_errors.append(error_msg)
                    # Continue scanning other files instead of exiting

        # Report any errors that occurred during scanning
        if scan_errors:
            logger.warning(f"Encountered {len(scan_errors)} errors during scanning:")
            for error in scan_errors:
                logger.warning(f"  - {error}")
            print(f"\n⚠️  {len(scan_errors)} errors occurred during scanning. Check logs for details.")

        # Generate HTML report
        try:
            logger.info("Generating HTML report...")
            report_path = generate_html_report(args.scan_type, args.path)
            logger.info(f"HTML report generated successfully: {report_path}")
        except Exception as e:
            logger.error(f"Error generating HTML report: {e}")
            sys.exit(EXIT_REPORT_ERROR)

        logger.info("Scanning complete.")
        sys.exit(EXIT_PII_FOUND if pii_found else EXIT_SUCCESS)

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(EXIT_GENERAL_ERROR) 