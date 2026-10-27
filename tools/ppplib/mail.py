"""ppp mail: an Outlook message (.msg) as text and files, without Outlook (GEN-20261026-WIN-01).

A .msg is an OLE compound file. Outlook COM hung on such files and kept them locked, so this reads the file itself with
the standard library: properties are streams __substg1.0_<tag><type> (001F UTF-16, 001E code page, 0102 binary),
attachments storages __attach_version1.0_#… with file name 3707/3704 and data 3701.
"""
from __future__ import annotations

import html
import re
import struct
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path

from .project import ToolError

SIGNATURE = bytes.fromhex("D0CF11E0A1B11AE1")
FREE, END, NOSTREAM = 0xFFFFFFFF, 0xFFFFFFFE, 0xFFFFFFFF
TIMES = ("0039", "0E06")  # client submit time, delivery time


class Compound:
    """Streams of an OLE compound file as {"storage/stream": bytes}, names in lower case."""

    def __init__(self, data: bytes):
        if data[:8] != SIGNATURE:
            raise ToolError("not an Outlook .msg (no OLE compound file)")
        self.data = data
        self.size = 1 << struct.unpack_from("<H", data, 0x1E)[0]
        self.mini_size = 1 << struct.unpack_from("<H", data, 0x20)[0]
        n_fat, first_dir, _, self.cutoff, first_mini, n_mini, first_difat, n_difat = struct.unpack_from("<8I", data, 0x2C)
        fat_sectors = [s for s in struct.unpack_from("<109I", data, 0x4C) if s != FREE]
        s = first_difat
        for _ in range(n_difat):
            if s in (FREE, END):
                break
            entries = struct.unpack_from(f"<{self.size // 4}I", self._sector(s))
            fat_sectors += [x for x in entries[:-1] if x != FREE]
            s = entries[-1]
        self.fat = [x for f in fat_sectors[:n_fat] for x in struct.unpack_from(f"<{self.size // 4}I", self._sector(f))]
        self.minifat = []
        if n_mini:
            raw = self._chain(first_mini)
            self.minifat = list(struct.unpack_from(f"<{len(raw) // 4}I", raw))
        raw = self._chain(first_dir)
        self.entries = [raw[i:i + 128] for i in range(0, len(raw), 128)]
        root = self._entry(0)
        self.ministream = self._chain(root["start"])[:root["size"]] if root["size"] else b""
        self.streams: dict[str, bytes] = {}
        self._walk(root["child"], "")

    def _sector(self, n: int) -> bytes:
        return self.data[(n + 1) * self.size:(n + 2) * self.size]

    def _chain(self, start: int) -> bytes:
        out, s, seen = [], start, set()
        while s not in (END, FREE) and s < len(self.fat) and s not in seen:
            seen.add(s)
            out.append(self._sector(s))
            s = self.fat[s]
        return b"".join(out)

    def _mini_chain(self, start: int, size: int) -> bytes:
        out, s, seen = [], start, set()
        while s not in (END, FREE) and s < len(self.minifat) and s not in seen:
            seen.add(s)
            out.append(self.ministream[s * self.mini_size:(s + 1) * self.mini_size])
            s = self.minifat[s]
        return b"".join(out)[:size]

    def _entry(self, i: int) -> dict:
        e = self.entries[i]
        length = struct.unpack_from("<H", e, 64)[0]
        left, right, child = struct.unpack_from("<3I", e, 68)
        start, size = struct.unpack_from("<IQ", e, 116)
        if self.size == 512:
            size &= 0xFFFFFFFF
        return {"name": e[:max(length - 2, 0)].decode("utf-16-le", "replace"), "type": e[66], "left": left,
                "right": right, "child": child, "start": start, "size": size}

    def _walk(self, i: int, prefix: str, seen: set | None = None) -> None:
        seen = set() if seen is None else seen
        if i == NOSTREAM or i >= len(self.entries) or i in seen:
            return
        seen.add(i)
        e = self._entry(i)
        self._walk(e["left"], prefix, seen)
        self._walk(e["right"], prefix, seen)
        path = prefix + e["name"].lower()
        if e["type"] == 1:
            self._walk(e["child"], path + "/", seen)
        elif e["type"] == 2:
            small = e["size"] < self.cutoff
            self.streams[path] = (self._mini_chain(e["start"], e["size"]) if small else self._chain(e["start"])[:e["size"]])


class _Text(HTMLParser):
    BREAKS = {"br", "p", "div", "tr", "li", "h1", "h2", "h3", "table"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script", "head"):
            self.skip += 1
        elif tag in self.BREAKS:
            self.parts.append("\n")
        elif tag == "td":
            self.parts.append("\t")

    def handle_endtag(self, tag):
        if tag in ("style", "script", "head"):
            self.skip = max(0, self.skip - 1)
        elif tag in self.BREAKS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_text(raw: str) -> str:
    p = _Text()
    p.feed(raw)
    text = html.unescape("".join(p.parts)).replace("\xa0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _value(streams: dict, prefix: str, tag: str):
    for kind in ("001f", "001e", "0102"):
        raw = streams.get(f"{prefix}__substg1.0_{tag.lower()}{kind}")
        if raw is not None:
            if kind == "001f":
                return raw.decode("utf-16-le", "replace").rstrip("\x00")
            if kind == "001e":
                return raw.decode("cp1252", "replace").rstrip("\x00")
            return raw
    return None


def _time(streams: dict) -> str:
    props = streams.get("__properties_version1.0", b"")
    found = {}
    for i in range(32, len(props) - 15, 16):
        ptype, pid = struct.unpack_from("<HH", props, i)
        if ptype == 0x0040:
            found[f"{pid:04X}"] = struct.unpack_from("<Q", props, i + 8)[0]
    for tag in TIMES:
        if found.get(tag):
            t = datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=found[tag] // 10)
            return t.strftime("%Y-%m-%d %H:%M UTC")
    return ""


def read(path: Path) -> dict:
    """Subject, sender, recipients, date, body and attachments (name, bytes) of a .msg."""
    try:
        streams = Compound(path.read_bytes()).streams
    except (OSError, struct.error, IndexError) as ex:
        raise ToolError(f"{path.name}: not readable as .msg ({ex})") from ex
    body = _value(streams, "", "1000")
    if not body:
        raw = _value(streams, "", "1013")
        if isinstance(raw, bytes):
            m = re.search(rb"charset=[\"']?([A-Za-z0-9_-]+)", raw[:2000])
            try:
                raw = raw.decode(m.group(1).decode() if m else "utf-8")
            except (LookupError, UnicodeDecodeError):
                raw = raw.decode("cp1252", "replace")
        body = html_text(raw) if raw else ""
    attachments, names = [], {}
    for folder in sorted({k.split("/")[0] for k in streams if k.startswith("__attach_version1.0_#")}):
        prefix = folder + "/"
        name = _value(streams, prefix, "3707") or _value(streams, prefix, "3704") or f"{folder[-8:]}.bin"
        data = streams.get(prefix + "__substg1.0_37010102")
        if data is None:
            name += " (embedded message, not extracted)"
        stem, suffix = Path(name).stem, Path(name).suffix
        names[name] = names.get(name, 0) + 1
        if names[name] > 1:  # equal names (image.png) would overwrite each other
            name = f"{stem}_{names[name]}{suffix}"
        attachments.append((name, data))
    sender = _value(streams, "", "0C1A") or ""
    address = _value(streams, "", "5D01") or _value(streams, "", "0C1F") or ""
    return {"subject": _value(streams, "", "0037") or "", "from": f"{sender} <{address}>" if address else sender,
            "to": _value(streams, "", "0E04") or "", "cc": _value(streams, "", "0E03") or "", "date": _time(streams),
            "body": (body or "").strip(), "attachments": attachments}


def show(path: Path, out: Path | None = None) -> list[str]:
    m = read(path)
    lines = [f"Subject: {m['subject']}", f"From: {m['from']}", f"To: {m['to']}"]
    lines += [f"Cc: {m['cc']}"] if m["cc"] else []
    lines += [f"Date: {m['date']}"] if m["date"] else []
    if out:
        out.mkdir(parents=True, exist_ok=True)
    for name, data in m["attachments"]:
        if out and data is not None:
            (out / name).write_bytes(data)
        lines.append(f"Attachment: {name}" + (f" ({len(data)} bytes)" if data is not None else ""))
    if m["attachments"] and not out:
        lines.append("(--out <folder> writes the attachments)")
    lines += ["", m["body"] or "(no text or HTML body)"]
    return lines
