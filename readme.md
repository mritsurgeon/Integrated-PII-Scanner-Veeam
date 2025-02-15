# PII Scanner for Veeam

A Python-based PII (Personally Identifiable Information) scanner that integrates with Veeam backup solutions. This tool scans various document types for potential PII data exposure using the GLiNER model for accurate detection.

## Overview

The PII Scanner is designed to:
- Detect sensitive information in backup documents
- Integrate seamlessly with Veeam backup solutions
- Support multiple document formats
- Provide both quick and thorough scanning options
- Track scan history and avoid duplicate scans

## Features

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

### Scanning Modes
- **Full Scan**: Complete document analysis
- **Lite Scan**: Quick 1MB limit scan for large files

### Additional Features
- SQLite database for scan history tracking
- Checksum-based file change detection
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

1. Clone the repository:
```bash
git clone https://github.com/mritsurgeon/Integrated-PII-Scanner-Veeam.git
cd Integrated-PII-Scanner-Veeam
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Create and configure .env file:
```bash
DB_FILE=pii_scan_history.db
MODEL_NAME=roberta-base
PII_MODEL_NAME=urchade/gliner_multi_pii-v1
MAX_CHUNK_LENGTH=400
```

4. Configure Veeam integration:
   - Copy pii_scanner.xml to Veeam configuration directory
   - Update paths in XML configuration

## Usage

### Command Line Options

Basic usage:
```bash
python pii_scanner.py /path/to/scan
```

Specify scan type:
```bash
python pii_scanner.py /path/to/scan --scan-type lite
python pii_scanner.py /path/to/scan --scan-type full
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

## Veeam Integration

1. Copy the XML configuration:
```bash
cp pii_scanner.xml <veeam-config-directory>
```

2. Update XML configuration:
```xml
<AntivirusInfo Name='PII Scanner' 
    ExecutableFilePath='<FULL_PATH_TO_SCRIPT>\pii_scanner.py'
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

