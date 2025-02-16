# PII Scanner for Veeam

A Python-based PII (Personally Identifiable Information) scanner that integrates with Veeam backup solutions. This tool scans various document types for potential PII data exposure using the GLiNER model for accurate detection.

## Overview

The PII Scanner is designed to:
- Detect sensitive information in backup documents
- Integrate seamlessly with Veeam backup solutions
- Support multiple document formats
- Provide both quick and thorough scanning options
- Track scan history and avoid duplicate scans
- Prevent rescanning identical content using checksums

## Features

### Scan Types
- **Full Scan**: Complete document analysis with extended PII detection
- **Lite Scan**: Quick 1MB scan for large files with basic PII detection

### Supported File Types
- Microsoft Word (.doc, .docx)
- Microsoft Excel (.xlsx)
- Microsoft PowerPoint (.pptx)
- Text files (.txt)

### PII Detection Capabilities
Using the GLiNER model, detects:
- Person names
- Email addresses
- Phone numbers
- Physical addresses
- Social Security Numbers
- Credit card numbers
- Passport numbers
- Driver licenses
- Company names
- And many more (see configuration)

### Database Features
- SQLite database for scan history
- Checksum-based duplicate detection
- Scan results tracking
- Support for multiple scan types per file

## Installation & Setup

### Requirements
- Python 3.8 or higher
- pip (Python package installer)
- Internet connection for initial model download
- Sufficient disk space for models and database

### Python Installation
```bash
# Clone repository
git clone https://github.com/mritsurgeon/Integrated-PII-Scanner-Veeam.git
cd Integrated-PII-Scanner-Veeam

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### Configuration
1. Copy example environment file:
```bash
cp .env.example .env
```

2. Configure environment variables in `.env`:
```bash
# Database configuration
DB_FILE=pii_scan_history.db

# Model configuration
MODEL_NAME=roberta-base
PII_MODEL_NAME=urchade/gliner_multi_pii-v1
MAX_CHUNK_LENGTH=400

# Basic PII Labels (for lite scans)
PII_LABELS=person,organization,phone number,address,passport number,email,credit card number,social security number

# Extended PII Labels (for full scans)
PII_LABELS_FULL=person,organization,phone number,address,passport number,email,credit card number,social security number,health insurance id number,date of birth,mobile phone number,bank account number,medication,cpf,driver's license number,tax identification number,medical condition,identity card number,national id number,ip address,email address,iban,credit card expiration date,username,health insurance number,registration number,student id number,insurance number,flight number,landline phone number,blood type,cvv,reservation number,digital signature,social media handle,license plate number,cnpj,postal code,passport_number,serial number,vehicle registration number,credit card brand,fax number,visa number,insurance company,identity document number,transaction number,national health insurance number,cvc,birth certificate number,train ticket number,passport expiration date,social_security_number
```

## Veeam Integration

### Executable Creation
```bash
# Install PyInstaller
pip install pyinstaller

# Create executable (with embedded config)
pyinstaller --onefile --add-data ".env:." pii_scanner.py

# OR for external configuration (recommended)
pyinstaller --onefile pii_scanner.py
```

### Installation Steps
1. Create directories:
```bash
mkdir "C:\Program Files\PII Scanner"
mkdir "C:\ProgramData\PII Scanner"
```

2. Copy files:
```bash
copy dist\pii_scanner.exe "C:\Program Files\PII Scanner\"
copy .env "C:\Program Files\PII Scanner\"
copy pii_scanner.xml "C:\Program Files\Veeam\Backup and Replication\<version>\AntivirusConf\"
```

3. Update `.env` for production:
```bash
DB_FILE=C:\ProgramData\PII Scanner\pii_scan_history.db
```

### XML Configuration
```xml
<?xml version="1.0" encoding="utf-8"?>
<Antiviruses>
  <AntivirusInfo 
    Name="PII Scanner" 
    IsPortableSoftware="true" 
    ExecutableFilePath="C:\Program Files\PII Scanner\pii_scanner.exe" 
    CommandLineParameters="%Path% --scan-type full" 
    ThreatExistsRegEx="PII data potentially exposed" 
    IsParallelScanAvailable="false">
    <ExitCodes>
      <ExitCode Type="Success" Description="No PII found">0</ExitCode>
      <ExitCode Type="Warning" Description="PII data found">1</ExitCode>
      <ExitCode Type="Error" Description="File not found">2</ExitCode>
      <ExitCode Type="Error" Description="Unsupported file">3</ExitCode>
      <ExitCode Type="Error" Description="Database error">4</ExitCode>
      <ExitCode Type="Error" Description="Model initialization failed">5</ExitCode>
    </ExitCodes>
  </AntivirusInfo>
</Antiviruses>
```

## Technical Reference

### Command Line Arguments
```bash
Usage: pii_scanner.exe [OPTIONS] PATH

Arguments:
  PATH                  Directory or file to scan

Options:
  --scan-type [lite|full]  Scan type (default: full)
                          lite: Quick 1MB scan with basic PII detection
                          full: Complete scan with extended PII detection
```

### Exit Codes
| Code | Type | Description |
|------|------|-------------|
| 0 | Success | No PII found |
| 1 | Warning | PII data found |
| 2 | Error | File not found |
| 3 | Error | Unsupported file type |
| 4 | Error | Database error |
| 5 | Error | Tokenizer initialization failed |
| 6 | Error | GLiNER model initialization failed |
| 7 | Error | NLTK initialization failed |
| 8 | Error | Checksum calculation failed |
| 9 | Error | Text extraction failed |
| 10 | Error | Text chunking failed |
| 11 | Error | PII detection failed |
| 12 | Error | Invalid scan type |
| 13 | Error | Missing file path |
| 99 | Error | General exception |

### Database Schema
```sql
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
);
```

### Troubleshooting

#### Common Issues
1. **Model Download Failures**
   - Check internet connectivity
   - Verify disk space
   - Ensure write permissions

2. **Database Errors**
   - Check write permissions
   - Verify SQLite functionality
   - Ensure sufficient disk space

3. **File Access Issues**
   - Verify file permissions
   - Check file paths
   - Confirm file format support

#### Console Output Colors
- **Green**: Success messages
- **Yellow**: Warnings and progress
- **Red**: Errors and PII detection
- **Blue/Cyan**: Processing information

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact

For questions or support, please contact:
- GitHub: [mritsurgeon](https://github.com/mritsurgeon)
- Project: [Integrated-PII-Scanner-Veeam](https://github.com/mritsurgeon/Integrated-PII-Scanner-Veeam)

## Acknowledgments

- GLiNER model by urchade for PII detection
- Veeam Software for integration capabilities
- RoBERTa tokenizer for text processing

