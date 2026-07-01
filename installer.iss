#define MyAppName "Study Budy Desktop"
#define MyAppExeName "Study Budy.exe"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "HotKey LLC"
#define MyAppURL "mailto:hotkeyllc@outlook.com"

[Setup]
AppId={{2D1433C0-8D4B-4E76-8B32-84E46B7F2E5F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\Study Budy Desktop
DefaultGroupName=Study Budy Desktop
DisableProgramGroupPage=yes
OutputDir=release
OutputBaseFilename=Study-Budy-Desktop-v{#MyAppVersion}-Windows-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=study_budy\assets\study-budy-icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Twitch task, timer, and Check-In overlay manager

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "dist\Study Budy\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Study Budy Desktop"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Study Budy Desktop"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Study Budy Desktop"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; User data in %LOCALAPPDATA%\Study Budy is intentionally preserved by default.
