# Builds dist\aprp.exe: one self-contained file (.NET runtime, C++ monitor and Python scanner inside).
#
#   .\build.ps1                      # uses `dotnet` on PATH (needs the .NET 10 SDK)
#   .\build.ps1 -Dotnet C:\path\dotnet.exe
#
# Needs: .NET 10 SDK, Python 3.10+ (pip install pyinstaller), CMake + MSVC Build Tools.
# Keep the repo at a short path (e.g. C:\dev\aprp): MSBuild fails beyond 260 characters.
#
# Code signing: set APRP_SIGN_THUMBPRINT or APRP_SIGN_AZURE_JSON (see tools/sign.ps1) and every
# executable is signed: the scanner, aprp.exe, the installer and its uninstaller.
# Use -RequireSign for release builds so an unsigned build fails instead of shipping.
param(
    [string]$Dotnet = "dotnet",
    [string]$Python = "python",
    [switch]$RequireSign
)
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$signing = [bool]($env:APRP_SIGN_THUMBPRINT -or $env:APRP_SIGN_AZURE_JSON)
if ($RequireSign -and -not $signing) { throw "-RequireSign: set APRP_SIGN_THUMBPRINT or APRP_SIGN_AZURE_JSON first" }
if (-not $signing) { Write-Warning "Code signing not configured: the build will be unsigned (SmartScreen will warn)." }
function Sign([string[]]$Files) {
    if (-not $signing) { return }
    & pwsh -NoProfile -File "$root\tools\sign.ps1" @Files
    if ($LASTEXITCODE -ne 0) { throw "signing failed: $Files" }
}

Write-Host "1/5  Native process monitor (C++)" -ForegroundColor Cyan
cmake -S "$root\native" -B "$root\native\build" -A x64 | Out-Null
cmake --build "$root\native\build" --config Release | Out-Null
if (-not (Test-Path "$root\native\bin\aprp_native.dll")) { throw "aprp_native.dll was not built" }

Write-Host "2/5  Python scanner -> aprp-scanner.exe (PyInstaller)" -ForegroundColor Cyan
& $Python -m PyInstaller --version *> $null
if ($LASTEXITCODE -ne 0) { & $Python -m pip install --user --quiet pyinstaller }
& $Python -m PyInstaller --noconfirm --clean --onefile --console --name aprp-scanner `
    --paths "$root\scanner" --distpath "$root\scanner\dist" --workpath "$root\scanner\build" `
    --specpath "$root\scanner\build" "$root\scanner\aprp_scanner_cli.py" | Out-Null
if (-not (Test-Path "$root\scanner\dist\aprp-scanner.exe")) { throw "aprp-scanner.exe was not built" }
Sign "$root\scanner\dist\aprp-scanner.exe"   # before it gets embedded in aprp.exe

Write-Host "3/5  App (C# / WPF) -> single self-contained exe" -ForegroundColor Cyan
& $Dotnet publish "$root\src\Aprp.App\Aprp.App.csproj" -c Release -r win-x64 `
    -p:PublishProfile=SingleExe -o "$root\src\Aprp.App\bin\publish" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "dotnet publish failed" }
Sign "$root\src\Aprp.App\bin\publish\aprp.exe"

Write-Host "4/5  dist\aprp.exe" -ForegroundColor Cyan
New-Item -ItemType Directory -Force "$root\dist" | Out-Null
Copy-Item "$root\src\Aprp.App\bin\publish\aprp.exe" "$root\dist\aprp.exe" -Force
$size = (Get-Item "$root\dist\aprp.exe").Length / 1MB
Write-Host ("     dist\aprp.exe ({0:n0} MB)" -f $size)

Write-Host "5/5  Installer (Inno Setup)" -ForegroundColor Cyan
$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
          "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    Write-Warning "Inno Setup not found (winget install JRSoftware.InnoSetup): skipping the installer."
} else {
    $version = ([xml](Get-Content "$root\src\Aprp.App\Aprp.App.csproj")).Project.PropertyGroup.Version | Where-Object { $_ } | Select-Object -First 1
    $isccArgs = @("/Q", "/DAppVersion=$version")
    if ($signing) {
        # Inno Setup signs the installer and the uninstaller it embeds; $f is the file to sign.
        $isccArgs += "/DSign", "/Saprpsign=pwsh.exe -NoProfile -File `$q$root\tools\sign.ps1`$q `$f"
    }
    & $iscc @isccArgs "$root\installer\aprp.iss"
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed" }
    Write-Host "     dist\aprp-setup-$version.exe"
}
Write-Host "Done." -ForegroundColor Green
