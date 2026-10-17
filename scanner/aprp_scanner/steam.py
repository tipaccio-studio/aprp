"""Steam: installed games from appmanifest_*.acf, owned games from local client caches.

Installed:  registry -> libraryfolders.vdf -> appmanifest_<appid>.acf
Owned:      apps in the user's library (appcache/librarycache + userdata/*/config/localconfig.vdf),
            named and typed via the binary appcache/appinfo.vdf. No API key or network needed.

Play with steam://rungameid/<appid>, install with steam://install/<appid>.
"""
from __future__ import annotations

import winreg
from pathlib import Path
from typing import Iterator, Optional

from . import vdf
from .models import Game
from .steam_appinfo import read_common

_NOT_GAMES = {"228980", "480"}  # Steamworks Common Redistributables, Spacewar (SDK test app)
_NON_GAME_TYPES = {"tool", "config", "dlc", "beta", "music", "video"}
_STATE_FULLY_INSTALLED = 4
_CDN = "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/{appid}/library_600x900.jpg"


def find_steam_root() -> Optional[Path]:
    candidates = [
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
    ]
    for hive, key, value in candidates:
        try:
            with winreg.OpenKey(hive, key) as k:
                path = Path(winreg.QueryValueEx(k, value)[0])
                if path.is_dir():
                    return path
        except OSError:
            continue
    return None


def library_folders(steam_root: Path) -> list[Path]:
    folders = [steam_root]
    lf = steam_root / "steamapps" / "libraryfolders.vdf"
    if lf.is_file():
        data = vdf.load(lf).get("libraryfolders", {})
        for entry in data.values():
            # New format: {"path": "..."}; old format: plain string.
            raw = entry.get("path") if isinstance(entry, dict) else entry
            if raw and Path(raw).is_dir():
                folders.append(Path(raw))
    # De-duplicate while preserving order (the root is usually listed again as "0").
    seen, unique = set(), []
    for f in folders:
        key = str(f.resolve()).lower()
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


_CDN_ROOT = "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/{appid}/"


def _local_art(steam_root: Path, appid: str, name: str, ext: str = "jpg") -> Optional[str]:
    """Art from Steam's own library cache: name = library_600x900 | library_hero | logo."""
    cache = steam_root / "appcache" / "librarycache"
    legacy = cache / f"{appid}_{name}.{ext}"  # pre-2024 client layout
    if legacy.is_file():
        return str(legacy)
    folder = cache / appid  # current layout: librarycache/<appid>/[<hash>/]<name>.<ext>
    if folder.is_dir():
        for hit in folder.rglob(f"{name}.{ext}"):
            return str(hit)
    return None


def _local_cover(steam_root: Path, appid: str) -> Optional[str]:
    return _local_art(steam_root, appid, "library_600x900")


def _art(root: Path, appid: str) -> dict:
    return {
        "cover": _local_cover(root, appid) or _CDN.format(appid=appid),
        "banner": _local_art(root, appid, "library_hero") or _CDN_ROOT.format(appid=appid) + "library_hero.jpg",
        "logo": _local_art(root, appid, "logo", "png"),
        "store_id": appid,
    }


def library_appids(steam_root: Path) -> set[str]:
    """App ids in the logged-in users' libraries, from client caches."""
    ids: set[str] = set()
    cache = steam_root / "appcache" / "librarycache"
    if cache.is_dir():
        ids.update(p.name for p in cache.iterdir() if p.is_dir() and p.name.isdigit())
    for lc in steam_root.glob("userdata/*/config/localconfig.vdf"):
        apps = (vdf.load(lc).get("userlocalconfigstore", {}).get("software", {})
                .get("valve", {}).get("steam", {}).get("apps", {}))
        ids.update(k for k in apps if k.isdigit())
    return ids


def _installed(root: Path) -> dict[str, Game]:
    games: dict[str, Game] = {}
    for lib in library_folders(root):
        steamapps = lib / "steamapps"
        for acf in steamapps.glob("appmanifest_*.acf"):
            state = vdf.load(acf).get("appstate", {})
            appid = state.get("appid")
            if not appid or appid in _NOT_GAMES:
                continue
            if not int(state.get("stateflags", "0")) & _STATE_FULLY_INSTALLED:
                continue
            games[appid] = Game(
                id=f"steam:{appid}",
                platform="steam",
                title=state.get("name", f"Steam app {appid}"),
                install_dir=str(steamapps / "common" / state.get("installdir", "")),
                launch_uri=f"steam://rungameid/{appid}",
                size_bytes=int(state.get("sizeondisk", "0")) or None,
                **_art(root, appid),
            )
    return games


def scan() -> Iterator[Game]:
    root = find_steam_root()
    if root is None:
        return
    installed = _installed(root)

    appinfo_path = root / "appcache" / "appinfo.vdf"
    try:
        appinfo = read_common(appinfo_path) if appinfo_path.is_file() else {}
    except (OSError, ValueError):
        appinfo = {}  # unknown future format: still report installed games

    for appid, game in installed.items():
        if appinfo.get(appid, {}).get("type", "").lower() in _NON_GAME_TYPES:
            continue
        yield game

    for appid in library_appids(root) - installed.keys() - _NOT_GAMES:
        common = appinfo.get(appid)
        if not common or common.get("type", "").lower() != "game" or not common.get("name"):
            continue
        yield Game(
            id=f"steam:{appid}",
            platform="steam",
            title=common["name"].strip(),
            install_dir="",
            launch_uri=f"steam://install/{appid}",
            installed=False,
            **_art(root, appid),
        )
