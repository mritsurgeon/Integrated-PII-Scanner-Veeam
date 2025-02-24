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

    ${NSD_CreateLabel} 0 0 100% 20u "Select GLiNER Model:"
    Pop $0

    ${NSD_CreateComboBox} 0 25 100% 12u ""
    Pop $ModelComboBox
    
    ${NSD_CB_AddString} $ModelComboBox "urchade/gliner_multi_pii-v1 - Personal Identifiable Information NER"
    ${NSD_CB_AddString} $ModelComboBox "urchade/gliner_multiv2.1 - Generalist NER"
    
    ${NSD_CB_SelectString} $ModelComboBox "urchade/gliner_multi_pii-v1 - Personal Identifiable Information NER"

    nsDialogs::Show
FunctionEnd

Function ModelSelectionPageLeave
    ${NSD_GetText} $ModelComboBox $ModelSelection
    ${StrStr} $0 $ModelSelection "urchade/"
    ${StrStr} $1 $0 " -"
    StrCpy $ModelSelection $1 -2
FunctionEnd

Section "Install"
    ; Create installation directories
    CreateDirectory "$INSTDIR"
    CreateDirectory "$LOCALAPPDATA\PII Scanner"
    CreateDirectory "$INSTDIR\model_download"

    ; Copy executable and configuration
    SetOutPath "$INSTDIR"
    File "dist\pii_scanner.exe"
    File ".env.example"
    File "pii_scanner.xml"

    ; Create Python script to download model
    FileOpen $0 "$INSTDIR\model_download\download_model.py" w
    FileWrite $0 'from transformers import AutoTokenizer, AutoModelForTokenClassification$\r$\n'
    FileWrite $0 'import sys$\r$\n'
    FileWrite $0 'model_name = sys.argv[1]$\r$\n'
    FileWrite $0 'print(f"Downloading model {model_name}...")$\r$\n'
    FileWrite $0 'tokenizer = AutoTokenizer.from_pretrained(model_name)$\r$\n'
    FileWrite $0 'model = AutoModelForTokenClassification.from_pretrained(model_name)$\r$\n'
    FileWrite $0 'print("Model downloaded successfully!")$\r$\n'
    FileClose $0

    ; Create batch script to run model download
    FileOpen $0 "$INSTDIR\model_download\download_model.bat" w
    FileWrite $0 '@echo off$\r$\n'
    FileWrite $0 'python download_model.py "$ModelSelection"$\r$\n'
    FileWrite $0 'pause$\r$\n'
    FileClose $0

    ; Create .env file with selected model
    FileOpen $0 "$INSTDIR\.env" w
    FileWrite $0 "# Database$\r$\n"
    FileWrite $0 "DB_FILE=C:\ProgramData\PII Scanner\pii_scan_history.db$\r$\n$\r$\n"
    FileWrite $0 "# GLiNER Model$\r$\n"
    FileWrite $0 "PII_MODEL_NAME=$ModelSelection$\r$\n"
    FileWrite $0 "MAX_CHUNK_LENGTH=384$\r$\n$\r$\n"
    FileWrite $0 "# Logging$\r$\n"
    FileWrite $0 "LOG_LEVEL=INFO$\r$\n"
    FileWrite $0 "LOG_FILE=C:\ProgramData\PII Scanner\pii_scanner.log$\r$\n"
    FileClose $0

    ; Set permissions using built-in commands
    ExecWait 'cmd.exe /C icacls "$INSTDIR" /grant "Users":(OI)(CI)RX'
    ExecWait 'cmd.exe /C icacls "$LOCALAPPDATA\PII Scanner" /grant "Users":(OI)(CI)F'

    ; Check if Veeam directory exists and copy/rename XML file
    IfFileExists "C:\Program Files\Common Files\Veeam\Backup and Replication\Mount Service" 0 +3
        CopyFiles "$INSTDIR\pii_scanner.xml" "C:\Program Files\Common Files\Veeam\Backup and Replication\Mount Service\AntivirusInfos.xml"
        Delete "$INSTDIR\pii_scanner.xml"

    ; Download the selected model
    MessageBox MB_OK "The installer will now download the selected GLiNER model. This may take a few minutes."
    ExecWait 'cmd.exe /c "$INSTDIR\model_download\download_model.bat"'

    ; Cleanup model download files
    RMDir /r "$INSTDIR\model_download"

    ; Notify user about completion
    MessageBox MB_OK "Installation complete. The model has been downloaded and configured."
SectionEnd
