"""Reader for Steam's binary appcache/appinfo.vdf.

This is where the client keeps metadata (name, type) for every app it knows,
including owned games that aren't installed. Only the "common" section is read.

Layout (v28/v29):
  header:  u32 magic, u32 universe, [v29: i64 string_table_offset]
  entries: u32 appid (0 = end), u32 size, then `size` bytes:
           u32 info_state, u32 last_updated, u64 pics_token, 20B sha1,
           u32 change_number, 20B binary_sha1, binary KeyValues
  v29 keys are i32 indexes into a string table (u32 count + NUL-terminated strings).
"""
from __future__ import annotations

import struct
from pathlib import Path
from typing import Optional

MAGIC_V28 = 0x07564428
MAGIC_V29 = 0x07564429
_ENTRY_HEADER = 4 + 4 + 8 + 20 + 4 + 20


class _KVReader:
    def __init__(self, data: bytes, pos: int, strings: Optional[list[str]]):
        self.data, self.pos, self.strings = data, pos, strings

    def _cstr(self) -> str:
        end = self.data.index(b"\x00", self.pos)
        s = self.data[self.pos:end].decode("utf-8", "replace")
        self.pos = end + 1
        return s

    def _key(self) -> str:
        if self.strings is None:
            return self._cstr()
        (idx,) = struct.unpack_from("<i", self.data, self.pos)
        self.pos += 4
        return self.strings[idx]

    def read_object(self) -> dict:
        obj: dict = {}
        while True:
            t = self.data[self.pos]
            self.pos += 1
            if t in (0x08, 0x0B):  # end of object
                return obj
            key = self._key().lower()
            if t == 0x00:
                obj[key] = self.read_object()
            elif t == 0x01:
                obj[key] = self._cstr()
            elif t in (0x02, 0x04, 0x06):
                obj[key] = struct.unpack_from("<i", self.data, self.pos)[0]
                self.pos += 4
            elif t == 0x03:
                obj[key] = struct.unpack_from("<f", self.data, self.pos)[0]
                self.pos += 4
            elif t == 0x07:
                obj[key] = struct.unpack_from("<Q", self.data, self.pos)[0]
                self.pos += 8
            elif t == 0x0A:
                obj[key] = struct.unpack_from("<q", self.data, self.pos)[0]
                self.pos += 8
            elif t == 0x05:  # UTF-16 string, NUL-terminated
                end = self.pos
                while self.data[end:end + 2] != b"\x00\x00":
                    end += 2
                obj[key] = self.data[self.pos:end].decode("utf-16-le", "replace")
                self.pos = end + 2
            else:
                raise ValueError(f"unknown KV type 0x{t:02x}")


def read_common(path: Path) -> dict[str, dict]:
    """Return {appid: common-section dict} (keys lower-cased: name, type, ...)."""
    data = path.read_bytes()
    magic, _universe = struct.unpack_from("<II", data, 0)
    pos = 8
    strings: Optional[list[str]] = None
    if magic == MAGIC_V29:
        (table_offset,) = struct.unpack_from("<q", data, pos)
        pos += 8
        (count,) = struct.unpack_from("<I", data, table_offset)
        strings = data[table_offset + 4:].split(b"\x00", count)[:count]
        strings = [s.decode("utf-8", "replace") for s in strings]
    elif magic != MAGIC_V28:
        raise ValueError(f"unsupported appinfo.vdf version 0x{magic:08x}")

    apps: dict[str, dict] = {}
    while pos + 8 <= len(data):
        appid, size = struct.unpack_from("<II", data, pos)
        if appid == 0:
            break
        body = pos + 8
        try:
            kv = _KVReader(data, body + _ENTRY_HEADER, strings).read_object()
            common = kv.get("appinfo", kv).get("common")
            if isinstance(common, dict):
                apps[str(appid)] = common
        except (ValueError, IndexError, struct.error):
            pass  # one corrupt entry shouldn't hide the rest
        pos = body + size
    return apps
