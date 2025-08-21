; Define installer name and output file
Name "PII Scanner"
OutFile "PII_Scanner_Installer.exe"

; Default installation directory
InstallDir "C:\Program Files\PII Scanner"

; Request administrator privileges
RequestExecutionLevel admin

; Include modern UI
!include "MUI2.nsh"
!include "nsDialogs.nsh"
!include "StrFunc.nsh"
${StrStr}

; Variables
Var Dialog
Var ModelComboBox
Var ModelSelection

; Custom page for model selection
Page custom ModelSelectionPage ModelSelectionPageLeave

; Pages to show in the installer
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

Function ModelSelectionPage
    nsDialogs::Create 1018
    Pop $Dialog

    ${NSD_CreateLabel} 0 0 100% 20u "Select GLiNER Model Configuration:"
    Pop $0

    ${NSD_CreateComboBox} 0 25 100% 12u ""
    Pop $ModelComboBox
    
    ; Model options
    ${NSD_CB_AddString} $ModelComboBox "urchade/gliner_multi_pii-v1"
    ${NSD_CB_AddString} $ModelComboBox "urchade/gliner_multiv2.1"
    
    ; Set default selection (the pre-downloaded model)
    ${NSD_CB_SelectString} $ModelComboBox "urchade/gliner_multi_pii-v1"

    ; Add description labels
    ${NSD_CreateLabel} 0 55 100% 40u "urchade/gliner_multi_pii-v1 (INCLUDED) - Specialized model for detecting Personal Identifiable Information including names, addresses, SSN, credit cards, phone numbers, emails, and more. This model is pre-downloaded and ready to use."
    Pop $0
    ${NSD_CreateLabel} 0 95 100% 40u "urchade/gliner_multiv2.1 (DOWNLOAD ON FIRST USE) - General-purpose Named Entity Recognition model for detecting organizations, locations, dates, and other entities. This model will be downloaded automatically when first used."
    Pop $1

    ${NSD_CreateLabel} 0 145 100% 20u "Note: The default PII model is included with the installer for immediate use."
    Pop $2

    nsDialogs::Show
FunctionEnd

Function ModelSelectionPageLeave
    ; Get selected model directly
    ${NSD_GetText} $ModelComboBox $ModelSelection
FunctionEnd

Section "Install"
    ; Create installation directories
    CreateDirectory "$INSTDIR"
    CreateDirectory "$INSTDIR\models"
    CreateDirectory "C:\ProgramData\PII Scanner"
    CreateDirectory "C:\ProgramData\PII Scanner\reports"

    ; Copy executable and configuration
    SetOutPath "$INSTDIR"
    File "dist\pii_scanner.exe"
    File ".env.example"
    File "pii_scanner.xml"

    ; Note: Models will be downloaded on first use to avoid installer size issues
    ; The GLiNER models are too large (~400MB+) for NSIS to handle efficiently

    ; Create .env file with selected model and HTML report configuration
    FileOpen $0 "$INSTDIR\.env" w
    FileWrite $0 "# PII Scanner Configuration$\r$\n$\r$\n"
    FileWrite $0 "# Report Output Directory$\r$\n"
    FileWrite $0 "REPORT_OUTPUT_DIR=C:\ProgramData\PII Scanner\reports$\r$\n$\r$\n"
    FileWrite $0 "# GLiNER Model Configuration$\r$\n"
    FileWrite $0 "PII_MODEL_NAME=$ModelSelection$\r$\n"
    FileWrite $0 "MAX_CHUNK_LENGTH=384$\r$\n$\r$\n"
    FileWrite $0 "# Logging Configuration$\r$\n"
    FileWrite $0 "LOG_LEVEL=INFO$\r$\n"
    FileWrite $0 "LOG_FILE=C:\ProgramData\PII Scanner\pii_scanner.log$\r$\n$\r$\n"
    FileWrite $0 "# Basic PII Labels (for lite scans)$\r$\n"
    FileWrite $0 "PII_LABELS=person,organization,phone number,address,passport number,email,credit card number,social security number$\r$\n$\r$\n"
    FileWrite $0 "# Extended PII Labels (for full scans)$\r$\n"
    FileWrite $0 "PII_LABELS_FULL=person,organization,phone number,address,passport number,email,credit card number,social security number,health insurance id number,date of birth,mobile phone number,bank account number,medication,cpf,driver's license number,tax identification number,medical condition,identity card number,national id number,ip address,email address,iban,credit card expiration date,username,health insurance number,registration number,student id number,insurance number,flight number,landline phone number,blood type,cvv,reservation number,digital signature,social media handle,license plate number,cnpj,postal code,passport_number,serial number,vehicle registration number,credit card brand,fax number,visa number,insurance company,identity document number,transaction number,national health insurance number,cvc,birth certificate number,train ticket number,passport expiration date,social_security_number$\r$\n"
    FileClose $0

    ; Set permissions using built-in commands
    ExecWait 'cmd.exe /C icacls "$INSTDIR" /grant "Users":(OI)(CI)RX'
    ExecWait 'cmd.exe /C icacls "C:\ProgramData\PII Scanner" /grant "Users":(OI)(CI)F'
    ExecWait 'cmd.exe /C icacls "C:\ProgramData\PII Scanner\reports" /grant "Users":(OI)(CI)F'

    ; Check if Veeam directory exists and copy/rename XML file
    IfFileExists "C:\Program Files\Common Files\Veeam\Backup and Replication\Mount Service" 0 +3
        CopyFiles "$INSTDIR\pii_scanner.xml" "C:\Program Files\Common Files\Veeam\Backup and Replication\Mount Service\AntivirusInfos.xml"
        Delete "$INSTDIR\pii_scanner.xml"

    ; Create usage information message with download-on-demand info
    MessageBox MB_OK "Installation complete!$\r$\n$\r$\nPII Scanner has been installed with:$\r$\n- Model: $ModelSelection (DOWNLOAD ON FIRST USE)$\r$\n- HTML reports: C:\ProgramData\PII Scanner\reports$\r$\n- Logs: C:\ProgramData\PII Scanner\pii_scanner.log$\r$\n$\r$\nNote: The GLiNER model will be downloaded automatically$\r$\nwhen you first run a scan. Internet connection required.$\r$\n$\r$\nCompatible with Veeam Backup & Replication.$\r$\nReady for immediate use!"
SectionEnd
