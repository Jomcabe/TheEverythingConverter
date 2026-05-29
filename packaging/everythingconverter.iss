; Inno Setup script for The Everything Converter (Windows installer).
; Compile with:  iscc packaging\everythingconverter.iss
; Expects PyInstaller output in dist\EverythingConverter\ (run build_windows.ps1 first).

#define AppName "The Everything Converter"
#define AppVersion "0.1.0"
#define AppExe "EverythingConverter.exe"
#define AppPublisher "The Everything Converter"

[Setup]
AppId={{B6F2A0E1-3C5D-4F7A-9C21-6E2B7A8D9C10}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\EverythingConverter
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=EverythingConverter-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Per-user install needs no admin rights — friendlier for friends.
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
; Bundle the entire PyInstaller output directory.
Source: "..\dist\EverythingConverter\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
