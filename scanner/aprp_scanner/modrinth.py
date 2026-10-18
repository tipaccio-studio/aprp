"""Modrinth App: Minecraft instances (modpacks), listed under Xbox.

The Modrinth App keeps its instances in %APPDATA%\\ModrinthApp\\app.db (SQLite, read here
read-only) with their files in profiles\\<path>. It records playtime itself, so aprp
doesn't need to track it.

Play with modrinth://launch/instance/<instance id>, the same link the Modrinth App
uses for the desktop shortcuts it creates.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Iterator, Optional
from urllib.parse import quote

from .models import Game

_LOADERS = {"forge": "Forge", "neoforge": "NeoForge", "fabric": "Fabric", "quilt": "Quilt", "vanilla": "Vanilla"}
_MODS_WORD = {"it": "mod", "de": "Mods"}  # everything else: "mods"
# Characters the Rust `url` crate leaves unescaped in a path segment (what the Modrinth App
# itself produces for its shortcuts); space, quotes, #, ?, %, /, <, >, `, {, } get escaped.
_URL_PATH_SAFE = "!$&'()*+,;=:@[]~^|\\"


def app_dir() -> Optional[Path]:
    path = Path(os.environ.get("APPDATA", "")) / "ModrinthApp"
    return path if (path / "app.db").is_file() else None


def _connect(db: Path) -> sqlite3.Connection:
    uri = db.as_posix()
    try:
        con = sqlite3.connect(f"file:{uri}?mode=ro", uri=True, timeout=5)
        con.execute("select 1 from instances limit 1")
        return con
    except sqlite3.Error:
        # The app may hold the WAL; an immutable snapshot is still good enough for a library list.
        return sqlite3.connect(f"file:{uri}?immutable=1", uri=True)


def _latest_screenshot(folder: Path) -> Optional[str]:
    shots = folder / "screenshots"
    if not shots.is_dir():
        return None
    files = [p for p in shots.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg")]
    return str(max(files, key=lambda p: p.stat().st_mtime)) if files else None


def _count_mods(folder: Path) -> int:
    mods = folder / "mods"
    return sum(1 for p in mods.iterdir() if p.suffix.lower() == ".jar") if mods.is_dir() else 0


def _description(game_version: Optional[str], loader: Optional[str], loader_version: Optional[str], mods: int) -> str:
    parts = [f"Minecraft {game_version}" if game_version else "Minecraft"]
    if loader and loader != "vanilla":
        parts.append(f"{_LOADERS.get(loader, loader.title())} {loader_version or ''}".strip())
    if mods:
        lang = os.environ.get("APRP_LANG", "en")
        parts.append(f"{mods} {_MODS_WORD.get(lang, 'mods')}")
    return " · ".join(parts)


def scan() -> Iterator[Game]:
    root = app_dir()
    if root is None:
        return
    con = _connect(root / "app.db")
    try:
        rows = con.execute(
            """select i.id, i.path, i.name, i.icon_path, i.install_stage, i.last_played,
                      i.submitted_time_played, i.recent_time_played,
                      c.game_version, c.loader, c.loader_version
               from instances i left join instance_content_sets c on c.id = i.applied_content_set_id"""
        ).fetchall()
    finally:
        con.close()

    for (iid, path, name, icon, stage, last, submitted, recent, game_version, loader, loader_version) in rows:
        if stage != "installed" or not path:
            continue
        folder = root / "profiles" / path
        if not folder.is_dir():
            continue
        seconds = int(submitted or 0) + int(recent or 0)
        yield Game(
            id=f"modrinth:{iid}",
            platform="xbox",          # shown under Xbox (Minecraft is a Microsoft game)
            source="modrinth",
            title=name or path,
            install_dir=str(folder),
            launch_uri="modrinth://launch/instance/" + quote(iid, safe=_URL_PATH_SAFE),
            cover=icon if icon and Path(icon).is_file() else None,
            banner=_latest_screenshot(folder),
            description=_description(game_version, loader, loader_version, _count_mods(folder)),
            playtime_minutes=seconds // 60,
            last_played=int(last) if last else None,
        )
