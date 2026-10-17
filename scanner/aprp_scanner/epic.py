"""Epic Games Store.

Installed: one JSON *.item manifest per install in Data/Manifests.
Owned:     the launcher's catalog cache (Data/Catalog/catcache.bin, base64 JSON),
           which lists the items in the user's library with titles and box art.

Launching/installing through the launcher URI (rather than the .exe) keeps
Epic's auth/ownership check and cloud saves working.
"""
from __future__ import annotations

import base64
import json
import os
import winreg
from pathlib import Path
from typing import Iterator, Optional
from urllib.parse import quote

from .metadata import looks_mangled
from .models import Game


def data_dir() -> Optional[Path]:
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Epic Games\EpicGamesLauncher") as k:
            path = Path(winreg.QueryValueEx(k, "AppDataPath")[0])
            if path.is_dir():
                return path
    except OSError:
        pass
    fallback = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Epic" / "EpicGamesLauncher" / "Data"
    return fallback if fallback.is_dir() else None


def launcher_uri(namespace: str, catalog_id: str, app_name: str, action: str = "launch") -> str:
    ident = quote(f"{namespace}:{catalog_id}:{app_name}", safe="")
    return f"com.epicgames.launcher://apps/{ident}?action={action}&silent=true"


# Kept for callers/tests that only launch.
def launch_uri(namespace: str, catalog_id: str, app_name: str) -> str:
    return launcher_uri(namespace, catalog_id, app_name, "launch")


def _installed_manifests(data: Path) -> dict[str, dict]:
    """AppName -> manifest, for complete installs of games (not engines, plugins or DLC)."""
    result: dict[str, dict] = {}
    for item in (data / "Manifests").glob("*.item"):
        try:
            m = json.loads(item.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if m.get("bIsIncompleteInstall"):
            continue
        categories = m.get("AppCategories") or []
        if categories and "games" not in categories:
            continue  # Unreal Engine, plugins, etc.
        if m.get("MainGameAppName") and m["MainGameAppName"] != m.get("AppName"):
            continue  # DLC installed into a base game
        if not m.get("InstallLocation") or not Path(m["InstallLocation"]).is_dir():
            continue
        result[m["AppName"]] = m
    return result


def _owned_catalog(data: Path) -> list[dict]:
    """Base games from the launcher's catalog cache, each with its Windows appId."""
    path = data / "Catalog" / "catcache.bin"
    try:
        items = json.loads(base64.b64decode(path.read_bytes()))
    except (OSError, ValueError):
        return []
    games = []
    for it in items:
        cats = {c.get("path") for c in it.get("categories") or []}
        if "games" not in cats or "addons" in cats:
            continue  # software, engines, audiences, DLC / launchable add-ons
        if (it.get("mainGameItem") or {}).get("id"):
            continue  # DLC of another game
        app_id = next((r.get("appId") for r in it.get("releaseInfo") or []
                       if r.get("appId") and "Windows" in (r.get("platform") or [])), None)
        if app_id:
            games.append({**it, "_appId": app_id})
    return games


def _clean_title(title: str) -> str:
    # The catalog cache sometimes stores ®/™ as a literal "?" (e.g. "Rocket League?").
    return title[:-1] if title.endswith("?") and title[-2:-1].isalnum() else title


def _details(item: dict) -> dict:
    """Art, description and developer from a catalog item."""
    images = {img.get("type"): img.get("url") for img in item.get("keyImages") or []}
    title = _clean_title(item.get("title") or "")
    desc = (item.get("description") or "").strip()
    # Drop text that is just the title again, or whose accented letters were lost as "?".
    if len(desc) <= len(title) + 10 or looks_mangled(desc):
        desc = ""
    return {
        "cover": images.get("DieselGameBoxTall") or images.get("Thumbnail") or images.get("DieselGameBox"),
        "banner": images.get("DieselGameBox") or images.get("DieselStoreFrontWide"),
        "description": desc or None,
        "developer": item.get("developer") or None,
    }


def scan() -> Iterator[Game]:
    data = data_dir()
    if data is None:
        return
    installed = _installed_manifests(data)
    details: dict[str, dict] = {}

    for item in _owned_catalog(data):
        app = item["_appId"]
        details[app] = _details(item)
        if app in installed:
            continue  # reported below with its real install folder
        yield Game(
            id=f"epic:{app}",
            platform="epic",
            title=_clean_title(item.get("title") or app),
            install_dir="",
            launch_uri=launcher_uri(item["namespace"], item["id"], app, "install"),
            installed=False,
            store_id=app,
            **details[app],
        )

    for app, m in installed.items():
        yield Game(
            id=f"epic:{app}",
            platform="epic",
            title=m.get("DisplayName") or app,
            install_dir=m["InstallLocation"],
            launch_uri=launcher_uri(m["CatalogNamespace"], m["CatalogItemId"], app),
            size_bytes=m.get("InstallSize") or None,
            store_id=app,
            **details.get(app, {}),
        )
