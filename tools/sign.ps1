# Authenticode-signs files (SHA-256 + RFC 3161 timestamp). Used by build.ps1 and by Inno Setup
# for the installer and uninstaller. Configure ONE signing method through environment variables:
#
#   Certificate in the Windows certificate store (Certum SimplySign, USB token, any OV/EV cert):
#     $env:APRP_SIGN_THUMBPRINT = "<SHA-1 thumbprint>"
#
#   Azure Artifact Signing (formerly Trusted Signing):
#     $env:APRP_SIGN_AZURE_JSON = "C:\path\metadata.json"          # Endpoint, CodeSigningAccountName, CertificateProfileName
#     $env:APRP_SIGN_AZURE_DLIB = "C:\path\Azure.CodeSigning.Dlib.dll"
#
#   Optional: $env:APRP_SIGN_TIMESTAMP  (default: DigiCert; Azure: http://timestamp.acs.microsoft.com)
#
# Exit codes: 0 signed, 2 not configured, other = signtool failure.
param([Parameter(Mandatory, ValueFromRemainingArguments)][string[]]$Files)
$ErrorActionPreference = "Stop"

$signtool = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin" -Recurse -Filter signtool.exe -ErrorAction SilentlyContinue |
    Where-Object FullName -match '\\x64\\' | Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
if (-not $signtool) { Write-Error "signtool.exe not found: install the Windows 10/11 SDK (Signing Tools)"; exit 3 }

$common = @("sign", "/fd", "sha256", "/td", "sha256", "/d", "aprp", "/du", "https://github.com/tipaccio-studio/aprp")
if ($env:APRP_SIGN_AZURE_JSON) {
    if (-not $env:APRP_SIGN_AZURE_DLIB) { Write-Error "APRP_SIGN_AZURE_DLIB is not set"; exit 3 }
    $ts = $env:APRP_SIGN_TIMESTAMP ?? "http://timestamp.acs.microsoft.com"
    $signArgs = $common + @("/tr", $ts, "/dlib", $env:APRP_SIGN_AZURE_DLIB, "/dmdf", $env:APRP_SIGN_AZURE_JSON)
} elseif ($env:APRP_SIGN_THUMBPRINT) {
    $ts = $env:APRP_SIGN_TIMESTAMP ?? "http://timestamp.digicert.com"
    $signArgs = $common + @("/tr", $ts, "/sha1", $env:APRP_SIGN_THUMBPRINT.Replace(" ", ""))
} else {
    Write-Host "signing not configured (set APRP_SIGN_THUMBPRINT or APRP_SIGN_AZURE_JSON)"
    exit 2
}

foreach ($f in $Files) {
    # A timestamp server hiccup shouldn't fail a release build: retry a few times.
    for ($try = 1; $try -le 3; $try++) {
        & $signtool @signArgs $f | Out-Host
        if ($LASTEXITCODE -eq 0) { break }
        Start-Sleep -Seconds (2 * $try)
    }
    if ($LASTEXITCODE -ne 0) { Write-Error "signing failed: $f"; exit $LASTEXITCODE }
}
exit 0
