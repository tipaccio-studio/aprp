"""Minimal parser for Valve's KeyValues text format (.vdf / .acf).

Steam's own files only use quoted tokens, so that is all we support.
Keys are lower-cased because Steam is inconsistent ("LibraryFolders" vs "libraryfolders").
"""
from __future__ import annotations

import re

_TOKEN = re.compile(r'"((?:[^"\\]|\\.)*)"|([{}])')
_ESCAPES = {"\\\\": "\\", '\\"': '"', "\\n": "\n", "\\t": "\t"}


def _unescape(s: str) -> str:
    return re.sub(r"\\[\\\"nt]", lambda m: _ESCAPES[m.group(0)], s)


def loads(text: str) -> dict:
    root: dict = {}
    stack = [root]
    key = None
    for m in _TOKEN.finditer(text):
        brace = m.group(2)
        if brace == "{":
            child: dict = {}
            stack[-1][key or ""] = child
            stack.append(child)
            key = None
        elif brace == "}":
            if len(stack) > 1:
                stack.pop()
        else:
            value = _unescape(m.group(1))
            if key is None:
                key = value.lower()
            else:
                stack[-1][key] = value
                key = None
    return root


def load(path) -> dict:
    with open(path, encoding="utf-8", errors="replace") as f:
        return loads(f.read())
