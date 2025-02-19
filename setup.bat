@echo off
mkdir "C:\Program Files\PII Scanner"
mkdir "C:\ProgramData\PII Scanner"

:: Copy executable and configuration
copy "dist\pii_scanner.exe" "C:\Program Files\PII Scanner\"
copy ".env.example" "C:\Program Files\PII Scanner\.env"

:: Set permissions
icacls "C:\ProgramData\PII Scanner" /grant "Users":(OI)(CI)F
icacls "C:\Program Files\PII Scanner" /grant "Users":(OI)(CI)RX

echo Installation complete.
echo Please review the configuration in "C:\Program Files\PII Scanner\.env"