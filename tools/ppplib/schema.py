"""Check components/sharepoint/schema.json, the source of the setup flow (ANFORDERUNGEN T3).

The keys stay those of the former listen_definition.json (German), so that existing definitions, setup flows and
tests carry over without loss (UEBERGANG Ü-13; user decision 2026-10-20). Format:
  schemaVersion (or version), optionen (CreateFieldAsXml options, default 25), hinweis, generiert,
  listen: [{titel, beschreibung, basis (100 list, 101 library), titelFeld {Indexed, EnforceUniqueValues},
            felder: [{name, schemaXml, werte (choice values to add to an existing field)}]}],
  daten: [{liste, schluessel, items: [...]}]   start values, inserted only for missing keys,
  setup: {laufListe, versionEinstellung {liste, titel}, ersterAdmin {liste, rolle}}   optional parts of the setup flow.
"""
from __future__ import annotations

import json
import re
import xml.dom.minidom
from pathlib import Path

from .report import Report

FIELD_TYPES = {"Text", "Note", "Number", "Integer", "Currency", "Boolean", "DateTime", "Choice", "MultiChoice", "User",
               "UserMulti", "Lookup", "LookupMulti", "URL", "Calculated", "Thumbnail", "Location", "Image"}
TOP_KEYS = {"schemaVersion", "version", "optionen", "hinweis", "generiert", "listen", "daten", "setup"}
LIST_KEYS = {"titel", "beschreibung", "basis", "titelFeld", "felder"}
FIELD_KEYS = {"name", "schemaXml", "werte"}
# fields the optional setup parts write (ASUM pattern)
RUN_LOG_FIELDS = ("Art", "Status", "Modus", "Start", "Ende", "Ergebnis", "Meldung")
VERSION_FIELDS = ("Wert", "Beschreibung")
ADMIN_FIELDS = ("Rolle", "Aktiv")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def fields_of(lst: dict) -> dict[str, dict]:
    """name -> {type, choices, xml} of the fields of a list definition; Title always exists."""
    out = {"Title": {"type": "Text", "choices": []}}
    for f in lst.get("felder") or []:
        try:
            x = xml.dom.minidom.parseString(f.get("schemaXml", "")).documentElement
        except Exception:  # noqa: BLE001 – reported by check()
            continue
        out[f.get("name")] = {"type": x.getAttribute("Type"),
                              "choices": [c.firstChild.data for c in x.getElementsByTagName("CHOICE") if c.firstChild]}
    return out


def check(d: dict, prefix: str | None, rep: Report) -> None:
    unknown = set(d) - TOP_KEYS
    if unknown:
        rep.warn("schema: unknown top-level keys " + ", ".join(sorted(unknown)))
    if not isinstance(d.get("schemaVersion", d.get("version")), str):
        rep.error("schema: schemaVersion (text) missing")
    if not isinstance(d.get("optionen", 25), int):
        rep.error("schema: optionen must be a number (CreateFieldAsXml options, usually 25)")
    lists = d.get("listen")
    if not isinstance(lists, list) or not lists:
        rep.error("schema: listen missing or empty")
        return
    titles = {}
    for i, lst in enumerate(lists):
        title = lst.get("titel")
        where = f"list {title or i}"
        if not isinstance(title, str) or not title:
            rep.error(f"schema: {where}: titel missing")
            continue
        if title in titles:
            rep.error(f"schema: list {title} defined twice")
        titles[title] = lst
        if prefix and not title.startswith(prefix + "_"):
            rep.warn(f"schema: {where}: title does not start with the prefix {prefix}_ (P5)")
        if set(lst) - LIST_KEYS:
            rep.warn(f"schema: {where}: unknown keys " + ", ".join(sorted(set(lst) - LIST_KEYS)))
        if lst.get("basis", 100) not in (100, 101):
            rep.error(f"schema: {where}: basis must be 100 (list) or 101 (library)")
        tf = lst.get("titelFeld")
        if tf is not None and (not isinstance(tf, dict) or any(not isinstance(tf.get(k), bool) for k in tf)):
            rep.error(f"schema: {where}: titelFeld needs true/false values (Indexed, EnforceUniqueValues)")
        names = set()
        for f in lst.get("felder") or []:
            name = f.get("name")
            fw = f"{where}, field {name}"
            if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name):
                rep.error(f"schema: {fw}: name must be letters, digits and _ (internal name)")
                continue
            if len(name) > 32:
                rep.warn(f"schema: {fw}: internal names longer than 32 characters are cut by SharePoint")
            if name in names or name == "Title":
                rep.error(f"schema: {fw}: defined twice" if name in names else f"schema: {fw}: Title exists already; use titelFeld")
            names.add(name)
            if set(f) - FIELD_KEYS:
                rep.warn(f"schema: {fw}: unknown keys " + ", ".join(sorted(set(f) - FIELD_KEYS)))
            try:
                x = xml.dom.minidom.parseString(f.get("schemaXml", "")).documentElement
            except Exception as ex:  # noqa: BLE001
                rep.error(f"schema: {fw}: schemaXml not parsable: {ex}")
                continue
            if x.tagName != "Field":
                rep.error(f"schema: {fw}: schemaXml must be one <Field>")
            if x.getAttribute("Name") != name or (x.getAttribute("StaticName") and x.getAttribute("StaticName") != name):
                rep.error(f"schema: {fw}: Name/StaticName in schemaXml differ from name")
            kind = x.getAttribute("Type")
            if kind not in FIELD_TYPES:
                rep.error(f"schema: {fw}: unknown Type {kind!r}")
            choices = [c.firstChild.data for c in x.getElementsByTagName("CHOICE") if c.firstChild]
            if kind in ("Choice", "MultiChoice") and not choices:
                rep.error(f"schema: {fw}: choice field without CHOICES")
            if "werte" in f:
                if kind not in ("Choice", "MultiChoice"):
                    rep.error(f"schema: {fw}: werte only for choice fields")
                elif [w for w in f["werte"] if w not in choices]:
                    rep.error(f"schema: {fw}: werte not in CHOICES: " + ", ".join(w for w in f["werte"] if w not in choices))
                elif list(f["werte"]) != choices:
                    rep.warn(f"schema: {fw}: werte differ from CHOICES; existing fields get only the values in werte")
    for block in d.get("daten") or []:
        lst, key = block.get("liste"), block.get("schluessel")
        where = f"daten {lst}"
        if lst not in titles:
            rep.error(f"schema: {where}: list not defined in listen")
            continue
        fields = fields_of(titles[lst])
        if key not in fields:
            rep.error(f"schema: {where}: schluessel {key!r} is no field of the list")
        seen = set()
        for item in block.get("items") or []:
            if key in fields and item.get(key) in seen:
                rep.error(f"schema: {where}: key {item.get(key)!r} twice")
            seen.add(item.get(key))
            for k, v in item.items():
                if k not in fields:
                    rep.error(f"schema: {where}: field {k} does not exist")
                elif fields[k]["type"] == "Choice" and v is not None and v not in fields[k]["choices"]:
                    rep.error(f"schema: {where}: {k}={v!r} not in CHOICES")
    setup = d.get("setup") or {}
    if setup and not isinstance(setup, dict):
        rep.error("schema: setup must be an object")
        return
    needs = []
    if setup.get("laufListe"):
        needs.append(("laufListe", setup["laufListe"], RUN_LOG_FIELDS))
    for key, fieldset in (("versionEinstellung", VERSION_FIELDS), ("ersterAdmin", ADMIN_FIELDS)):
        part = setup.get(key)
        if part is not None:
            if not isinstance(part, dict) or not part.get("liste") or not part.get("titel" if key == "versionEinstellung" else "rolle"):
                rep.error(f"schema: setup.{key} needs liste and {'titel' if key == 'versionEinstellung' else 'rolle'}")
                continue
            needs.append((key, part["liste"], fieldset))
    for key, lst, fieldset in needs:
        if lst not in titles:
            rep.error(f"schema: setup.{key}: list {lst} not defined in listen")
            continue
        missing = [f for f in fieldset if f not in fields_of(titles[lst])]
        if missing:
            rep.error(f"schema: setup.{key}: list {lst} lacks the fields " + ", ".join(missing))
    admin = setup.get("ersterAdmin")
    if isinstance(admin, dict) and admin.get("liste") in titles:
        role = fields_of(titles[admin["liste"]]).get("Rolle") or {}
        if role.get("type") == "Choice" and admin.get("rolle") not in role.get("choices", []):
            rep.error(f"schema: setup.ersterAdmin: rolle {admin.get('rolle')!r} not in the CHOICES of Rolle")
    rep.info(f"schema: {len(lists)} lists, {sum(len(l.get('felder') or []) for l in lists)} fields, "
             f"{len(d.get('daten') or [])} start value blocks" + (", setup parts: " + ", ".join(sorted(setup)) if setup else ""))
