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
Source: "dist\StashSage.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\StashSage"; Filename: "{app}\StashSage.exe"
