# PII Scanner for Veeam

A Python-based PII scanner that integrates with Veeam backup solutions, using GLiNER for accurate PII detection.

## Key Features

- **Two Scan Modes**:
  - `full`: Complete document analysis (recommended for detailed PII discovery)
  - `lite`: Quick 1MB scan (ideal for initial file classification)
- **Efficient Processing**:
  - Checksum-based duplicate detection
  - Configurable chunk sizes
  - SQLite database for scan history
- **Veeam Integration**:
  - Compatible with Veeam's antivirus scanning interface
  - Supports continuous scanning option

## Configuration

### Environment Variables (.env)
```bash
# Database
DB_FILE=C:\ProgramData\PII Scanner\pii_scan_history.db

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
pyinstaller --onefile --uac-admin --add-data ".env;." --hidden-import=sqlite3 pii_scanner.py
```

### Setup Script (setup.bat)
```batch
@echo off
mkdir "C:\Program Files\PII Scanner"
mkdir "C:\ProgramData\PII Scanner"
copy "dist\pii_scanner.exe" "C:\Program Files\PII Scanner\"
copy ".env" "C:\Program Files\PII Scanner\"
icacls "C:\ProgramData\PII Scanner" /grant "Users":(OI)(CI)F
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

### Veeam Integration Tips
1. For complete PII discovery:
   - Use `full` scan type
   - Enable "Continue scanning all remaining files after the first occurrence"
   - Expect longer scan times but comprehensive results

2. For quick file classification:
   - Use `lite` scan type
   - Faster processing
   - Identifies files containing PII without detailed analysis

### Performance Considerations
- Lite scans process only the first 1MB of files
- Full scans process entire files
- Database caching prevents redundant scans
- Checksum-based detection avoids duplicate processing

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

The PII Scanner includes integration with PandaAI for visualizing scan results and analyzing PII detection patterns.

### Setup PandaAI Integration

1. **Install Requirements**:
```bash
pip install -r Pandas.ai/requirements.txt
```

2. **Get PandaAI API Key**:
   - Sign up at [PandaAI](https://pandas.ai)
   - Navigate to your account settings
   - Generate a new API key
   - Replace the API key in `Pandas.ai/datacollector.py`:
     ```python
     pai.api_key.set("YOUR-API-KEY-HERE")
     ```

3. **Configure Database Path**:
   - Update the db_path in `Pandas.ai/datacollector.py` to point to your SQLite database:
     ```python
     db_path = os.path.join('path', 'to', 'pii_scan_history.db')
     ```

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

### Schema
```yaml
columns:
- id: Unique scan identifier
- file_path: Path to scanned file
- scan_time: Timestamp of scan
- file_size: Size of scanned file
- file_modified: Last modification time
- file_checksum: File hash
- scan_type: 'lite' or 'full'
- pii_entities: Detected PII data
```
### Screenshots 

<img width="1501" alt="image" src="https://github.com/user-attachments/assets/ae74a474-f192-4f00-9722-f2318e3ea231" />

