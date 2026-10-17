"""Online metadata: descriptions, banners and developers, cached on disk.

Sources, in order of preference:
  Steam games   Steam store appdetails (store language)
  Xbox games    Microsoft Store display catalog, looked up by PackageFamilyName
  Epic games    local catalog text when it's intact, else the same title on the Steam store
  anything left Wikipedia page summary in the user's language (only if it's about a video game)

Results (including misses) are cached in %LOCALAPPDATA%\\aprp\\metadata.json so
rescans are offline and fast; entries refresh after 30 days, misses after 3.
"""
from __future__ import annotations

import ctypes
import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from .models import Game

CACHE_PATH = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "aprp" / "metadata.json"
TTL_HIT = 30 * 86400
TTL_MISS = 3 * 86400
_UA = "aprp-launcher/0.2 (+https://github.com/; desktop game launcher)"

_STEAM_LANG = {
    "it": "italian", "en": "english", "de": "german", "fr": "french", "es": "spanish",
    "pt": "brazilian", "pl": "polish", "ru": "russian", "nl": "dutch", "tr": "turkish",
    "ja": "japanese", "ko": "koreana", "zh": "schinese",
}
_WIKI_GAME_WORDS = ("videogioco", "video game", "videospiel", "computerspiel", "jeu vidéo", "videojuego",
                    "videogame", "jogo eletrônico", "gioco", "spiel", "jeu", "juego", "jogo")
_WIKI_DISAMBIG = {"it": "videogioco", "en": "video game", "es": "videojuego", "fr": "jeu vidéo",
                  "de": "Computerspiel", "pt": "jogo eletrônico"}
_DEFAULT_COUNTRY = {"it": "IT", "en": "US", "es": "ES", "fr": "FR", "de": "DE", "pt": "BR"}


def user_locale() -> tuple[str, str]:
    """('it', 'IT'): the app's language (APRP_LANG) or the Windows user locale; English/US if unavailable."""
    app_lang = os.environ.get("APRP_LANG", "").lower()
    if app_lang:
        return app_lang, _DEFAULT_COUNTRY.get(app_lang, "US")
    try:
        buf = ctypes.create_unicode_buffer(85)
        if ctypes.windll.kernel32.GetUserDefaultLocaleName(buf, 85):
            lang, _, country = buf.value.partition("-")
            return lang.lower(), (country or "US").upper()[:2]
    except (AttributeError, OSError):
        pass
    return "en", "US"


def _get_json(url: str, timeout: float = 10) -> Optional[dict]:
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except (OSError, ValueError):
        return None


def _clean(text: Optional[str], limit: int = 600) -> Optional[str]:
    if not text:
        return None
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        cut = text.rfind(". ", 0, limit)
        text = text[: cut + 1] if cut > limit // 2 else text[:limit].rstrip() + "…"
    return text or None


def looks_mangled(text: str) -> bool:
    """Epic's catalog cache sometimes stores non-ASCII letters as '?' ("è un" -> "? un")."""
    return bool(re.search(r"\w\?\w|\s\?\s", text))


# ── sources ──────────────────────────────────────────────────────────────────

def steam_details(appid: str, lang: str, country: str) -> dict:
    l = _STEAM_LANG.get(lang, "english")
    data = _get_json(f"https://store.steampowered.com/api/appdetails?appids={appid}&l={l}&cc={country}")
    entry = (data or {}).get(str(appid)) or {}
    if not entry.get("success"):
        return {}
    d = entry.get("data") or {}
    return {
        "description": _clean(d.get("short_description")),
        "developer": ", ".join(d.get("developers") or []) or None,
    }


def steam_search(title: str, lang: str, country: str) -> Optional[str]:
    """Steam appid for an exact (case-insensitive) title match."""
    l = _STEAM_LANG.get(lang, "english")
    q = urllib.parse.quote(title)
    data = _get_json(f"https://store.steampowered.com/api/storesearch/?term={q}&l={l}&cc={country}")
    norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
    for item in (data or {}).get("items") or []:
        if norm(item.get("name", "")) == norm(title):
            return str(item["id"])
    return None


def xbox_details(pfn: str, lang: str, country: str) -> dict:
    url = ("https://displaycatalog.mp.microsoft.com/v7.0/products/lookup?alternateId=PackageFamilyName"
           f"&value={urllib.parse.quote(pfn)}&market={country}&languages={lang}-{country},en-US&fieldsTemplate=details")
    products = (_get_json(url) or {}).get("Products") or []
    if not products:
        return {}
    lp = (products[0].get("LocalizedProperties") or [{}])[0]
    images = {img.get("ImagePurpose"): img.get("Uri") for img in lp.get("Images") or []}
    banner = images.get("SuperHeroArt") or images.get("TitledHeroArt") or images.get("Screenshot")
    cover = images.get("Poster") or images.get("BoxArt")
    fix = lambda u: ("https:" + u) if u and u.startswith("//") else u
    return {
        "description": _clean(lp.get("ShortDescription") or lp.get("ProductDescription")),
        "developer": lp.get("DeveloperName") or lp.get("PublisherName") or None,
        "banner": fix(banner),
        "cover": fix(cover),
    }


def wikipedia_summary(title: str, lang: str) -> Optional[str]:
    for candidate in (f"{title} ({_WIKI_DISAMBIG.get(lang, 'video game')})", title):
        slug = urllib.parse.quote(candidate.replace(" ", "_"))
        d = _get_json(f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{slug}")
        if not d or d.get("type") != "standard":
            continue
        about = (d.get("description") or "").lower()
        if any(w in about for w in _WIKI_GAME_WORDS):
            return _clean(d.get("extract"))
    return None


# ── enrichment ───────────────────────────────────────────────────────────────

def _lookup(game: Game, lang: str, country: str) -> dict:
    meta: dict = {}
    if game.platform == "steam" and game.store_id:
        meta = steam_details(game.store_id, lang, country)
    elif game.platform == "xbox" and game.store_id:
        meta = xbox_details(game.store_id, lang, country)
    elif game.platform == "epic":
        appid = steam_search(game.title, lang, country)
        if appid:
            meta = steam_details(appid, lang, country)

    if not meta.get("description"):
        wiki = wikipedia_summary(game.title, lang)
        if not wiki and lang != "en":
            wiki = wikipedia_summary(game.title, "en")
        if wiki:
            meta["description"] = wiki
    return {k: v for k, v in meta.items() if v}


def _needs_lookup(game: Game) -> bool:
    return not game.description or (game.platform == "xbox" and not game.banner)


def enrich(games: list[Game], online: bool = True, workers: int = 8) -> None:
    """Fill missing description/banner/developer in place.

    Always applies what's already cached; only touches the network when `online`.
    """
    try:
        cache: dict = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    lang, country = user_locale()
    now = time.time()

    def fresh(entry: dict) -> bool:
        ttl = TTL_HIT if entry.get("data") else TTL_MISS
        return entry.get("lang") == lang and now - entry.get("ts", 0) < ttl

    todo = [g for g in games if online and _needs_lookup(g) and not fresh(cache.get(g.id, {}))]
    if todo:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for game, data in zip(todo, pool.map(lambda g: _lookup(g, lang, country), todo)):
                cache[game.id] = {"ts": now, "lang": lang, "data": data}
        try:
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    for g in games:
        data = (cache.get(g.id) or {}).get("data") or {}
        g.description = g.description or data.get("description")
        g.developer = g.developer or data.get("developer")
        g.banner = g.banner or data.get("banner")
        if g.platform == "xbox" and data.get("cover"):
            g.cover = data["cover"]  # store poster beats the square package logo
