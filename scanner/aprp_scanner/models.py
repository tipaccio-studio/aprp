"""Shared data model. This JSON shape is the contract with the C# UI."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional


@dataclass
class Game:
    id: str                      # globally unique, e.g. "steam:570", "epic:Fortnite"
    platform: str                # "steam" | "epic" | "xbox"
    title: str
    install_dir: str             # used by the C++ monitor to find the running game process ("" if not installed)
    launch_uri: str              # handed to ShellExecute by the UI: plays if installed, otherwise starts the install
    cover: Optional[str] = None  # portrait art (2:3), local file path or https URL
    size_bytes: Optional[int] = None
    installed: bool = True       # False = owned in the store library but not on disk
    banner: Optional[str] = None       # wide hero art (16:9 or wider)
    logo: Optional[str] = None         # transparent title logo, local file only
    description: Optional[str] = None  # short store/encyclopedia blurb, in the user's language when available
    developer: Optional[str] = None
    store_id: Optional[str] = None     # platform-specific id used for online metadata lookups
    source: Optional[str] = None       # launcher inside the platform, e.g. "modrinth" (shown under Xbox)
    playtime_minutes: Optional[int] = None  # as recorded by the store/launcher itself (None = unknown)
    last_played: Optional[int] = None       # unix seconds, from the store/launcher

    def to_dict(self) -> dict:
        return asdict(self)
