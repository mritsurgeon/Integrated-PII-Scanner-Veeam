import os
import sys
import sqlite3
import hashlib
from datetime import datetime, timezone
from docx import Document
from pptx import Presentation
from openpyxl import load_workbook
from transformers import RobertaTokenizer
from gliner import GLiNER
from termcolor import colored
from dotenv import load_dotenv
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from tqdm import tqdm
import argparse
import torch

# Load environment variables from .env file
load_dotenv()

# Configuration - Pull from environment variables or use defaults
DB_FILE = os.path.abspath(os.getenv("DB_FILE", "pii_scan_history.db"))
ALLOWED_FILE_TYPES = {".doc", ".docx", ".xlsx", ".pptx", ".txt"}
MODEL_NAME = os.getenv("MODEL_NAME", "roberta-base")
MAX_CHUNK_LENGTH = int(os.getenv("MAX_CHUNK_LENGTH", "400"))
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
EXIT_DB_ERROR = 4
EXIT_TOKENIZER_INIT_ERROR = 5
EXIT_GLINER_INIT_ERROR = 6
EXIT_NLTK_INIT_ERROR = 7
EXIT_CHECKSUM_ERROR = 8
EXIT_TEXT_EXTRACTION_ERROR = 9
EXIT_TEXT_CHUNKING_ERROR = 10
EXIT_PII_DETECTION_ERROR = 11
EXIT_INVALID_SCAN_TYPE = 12
EXIT_MISSING_PATH = 13
EXIT_GENERAL_ERROR = 99

def init_nltk():
    """Initialize NLTK resources."""
    try:
        nltk.data.find('tokenizers/punkt_tab/english')
        print(colored("NLTK punkt_tab already installed.", "green"))
    except LookupError:
        try:
            print(colored("Downloading NLTK punkt_tab...", "yellow"))
            nltk.download('punkt_tab')
            nltk.data.find('tokenizers/punkt_tab/english')
            print(colored("NLTK punkt_tab downloaded successfully.", "green"))
        except Exception as e:
            print(colored(f"Failed to initialize NLTK: {e}", "red"))
            sys.exit(EXIT_NLTK_INIT_ERROR)

# Initialize tokenizer
try:
    tokenizer = RobertaTokenizer.from_pretrained(MODEL_NAME)
    tokenizer.add_prefix_space = True
    print(colored(f"Tokenizer '{MODEL_NAME}' initialized successfully.", "green"))
except Exception as e:
    print(colored(f"Error initializing tokenizer: {e}", "red"))
    tokenizer = None

# Initialize GLiNER model
try:
    gliner_model = GLiNER.from_pretrained(PII_MODEL_NAME)
    print(colored(f"GLiNER model '{PII_MODEL_NAME}' initialized successfully.", "green"))
except Exception as e:
    print(colored(f"Error initializing GLiNER model: {e}", "red"))
    gliner_model = None

def init_db():
    """Initialize the SQLite database with proper error handling."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Drop existing table if it exists
        cursor.execute("DROP TABLE IF EXISTS scan_history")
        
        # Create the scan_history table with proper constraints
        cursor.execute("""
            CREATE TABLE scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                scan_time TEXT NOT NULL,
                file_size INTEGER,
                file_modified TEXT,
                file_checksum TEXT NOT NULL,
                scan_type TEXT CHECK(scan_type IN ('lite', 'full')),
                pii_entities TEXT,
                UNIQUE(file_checksum, scan_type)
            )
        """)
        
        # Add index on checksum for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_checksum_type 
            ON scan_history(file_checksum, scan_type)
        """)
        
        conn.commit()
        print(colored("Database initialized successfully at: " + DB_FILE, "green"))
        
    except sqlite3.Error as e:
        print(colored(f"Database initialization error: {e}", "red"))
        print(colored(f"Error details: {str(e)}", "red"))
        if conn:
            conn.rollback()
        sys.exit(EXIT_DB_ERROR)
    finally:
        if conn:
            conn.close()

def calculate_checksum(file_path, scan_type):
    """Calculate SHA256 checksum of a file."""
    hasher = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            if scan_type == "lite":
                chunk = f.read(LITE_SCAN_LIMIT)
                hasher.update(chunk)
            else:
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        print(colored(f"Error calculating checksum for {file_path}: {e}", "red"))
        return None

def is_file_scanned(file_path, checksum, scan_type):
    """Check if file has been scanned with improved error handling."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # First check by checksum only
        cursor.execute("""
            SELECT file_path, scan_time 
            FROM scan_history
            WHERE file_checksum = ? AND scan_type = ?
        """, (checksum, scan_type))
        
        result = cursor.fetchone()
        
        if result:
            original_path, last_scan = result
            print(colored(f"File content already scanned on {last_scan}", "yellow"))
            print(colored(f"Original file: {original_path}", "yellow"))
            print(colored(f"Current file: {file_path}", "yellow"))
            return True
            
        return False
        
    except sqlite3.Error as e:
        print(colored(f"Database error while checking scan history: {e}", "red"))
        raise
    finally:
        if conn:
            conn.close()

def save_scan_result(file_path, pii_entities, file_size, file_modified, file_checksum, scan_type):
    """Save scan results to database with improved error handling."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        
        # Validate inputs
        if not isinstance(file_size, int):
            file_size = int(file_size)
        
        if not scan_type in ['lite', 'full']:
            raise ValueError(f"Invalid scan_type: {scan_type}")
            
        if not file_checksum:
            raise ValueError("file_checksum cannot be None")
            
        # Print debug info
        print(colored(f"Saving scan result:", "cyan"))
        print(colored(f"  Path: {file_path}", "cyan"))
        print(colored(f"  Checksum: {file_checksum}", "cyan"))
        print(colored(f"  Scan type: {scan_type}", "cyan"))
            
        # Insert or update the scan result
        cursor.execute("""
            INSERT OR REPLACE INTO scan_history 
            (file_path, scan_time, file_size, file_modified, file_checksum, scan_type, pii_entities)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (file_path, now, file_size, file_modified, file_checksum, scan_type, str(pii_entities)))
        
        conn.commit()
        print(colored(f"Scan result saved for: {file_path}", "green"))
        
    except sqlite3.Error as e:
        print(colored(f"Database error while saving scan result: {e}", "red"))
        print(colored(f"Error details: {str(e)}", "red"))
        if conn:
            conn.rollback()
        raise
    except ValueError as e:
        print(colored(f"Invalid data error: {e}", "red"))
        raise
    finally:
        if conn:
            conn.close()

def extract_text_from_file(file_path, scan_type):
    """Extract text from various file types."""
    try:
        if file_path.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read(LITE_SCAN_LIMIT) if scan_type == "lite" else f.read()
                
        elif file_path.endswith((".doc", ".docx")):
            document = Document(file_path)
            text = ""
            for paragraph in document.paragraphs:
                text += paragraph.text + "\n"
                if scan_type == "lite" and len(text.encode('utf-8')) > LITE_SCAN_LIMIT:
                    return text[:LITE_SCAN_LIMIT].decode('utf-8', 'ignore')
            return text
            
        elif file_path.endswith(".xlsx"):
            workbook = load_workbook(file_path)
            text = ""
            for sheet in workbook:
                for row in sheet.iter_rows():
                    text += " ".join([str(cell.value) if cell.value is not None else "" for cell in row]) + "\n"
                    if scan_type == "lite" and len(text.encode('utf-8')) > LITE_SCAN_LIMIT:
                        return text[:LITE_SCAN_LIMIT].decode('utf-8', 'ignore')
            return text
            
        elif file_path.endswith(".pptx"):
            presentation = Presentation(file_path)
            text = ""
            for slide in presentation.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text += shape.text + "\n"
                    if scan_type == "lite" and len(text.encode('utf-8')) > LITE_SCAN_LIMIT:
                        return text[:LITE_SCAN_LIMIT].decode('utf-8', 'ignore')
            return text
            
        return None
    except Exception as e:
        print(colored(f"Error extracting text from {file_path}: {e}", "red"))
        return None

def chunk_text(text, max_length=400):
    """Split text into chunks using RoBERTa tokenizer."""
    try:
        if not text:
            return []
        
        tokens = tokenizer.tokenize(text)
        chunks = []
        
        for i in range(0, len(tokens), max_length):
            chunk_tokens = tokens[i:i + max_length]
            chunk_text = tokenizer.convert_tokens_to_string(chunk_tokens)
            chunks.append(chunk_text)
        
        print(colored(f"Split text into {len(chunks)} chunks", "blue"))
        for i, chunk in enumerate(chunks):
            chunk_tokens = tokenizer.tokenize(chunk)
            print(colored(f"Chunk {i+1} length: {len(chunk_tokens)} tokens", "cyan"))
        
        return chunks
    except Exception as e:
        print(colored(f"Error chunking text: {e}", "red"))
        try:
            tokens = tokenizer.tokenize(text)
            return [tokenizer.convert_tokens_to_string(tokens[:max_length])]
        except Exception as e:
            print(colored(f"Fallback chunking failed: {e}", "red"))
            return [text[:max_length]]

def detect_pii(text, scan_type="full"):
    """Detect PII in text using GLiNER model."""
    try:
        if not gliner_model:
            return []

        # Use full label set for full scans, basic set for lite scans
        labels_to_use = PII_LABELS_FULL if scan_type == "full" else PII_LABELS
        
        # Process text with GLiNER
        entities = gliner_model.predict_entities(text, labels_to_use)
        
        # Convert entities to standard format
        formatted_entities = []
        for entity in entities:
            formatted_entities.append({
                "text": entity["text"],
                "label": entity["label"]
            })
            
        return formatted_entities
        
    except Exception as e:
        print(colored(f"Error detecting PII: {e}", "yellow"))
        return []

def scan_file_for_pii(file_path, scan_type):
    """Scan a file for PII entities."""
    try:
        text = extract_text_from_file(file_path, scan_type)
        if not text:
            print(colored(f"Failed to extract text from {file_path}", "red"))
            return []

        chunks = chunk_text(text, MAX_CHUNK_LENGTH)
        all_pii_entities = []

        print(colored(f"Processing chunks for file: {file_path} ({scan_type})", "green"))
        for i, chunk in enumerate(chunks):
            print(colored(f"Chunk {i + 1}: {chunk[:50]}...", "yellow"))
            pii_entities = detect_pii(chunk, scan_type)
            if pii_entities:
                all_pii_entities.extend(pii_entities)

        if all_pii_entities:
            print(colored(f"Found PII in {file_path} ({scan_type}): {all_pii_entities}", "red"))
            print("PII data potentially exposed")  # Required for Veeam detection
            
        return all_pii_entities
    except Exception as e:
        print(colored(f"Error scanning file {file_path}: {e}", "red"))
        sys.exit(EXIT_PII_DETECTION_ERROR)

def process_file(file_path, scan_type):
    """Process a single file for PII scanning."""
    print(colored(f"\nProcessing file: {file_path}", "cyan"))
    
    file_extension = os.path.splitext(file_path)[1].lower()
    if file_extension not in ALLOWED_FILE_TYPES:
        print(colored(f"Skipping unsupported file type: {file_extension}", "yellow"))
        return

    file_size = os.path.getsize(file_path)
    file_modified = datetime.fromtimestamp(os.path.getmtime(file_path), tz=timezone.utc).isoformat()
    
    print(colored("Calculating checksum...", "cyan"))
    file_checksum = calculate_checksum(file_path, scan_type)

    if file_checksum is None:
        print(colored(f"Skipping {file_path} due to checksum error.", "red"))
        return

    print(colored(f"Checksum: {file_checksum}", "cyan"))

    if is_file_scanned(file_path, file_checksum, scan_type):
        print(colored(f"Skipping already scanned file: {file_path} ({scan_type})", "yellow"))
        return

    print(colored(f"Scanning file for PII: {file_path} ({scan_type})", "cyan"))
    pii_entities = scan_file_for_pii(file_path, scan_type)

    print(colored("Saving results to database...", "cyan"))
    save_scan_result(file_path, pii_entities, file_size, file_modified, file_checksum, scan_type)

def scan_directory(directory, scan_type):
    """Scan all supported files in a directory."""
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            process_file(file_path, scan_type)

# Add a function to verify database
def verify_database():
    """Verify database exists and is properly initialized."""
    conn = None
    try:
        if not os.path.exists(DB_FILE):
            print(colored(f"Database file not found at: {DB_FILE}", "yellow"))
            init_db()
            return
            
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='scan_history'
        """)
        
        if not cursor.fetchone():
            print(colored("Database exists but missing required table.", "yellow"))
            if conn:
                conn.close()
            init_db()
        else:
            print(colored("Database verified successfully.", "green"))
            
    except sqlite3.Error as e:
        print(colored(f"Database verification error: {e}", "red"))
        sys.exit(EXIT_DB_ERROR)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    try:
        verify_database()
        init_nltk()
        
        parser = argparse.ArgumentParser(description="PII Scanner with Lite and Full Scan Options")
        parser.add_argument("path", help="The directory to scan")
        parser.add_argument("--scan-type", choices=["lite", "full"], default="full",
                          help="Specify 'lite' for a quick 1MB scan or 'full' for a complete scan (default: full)")

        args = parser.parse_args()
        
        if not args.path:
            print(colored("Missing file path argument", "red"))
            sys.exit(EXIT_MISSING_PATH)
            
        if args.scan_type not in ["lite", "full"]:
            print(colored("Invalid scan type specified", "red"))
            sys.exit(EXIT_INVALID_SCAN_TYPE)

        # Initialize models
        if tokenizer is None or gliner_model is None:
            print(colored("Failed to initialize required models", "red"))
            sys.exit(EXIT_TOKENIZER_INIT_ERROR)

        # Scan directory using process_file
        pii_found = False
        for root, _, files in os.walk(args.path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    if os.path.splitext(file)[1].lower() not in ALLOWED_FILE_TYPES:
                        continue
                        
                    # Use process_file instead of scan_file_for_pii directly
                    process_file(file_path, args.scan_type)
                    
                    # Check if PII was found by querying the database
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT pii_entities 
                        FROM scan_history 
                        WHERE file_path = ? AND scan_type = ?
                    """, (file_path, args.scan_type))
                    
                    result = cursor.fetchone()
                    if result and result[0] != '[]':
                        pii_found = True
                    
                    conn.close()
                        
                except FileNotFoundError:
                    print(colored(f"File not found: {file_path}", "red"))
                    sys.exit(EXIT_FILE_NOT_FOUND)
                except Exception as e:
                    print(colored(f"Error processing file {file_path}: {e}", "red"))
                    sys.exit(EXIT_GENERAL_ERROR)

        print(colored("Scanning complete.", "green"))
        sys.exit(EXIT_PII_FOUND if pii_found else EXIT_SUCCESS)

    except Exception as e:
        print(colored(f"An error occurred: {e}", "red"))
        sys.exit(EXIT_GENERAL_ERROR) 