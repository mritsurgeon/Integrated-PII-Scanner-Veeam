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

### Database Features
- SQLite database for scan history
- Checksum-based duplicate detection
- Scan results tracking
- Support for multiple scan types per file

## Installation

1. Clone the repository:
```bash
git clone https://github.com/mritsurgeon/Integrated-PII-Scanner-Veeam.git
cd Integrated-PII-Scanner-Veeam
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your settings
```

## Configuration

### Environment Variables (.env)
```bash
# Database configuration
DB_FILE=pii_scan_history.db

# Model configuration
MODEL_NAME=roberta-base
PII_MODEL_NAME=urchade/gliner_multi_pii-v1
MAX_CHUNK_LENGTH=400

# Basic PII Labels (comma-separated, used for lite scans)
PII_LABELS=person,organization,phone number,address,passport number,email,credit card number,social security number

# Extended PII Labels (comma-separated, used for full scans)
PII_LABELS_FULL=person,organization,phone number,address,passport number,email,credit card number,social security number,health insurance id number,date of birth,mobile phone number,bank account number,medication,cpf,driver's license number,tax identification number,medical condition,identity card number,national id number,ip address,email address,iban,credit card expiration date,username,health insurance number,registration number,student id number,insurance number,flight number,landline phone number,blood type,cvv,reservation number,digital signature,social media handle,license plate number,cnpj,postal code,passport_number,serial number,vehicle registration number,credit card brand,fax number,visa number,insurance company,identity document number,transaction number,national health insurance number,cvc,birth certificate number,train ticket number,passport expiration date,social_security_number
```

### Executable Creation for Veeam
The scanner needs to be packaged as an executable with its configuration for Veeam integration:

1. Create the executable with embedded configuration:
```bash
# Install PyInstaller
pip install pyinstaller

# Create executable with embedded .env
pyinstaller --onefile --add-data ".env:." pii_scanner.py

# For external configuration (recommended)
pyinstaller --onefile pii_scanner.py
```

2. Configure external database and settings:
- Place `pii_scan_history.db` in a persistent location
- Create `.env` file in the same directory as the executable
- Update DB_FILE path in `.env` to point to the persistent database location

3. Test the executable:
```bash
# Test with internal config
./dist/pii_scanner.exe /path/to/scan --scan-type full

# Test with external config
copy .env dist/
cd dist
./pii_scanner.exe /path/to/scan --scan-type full
```

### Veeam SureBackup Integration

1. XML Configuration (pii_scanner.xml):
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

2. Installation for Veeam:
```bash
# Create installation directory
mkdir "C:\Program Files\PII Scanner"

# Copy files
copy dist\pii_scanner.exe "C:\Program Files\PII Scanner\"
copy .env "C:\Program Files\PII Scanner\"
copy pii_scanner.xml "C:\Program Files\Veeam\Backup and Replication\<version>\AntivirusConf\"

# Create persistent database directory
mkdir "C:\ProgramData\PII Scanner"
```

3. Update `.env` for production:
```bash
# Update DB_FILE to persistent location
DB_FILE=C:\ProgramData\PII Scanner\pii_scan_history.db
```

### Command Line Arguments
The executable supports the following arguments:

```bash
Usage: pii_scanner.exe [OPTIONS] PATH

Arguments:
  PATH                  Directory or file to scan

Options:
  --scan-type [lite|full]  Scan type (default: full)
                          lite: Quick 1MB scan with basic PII detection
                          full: Complete scan with extended PII detection
```

These arguments are used by Veeam in the XML configuration's CommandLineParameters.

## Exit Codes
| Code | Description |
|------|-------------|
| 0 | Success - No PII found |
| 1 | Warning - PII found |
| 2 | Error - File not found |
| 3 | Error - Unsupported file |
| 4 | Error - Database error |
| ... | ... |

## License
MIT License - See LICENSE file

## Contact
- GitHub: [mritsurgeon](https://github.com/mritsurgeon)
- Project: [Integrated-PII-Scanner-Veeam](https://github.com/mritsurgeon/Integrated-PII-Scanner-Veeam)

## High-Level Process Flow

1. **Initialization**
   - Load environment configuration
   - Initialize database
   - Set up NLTK and models
   - Verify dependencies

2. **Scanning Process**
   - Mount backup through Veeam
   - Scan files based on type (lite/full)
   - Detect PII using GLiNER model
   - Store results in SQLite database
   - Return status to Veeam

3. **Results Processing**
   - Store scan history
   - Track file changes via checksums
   - Report PII findings
   - Maintain audit trail

## Features

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

### Additional Features
- Colored console output for better visibility
- Progress tracking during scans
- Configurable via environment variables
- Exit codes for Veeam integration

## Requirements

- Python 3.8 or higher
- pip (Python package installer)
- Internet connection for initial model download
- Sufficient disk space for models and database
- Required Python packages (see requirements.txt)

## Installation

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

# Configure environment
cp .env.example .env
# Edit .env with your settings
```

### Executable Creation for Veeam
```bash
# Install PyInstaller
pip install pyinstaller

# Create executable
pyinstaller --onefile --add-data ".env:." pii_scanner.py
```

The executable will be created in `dist/pii_scanner.exe`

## Configuration

### Environment Configuration (.env)
```bash
# Database configuration
DB_FILE=pii_scan_history.db

# Model configuration
MODEL_NAME=roberta-base
PII_MODEL_NAME=urchade/gliner_multi_pii-v1
MAX_CHUNK_LENGTH=400

# PII Labels Configuration
PII_LABELS=person,organization,phone number,address,passport number,email,credit card number,social security number

# Full PII Labels Set (used in full scans)
PII_LABELS_FULL=person,organization,phone number,address,passport number,email,credit card number,social security number,health insurance id number,...
```

### Veeam Integration (pii_scanner.xml)
```xml
<?xml version="1.0" encoding="utf-8"?>
<Antiviruses>
  <AntivirusInfo Name='PII Scanner' 
    IsPortableSoftware='true' 
    ExecutableFilePath='<FULL_PATH_TO_SCRIPT>\pii_scanner.exe' 
    CommandLineParameters='%Path% --scan-type full' 
    ThreatExistsRegEx='PII data potentially exposed' 
    IsParallelScanAvailable='false'>
    <ExitCodes>
      <ExitCode Type='Success' Description='No PII found'>0</ExitCode>
      <ExitCode Type='Warning' Description='PII data found'>1</ExitCode>
      <!-- Additional exit codes -->
    </ExitCodes>
  </AntivirusInfo>
</Antiviruses>
```

### Command Line Arguments
```bash
# Full scan
pii_scanner.exe /path/to/scan --scan-type full

# Lite scan (1MB limit)
pii_scanner.exe /path/to/scan --scan-type lite

# Default (full scan)
pii_scanner.exe /path/to/scan
```

## SQLite Database

### Database Structure
```sql
CREATE TABLE scan_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    scan_time TEXT NOT NULL,
    file_size INTEGER,
    file_modified TEXT,
    file_checksum TEXT,
    scan_type TEXT CHECK(scan_type IN ('lite', 'full')),
    pii_entities TEXT,
    UNIQUE(file_path, scan_type)
);
```

### Querying Results
```sql
-- Find files with PII
SELECT file_path, scan_time, pii_entities 
FROM scan_history 
WHERE pii_entities != '[]';

-- Get scan statistics
SELECT scan_type, COUNT(*) as count 
FROM scan_history 
GROUP BY scan_type;
```

### Visualization Options
- Connect to PowerBI via SQLite connector
- Use DB Browser for SQLite for direct visualization
- Export to CSV for custom reporting

## Scan Types

### Full Scan
- Scans entire file content
- Checks for all configured PII types
- More thorough but slower
- Uses PII_LABELS_FULL configuration

### Lite Scan
- Scans first 1MB of files
- Checks basic PII types only
- Faster but less thorough
- Uses basic PII_LABELS configuration

## Exit Codes
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

## Veeam Integration

1. Copy the XML configuration:
```bash
cp pii_scanner.xml <veeam-config-directory>
```

2. Update XML configuration:
```xml
<AntivirusInfo Name='PII Scanner' 
    ExecutableFilePath='<FULL_PATH_TO_SCRIPT>\pii_scanner.exe'
    CommandLineParameters='%Path% --scan-type full'
    ...>
```

3. Verify the scanner appears in Veeam's antivirus scan options

## Troubleshooting

### Common Issues

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

### Console Output Colors

- **Green**: Success messages
- **Yellow**: Warnings and progress
- **Red**: Errors and PII detection
- **Blue/Cyan**: Processing information

## Project Structure

```
Integrated-PII-Scanner-Veeam/
├── pii_scanner.py     # Main scanner script
├── pii_scanner.xml    # Veeam configuration
├── requirements.txt   # Python dependencies
├── .env              # Environment configuration
├── install.sh        # Unix/Linux installation script
├── install.bat       # Windows installation script
├── LICENSE           # MIT License
└── README.md         # Documentation
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Contact

For questions or support, please contact:

- GitHub: [mritsurgeon](https://github.com/mritsurgeon)
- Project Link: [https://github.com/mritsurgeon/Integrated-PII-Scanner-Veeam](https://github.com/mritsurgeon/Integrated-PII-Scanner-Veeam)

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

- GLiNER model by urchade for PII detection
- Veeam Software for integration capabilities
- RoBERTa tokenizer for text processing

