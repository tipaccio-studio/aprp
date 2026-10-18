"""CLI entry point: `python -m aprp_scanner scan [--platform steam|epic|xbox]`.

Writes one JSON document to stdout: {"games": [...], "errors": [...]}.
A failing platform never hides results from the others.
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback

from . import epic, metadata, modrinth, steam, xbox

SCANNERS = {"steam": steam.scan, "epic": epic.scan, "xbox": xbox.scan, "modrinth": modrinth.scan}


def _borrow_minecraft_banner(games: list) -> None:
    """Modrinth instances without screenshots get the Minecraft banner from the Xbox app's Minecraft."""
    banner = next((g.banner for g in games if g.platform == "xbox" and g.source is None
                   and "minecraft" in g.title.lower() and g.banner), None)
    if banner:
        for g in games:
            if g.source == "modrinth" and not g.banner:
                g.banner = banner


def run_scan(platforms: list[str], online: bool = False) -> dict:
    games, errors = [], []
    for name in platforms:
        try:
            games.extend(SCANNERS[name]())
        except Exception as exc:  # noqa: BLE001 - report, don't crash the whole scan
            errors.append({"platform": name, "message": str(exc), "trace": traceback.format_exc()})
    try:
        metadata.enrich(games, online=online)
    except Exception as exc:  # noqa: BLE001 - metadata is optional
        errors.append({"platform": "metadata", "message": str(exc), "trace": traceback.format_exc()})
    _borrow_minecraft_banner(games)
    games.sort(key=lambda g: g.title.lower())
    return {"games": [g.to_dict() for g in games], "errors": errors}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aprp_scanner")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="detect installed games")
    scan.add_argument("--platform", choices=sorted(SCANNERS), action="append",
                      help="limit to one platform (repeatable)")
    scan.add_argument("--online", action="store_true",
                      help="fetch missing descriptions/banners from the internet (cached)")
    scan.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    result = run_scan(args.platform or list(SCANNERS), online=args.online)
    sys.stdout.reconfigure(encoding="utf-8")
    json.dump(result, sys.stdout, indent=2 if args.pretty else None, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
