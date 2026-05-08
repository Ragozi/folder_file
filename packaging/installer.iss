; Inno Setup script for folder_file Windows installer.
; Compile with Inno Setup Compiler (https://jrsoftware.org/isinfo.php) or via CI.
; Expects a built `dist\folder_file\` directory from the PyInstaller spec.

#define MyAppName "folder_file"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Ragozi"
#define MyAppURL "https://github.com/Ragozi/folder_file"
#define MyAppExeName "folder_file.exe"

[Setup]
AppId={{F0LD3R-F11E-4A0B-9C2E-001122334455}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputBaseFilename=folder_file_setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
InfoAfterFile=READ_ME_FIRST.txt

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "startupicon"; Description: "Start folder_file when I sign in to Windows"; GroupDescription: "Auto-start:"; Flags: unchecked

[Files]
Source: "..\dist\folder_file\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "READ_ME_FIRST.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startupicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch folder_file"; Flags: nowait postinstall skipifsilent
