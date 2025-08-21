@echo off
mkdir "C:\Program Files\PII Scanner"
mkdir "C:\ProgramData\PII Scanner"
mkdir "C:\ProgramData\PII Scanner\reports"
copy "dist\pii_scanner.exe" "C:\Program Files\PII Scanner\"
copy ".env" "C:\Program Files\PII Scanner\"
icacls "C:\ProgramData\PII Scanner" /grant "Users":(OI)(CI)F
icacls "C:\ProgramData\PII Scanner\reports" /grant "Users":(OI)(CI)F
echo Setup complete! PII Scanner installed with HTML report generation.
pause