# PII Scanner for Veeam

A Python-based PII scanner that integrates with Veeam backup solutions, using GLiNER for accurate PII detection and generating comprehensive HTML reports.

## Key Features

- **Two Scan Modes**:
  - `full`: Complete document analysis (recommended for detailed PII discovery)
  - `lite`: Quick 1MB scan (ideal for initial file classification)
- **Efficient Processing**:
  - Configurable chunk sizes
  - HTML report generation with detailed findings
- **Veeam Integration**:
  - Compatible with Veeam's antivirus scanning interface
  - Supports continuous scanning option
- **Beautiful HTML Reports**:
  - Comprehensive scan summaries
  - PII breakdown by type
  - File-level details with risk assessment
  - Professional styling and responsive design

## Configuration

### Environment Variables (.env)
```bash
# Report Output
REPORT_OUTPUT_DIR=C:\ProgramData\PII Scanner\reports

# GLiNER Model
PII_MODEL_NAME=urchade/gliner_multi_pii-v1
MAX_CHUNK_LENGTH=384

# Logging
LOG_LEVEL=INFO
LOG_FILE=C:\ProgramData\PII Scanner\pii_scanner.log

# Basic PII Labels (for lite scans)
PII_LABELS=person,organization,phone number,address,passport number,email,credit card number,social 
security number
# Extended PII Labels (for full scans)
PII_LABELS_FULL=person,organization,phone number,address,passport number,email,credit card number,social security number,health insurance id number,date of birth,mobile phone number,bank account number,medication,cpf,driver's license number,tax identification number,medical condition,identity card number,national id number,ip address,email address,iban,credit card expiration date,username,health insurance number,registration number,student id number,insurance number,flight number,landline phone number,blood type,cvv,reservation number,digital signature,social media handle,license plate number,cnpj,postal code,passport_number,serial number,vehicle registration number,credit card brand,fax number,visa number,insurance company,identity document number,transaction number,national health insurance number,cvc,birth certificate number,train ticket number,passport expiration date,social_security_number
```

## Installation

### Create Executable
```bash
pyinstaller --onefile --uac-admin --add-data ".env;." pii_scanner.py
```

### Setup Script (setup.bat)
```batch
@echo off
mkdir "C:\Program Files\PII Scanner"
mkdir "C:\ProgramData\PII Scanner"
mkdir "C:\ProgramData\PII Scanner\reports"
copy "dist\pii_scanner.exe" "C:\Program Files\PII Scanner\"
copy ".env" "C:\Program Files\PII Scanner\"
icacls "C:\ProgramData\PII Scanner" /grant "Users":(OI)(CI)F
icacls "C:\ProgramData\PII Scanner\reports" /grant "Users":(OI)(CI)F
```

### Veeam Integration (pii_scanner.xml)
```xml
<AntivirusInfo 
  Name="PII Scanner" 
  IsPortableSoftware="true" 
  ExecutableFilePath="C:\Program Files\PII Scanner\pii_scanner.exe" 
  CommandLineParameters="%Path% --scan-type full" 
  ThreatExistsRegEx="PII_DETECTED: (.*)" 
  IsParallelScanAvailable="false">
  <!-- Add ContinueScanningAfterThreat="true" for scanning all files -->
</AntivirusInfo>
```

## Usage Notes

### Scan Types
- **Full Scan**: Use when you need to discover all PII instances
  ```bash
  pii_scanner.exe path/to/scan --scan-type full
  ```
- **Lite Scan**: Use for quick file classification
  ```bash
  pii_scanner.exe path/to/scan --scan-type lite
  ```

### HTML Report Generation
After each scan, a comprehensive HTML report is automatically generated in the `reports` directory. The report includes:

- **Summary Dashboard**: Total files, files with PII, total PII entities, and risk level
- **PII Breakdown**: Grouped by type with file locations
- **File Details**: Individual file information with PII findings
- **Professional Styling**: Modern, responsive design for easy viewing

### Veeam Integration Tips
1. For complete PII discovery:
   - Use `full` scan type
   - Enable "Continue scanning all remaining files after the first occurrence"
   - Expect longer scan times but comprehensive results

2. For quick file classification:
   - Use `lite` scan type
   - Faster processing
   - Identifies files containing PII without detailed analysis

### Veeam Usage Screenshots

<img width="1159" alt="image" src="https://github.com/user-attachments/assets/6d0e130e-291b-4107-a6b6-4a3c955545fb" />

<img width="607" alt="image" src="https://github.com/user-attachments/assets/7957f4f1-7903-452e-be15-51f1a3abc608" />

<img width="1215" alt="image" src="https://github.com/user-attachments/assets/f6197d9d-aba9-4ac7-b648-51d1a3abc608" />

### Performance Considerations
- Lite scans process only the first 1MB of files
- Full scans process entire files
- HTML reports are generated after scanning completion
- No database overhead - results stored in memory during scan

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
  --verbose              Enable verbose logging (DEBUG level)
```

### Exit Codes
| Code | Type | Description |
|------|------|-------------|
| 0 | Success | No PII found |
| 1 | Warning | PII data found |
| 2 | Error | File not found |
| 3 | Error | Unsupported file type |
| 4 | Error | Report generation failed |
| 5 | Error | Tokenizer initialization failed |
| 6 | Error | GLiNER model initialization failed |
| 7 | Error | NLTK initialization failed |
| 8 | Error | Text extraction failed |
| 9 | Error | Text chunking failed |
| 10 | Error | PII detection failed |
| 11 | Error | Invalid scan type |
| 12 | Error | Missing file path |
| 99 | Error | General exception |

### HTML Report Structure
```html
<!-- Report includes: -->
- Scan information and metadata
- Summary statistics dashboard
- PII breakdown by entity type
- Detailed file information
- Professional CSS styling
- Responsive design for all devices
```

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


## Data Visualization with PandaAI

The PII Scanner includes integration with PandaAI for visualizing scan results and analyzing PII detection patterns from HTML reports.

### Setup PandaAI Integration

1. **Install Requirements**:
```bash
cd Pandas.ai
pip install -r requirements.txt
```

2. **Get PandaAI API Key**:
   - Sign up at [PandaAI](https://pandas.ai)
   - Navigate to your account settings
   - Generate a new API key
   - Replace the API key in `Pandas.ai/datacollector.py`:
     ```python
     pai.api_key.set("YOUR-API-KEY-HERE")
     ```

3. **Configure Reports Path**:
   - The datacollector automatically looks for HTML reports in the `reports` directory
   - Ensure reports are generated before running the datacollector

### Using PandaAI Visualization

1. **Run Data Collection**:
```bash
cd Pandas.ai
python datacollector.py
```

2. **Access Visualizations**:
   - Log into your PandaAI dashboard
   - Navigate to the "vbr-pii-scanner" dataset
   - View PII detection patterns and statistics

### Available Data Points
- Scan history timeline
- PII type distribution
- File type analysis
- Detection patterns
- Scan performance metrics
- Risk level assessment

### Data Source
The PandaAI integration now parses HTML reports instead of SQLite databases, providing:
- Real-time data from the latest scan reports
- Comprehensive scan metadata
- File-level PII findings
- Risk assessment data

### Screenshots 

<img width="1501" alt="image" src="https://github.com/user-attachments/assets/ae74a474-f192-4f00-9722-f2318e3ea231" />

