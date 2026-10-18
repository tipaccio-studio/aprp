# Builds dist\aprp-<version>.msi with Advanced Installer, from dist\aprp.exe.
#
#   .\installer\advinst\make-msi.ps1                 # after .\build.ps1 -Stage app
#
# The project file is generated from scratch every time from the command file below,
# so nothing binary is kept in git. It needs a registered Advanced Installer licence
# (Professional or higher: banners, languages and command-line editing are not in the
# free edition). Tipaccio Studio applied for the free open-source licence; register it with
#   AdvancedInstaller.com /register <licence id>
#
# Status: prepared for the licence; not built yet (see installer/advinst/README.md).
param([string]$Version)
$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\..\.."
if (-not $Version) {
    $Version = ([xml](Get-Content "$root\src\Aprp.App\Aprp.App.csproj")).Project.PropertyGroup.Version | Where-Object { $_ } | Select-Object -First 1
}
$exe = "$root\dist\aprp.exe"
if (-not (Test-Path $exe)) { throw "dist\aprp.exe is missing: run .\build.ps1 -Stage app first" }

$ai = Get-ChildItem "${env:ProgramFiles(x86)}\Caphyon", "$env:ProgramFiles\Caphyon" -Recurse -Filter AdvancedInstaller.com -ErrorAction SilentlyContinue |
    Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
if (-not $ai) { throw "Advanced Installer not found (winget install Caphyon.AdvancedInstaller)" }

$work = "$root\installer\advinst\build"
New-Item -ItemType Directory -Force $work | Out-Null
$aip = "$work\aprp.aip"
& $ai /newproject $aip -type professional -lang en -overwrite
if ($LASTEXITCODE -ne 0) { throw "AdvancedInstaller /newproject failed ($LASTEXITCODE)" }

# Command file (.aic): first line must be ";aic"; UTF-8 needs a BOM.
$aic = @"
;aic
SetVersion $Version
SetProperty ProductName="aprp"
SetProperty Manufacturer="Tipaccio Studio"
SetProperty ARPURLINFOABOUT="https://github.com/tipaccio-studio/aprp"
SetProperty ARPHELPLINK="https://github.com/tipaccio-studio/aprp/issues"
SetPackageType x64
SetIcon -icon "$root\src\Aprp.App\Assets\aprp.ico"
SetBitmap -banner "$root\installer\art\msi-banner.bmp" -dialog "$root\installer\art\msi-dialog.bmp"
AddFile APPDIR "$exe"
NewShortcut -name aprp -dir ProgramMenuFolder -target APPDIR\aprp.exe -desc "All your games in one library"
NewShortcut -name aprp -dir DesktopFolder -target APPDIR\aprp.exe -desc "All your games in one library"
AddLanguage 1040 -buildname DefaultBuild
AddLanguage 3082 -buildname DefaultBuild
AddLanguage 1036 -buildname DefaultBuild
AddLanguage 1031 -buildname DefaultBuild
AddLanguage 1046 -buildname DefaultBuild
SetPackageName "$root\dist\aprp-$Version.msi" -buildname DefaultBuild
Save
Rebuild
"@
Set-Content "$work\aprp.aic" $aic -Encoding utf8BOM
& $ai /execute $aip "$work\aprp.aic"
if ($LASTEXITCODE -ne 0) { throw "AdvancedInstaller /execute failed ($LASTEXITCODE)" }
Write-Host "dist\aprp-$Version.msi"
