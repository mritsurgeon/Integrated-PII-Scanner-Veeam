; Define installer name and output file
Name "PII Scanner"
OutFile "PII_Scanner_Installer.exe"

; Default installation directory
InstallDir "C:\Program Files\PII Scanner"

; Request administrator privileges
RequestExecutionLevel admin

; Include modern UI
!include "MUI2.nsh"

; Pages to show in the installer
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

; Section for installation
Section "Install"
  ; Create installation directories
  CreateDirectory "$INSTDIR"
  CreateDirectory "$LOCALAPPDATA\PII Scanner"

  ; Copy executable and configuration
  SetOutPath "$INSTDIR"
  File "dist\pii_scanner.exe"  ; Your compiled executable
  File ".env.example"          ; Your .env.example file
  File "pii_scanner.xml"       ; Your XML file

  ; Rename .env.example to .env
  Rename "$INSTDIR\.env.example" "$INSTDIR\.env"

  ; Set permissions using built-in commands
  ExecWait 'cmd.exe /C icacls "$INSTDIR" /grant "Users":(OI)(CI)RX'
  ExecWait 'cmd.exe /C icacls "$LOCALAPPDATA\PII Scanner" /grant "Users":(OI)(CI)F'

  ; Check if Veeam directory exists and copy/rename XML file
  IfFileExists "C:\Program Files\Common Files\Veeam\Backup and Replication\Mount Service" 0 +3
    CopyFiles "$INSTDIR\pii_scanner.xml" "C:\Program Files\Common Files\Veeam\Backup and Replication\Mount Service\AntivirusInfos.xml"
    Delete "$INSTDIR\pii_scanner.xml"  ; Remove the original XML file from the installation directory

  ; Notify user about configuration
  MessageBox MB_OK "Installation complete. Please review the configuration in $INSTDIR\.env"
SectionEnd
