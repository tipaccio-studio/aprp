"""Xbox app / Microsoft Store (PC Game Pass) games.

These are MSIX packages. GDK games ship a MicrosoftGame.config in their
install folder, which is how we tell games apart from ordinary Store apps.
Launch via the shell's AppsFolder: shell:AppsFolder\\<PackageFamilyName>!<AppId>.
Their executables are ACL-protected, so launching the .exe directly fails.
"""
from __future__ import annotations

import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterator, Optional

from .models import Game

_PS = r"""
$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$games = Get-AppxPackage | Where-Object {
    -not $_.IsFramework -and $_.InstallLocation -and
    (Test-Path -LiteralPath (Join-Path $_.InstallLocation 'MicrosoftGame.config'))
} | ForEach-Object {
    $m = Get-AppxPackageManifest $_
    [pscustomobject]@{
        Name              = $_.Name
        PackageFamilyName = $_.PackageFamilyName
        InstallLocation   = $_.InstallLocation
        AppId             = @($m.Package.Applications.Application)[0].Id
        DisplayName       = $m.Package.Properties.DisplayName
    }
}
ConvertTo-Json -InputObject @($games) -Depth 3
"""


def _query_packages() -> list[dict]:
    out = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _PS],
        capture_output=True, text=True, encoding="utf-8", timeout=120,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    text = out.stdout.strip()
    return json.loads(text) if text else []


def _read_game_config(install_dir: Path) -> tuple[Optional[str], Optional[str]]:
    """Return (display name, logo path) from MicrosoftGame.config."""
    try:
        root = ET.parse(install_dir / "MicrosoftGame.config").getroot()
    except (OSError, ET.ParseError):
        return None, None
    visuals = root.find("ShellVisuals")
    if visuals is None:
        return None, None
    name = visuals.get("DefaultDisplayName")
    logo = None
    for attr in ("Square480x480Logo", "Square150x150Logo", "StoreLogo"):
        rel = visuals.get(attr)
        if rel:
            p = install_dir / rel
            # Packaged images often only exist with a scale suffix (Logo.scale-200.png).
            hits = [p] if p.is_file() else sorted(p.parent.glob(f"{p.stem}*{p.suffix}"), reverse=True)
            if hits:
                logo = str(hits[0])
                break
    return name, logo


def scan() -> Iterator[Game]:
    for pkg in _query_packages():
        pfn, app_id = pkg.get("PackageFamilyName"), pkg.get("AppId")
        if not pfn or not app_id:
            continue
        install_dir = Path(pkg["InstallLocation"])
        cfg_name, logo = _read_game_config(install_dir)
        manifest_name = pkg.get("DisplayName") or ""
        title = cfg_name or (manifest_name if not manifest_name.startswith("ms-resource:") else pkg["Name"])
        yield Game(
            id=f"xbox:{pfn}",
            platform="xbox",
            title=title,
            install_dir=str(install_dir),
            launch_uri=f"shell:AppsFolder\\{pfn}!{app_id}",
            cover=logo,
            store_id=pfn,  # Microsoft Store lookups accept the PackageFamilyName
        )
