; Inno Setup definition — requires ISCC.
#define MyAppName "Ionogram Morphology Lab"
#define MyAppVersion "1.1.1"
#define MyAppExeName "IonogramMorphologyLab.exe"
#define MyAppPublisher "Ionogram Morphology Lab"

[Setup]
AppId={{A7C3E2F1-9B40-4D21-9C1E-IML000000001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\IonogramMorphologyLab
DefaultGroupName={#MyAppName}
OutputDir=..\installer
OutputBaseFilename=IonogramMorphologyLab_Setup_{#MyAppVersion}
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=no
UninstallDisplayIcon={app}\{#MyAppExeName}
; Preserve user workspaces under {localappdata} / chosen workspace — do not delete on uninstall
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\IonogramMorphologyLab\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Classes\.imlproj"; ValueType: string; ValueName: ""; ValueData: "IMLProjectPackage"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\IMLProjectPackage"; ValueType: string; ValueName: ""; ValueData: "Ionogram Morphology Lab Project"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\IMLProjectPackage\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Classes\IMLProjectPackage\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Do not remove user projects/workspaces — only leftover app temp if any
Type: files; Name: "{app}\*.log"
