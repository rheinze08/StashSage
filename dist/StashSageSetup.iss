[Setup]
AppName=StashSage
AppVersion=1.0
AppPublisher=Roland Heinze
DefaultDirName={pf}\StashSage
DefaultGroupName=StashSage
OutputBaseFilename=StashSageInstaller
OutputDir=docs
Compression=lzma
SolidCompression=yes

[Files]
; Install everything inside your /dist/ folder to the app directory
Source: "dist\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
; Shortcut to the compiled .exe (not run.bat)
Name: "{group}\StashSage"; Filename: "{app}\StashSage.exe"; WorkingDir: "{app}"

; Optional desktop shortcut
Name: "{commondesktop}\StashSage"; Filename: "{app}\StashSage.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

