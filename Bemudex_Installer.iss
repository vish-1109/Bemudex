[Setup]
AppName=Bemudex
AppVersion=1.2
AppPublisher="Vishrut"
DefaultDirName={commonpf}\Bemudex
DefaultGroupName=Bemudex
UninstallDisplayName=Bemudex
UninstallDisplayIcon={app}\Bemudex.exe
SetupIconFile="assets\favicon.ico"
Compression=lzma2
SolidCompression=yes
OutputDir=.
OutputBaseFilename=Bemudex-Setup

[Files]
Source: "dist\Bemudex\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs
Source: "dist\VC_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{group}\Bemudex"; Filename: "{app}\Bemudex.exe"; IconFilename: "{app}\Bemudex.exe"; IconIndex: 0
Name: "{commondesktop}\Bemudex"; Filename: "{app}\Bemudex.exe"; IconFilename: "{app}\Bemudex.exe"; IconIndex: 0

[Run]
Filename: "{tmp}\VC_redist.x64.exe"; Parameters: "/quiet /norestart"; Check: IsVCRuntimeMissing; StatusMsg: "Installing Visual C++ Runtime (one-time)..."

[Code]
function IsVCRuntimeMissing: Boolean;
begin
  Result := not RegKeyExists(HKLM, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64');
end;