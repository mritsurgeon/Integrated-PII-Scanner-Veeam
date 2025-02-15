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
DB_FILE = os.getenv("DB_FILE", "pii_scan_history.db")
ALLOWED_FILE_TYPES = {".doc", ".docx", ".xlsx", ".pptx", ".txt"}
MODEL_NAME = os.getenv("MODEL_NAME", "roberta-base")
MAX_CHUNK_LENGTH = int(os.getenv("MAX_CHUNK_LENGTH", "400"))
LITE_SCAN_LIMIT = 1024 * 1024  # 1MB limit for lite scan
PII_MODEL_NAME = os.getenv("PII_MODEL_NAME", "urchade/gliner_multi_pii-v1")
PII_LABELS = [
    "person", "email", "phone number", "address", "Social Security Number",
    "credit card number", "passport number", "driver licence", "company"
]

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
    """Initialize the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL UNIQUE,
            scan_time TEXT NOT NULL,
            file_size INTEGER,
            file_modified TEXT,
            file_checksum TEXT,
            scan_type TEXT,
            pii_entities TEXT
        )
    """)
    conn.commit()
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
    """Check if file has already been scanned."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM scan_history
        WHERE file_path = ? AND file_checksum = ? AND scan_type = ?
    """, (file_path, checksum, scan_type))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

def save_scan_result(file_path, pii_entities, file_size, file_modified, file_checksum, scan_type):
    """Save scan results to database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    try:
        cursor.execute("""
            INSERT INTO scan_history 
            (file_path, scan_time, file_size, file_modified, file_checksum, scan_type, pii_entities)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (file_path, now, file_size, file_modified, file_checksum, scan_type, str(pii_entities)))
        conn.commit()
    except sqlite3.IntegrityError:
        print(colored(f"File already exists in database: {file_path} with scan type {scan_type}", "yellow"))
    finally:
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

def detect_pii(text):
    """Detect PII in text using GLiNER model."""
    try:
        if not gliner_model:
            return []

        # Process text with GLiNER
        entities = gliner_model.predict_entities(text, PII_LABELS)
        
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
            pii_entities = detect_pii(chunk)
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
    file_extension = os.path.splitext(file_path)[1].lower()
    if file_extension not in ALLOWED_FILE_TYPES:
        return

    file_size = os.path.getsize(file_path)
    file_modified = datetime.fromtimestamp(os.path.getmtime(file_path), tz=timezone.utc).isoformat()
    file_checksum = calculate_checksum(file_path, scan_type)

    if file_checksum is None:
        print(colored(f"Skipping {file_path} due to checksum error.", "red"))
        return

    if is_file_scanned(file_path, file_checksum, scan_type):
        print(colored(f"Skipping already scanned file: {file_path} ({scan_type})", "yellow"))
        return

    print(colored(f"Scanning file: {file_path} ({scan_type})", "cyan"))
    pii_entities = scan_file_for_pii(file_path, scan_type)

    if pii_entities:
        print(colored(f"Found PII in {file_path} ({scan_type}): {pii_entities}", "red"))
    else:
        print(colored(f"No PII found in {file_path} ({scan_type})", "green"))

    save_scan_result(file_path, pii_entities, file_size, file_modified, file_checksum, scan_type)

def scan_directory(directory, scan_type):
    """Scan all supported files in a directory."""
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            process_file(file_path, scan_type)

if __name__ == "__main__":
    try:
        # Initialize NLTK
        init_nltk()
        
        # Parse arguments
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

        # Initialize database
        try:
            init_db()
        except Exception as e:
            print(colored(f"Database initialization error: {e}", "red"))
            sys.exit(EXIT_DB_ERROR)

        # Initialize tokenizer
        if tokenizer is None:
            print(colored("Failed to initialize tokenizer", "red"))
            sys.exit(EXIT_TOKENIZER_INIT_ERROR)

        # Initialize GLiNER model
        if gliner_model is None:
            print(colored("Failed to initialize GLiNER model", "red"))
            sys.exit(EXIT_GLINER_INIT_ERROR)

        # Scan directory
        pii_found = False
        for root, _, files in os.walk(args.path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    if os.path.splitext(file)[1].lower() not in ALLOWED_FILE_TYPES:
                        continue
                        
                    pii_entities = scan_file_for_pii(file_path, args.scan_type)
                    if pii_entities:
                        pii_found = True
                        
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