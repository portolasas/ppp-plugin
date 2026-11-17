"""What ppp needs on this computer: check it, and install the missing Python packages (PLUGIN PL-29).

ppp setup --check lists each part with ok or missing and what it serves; ppp setup --install installs the missing
Python packages with pip into the Python that runs ppp (with --user outside a virtual environment, since group policies
often block virtual environments) and the ffmpeg of Playwright. Programs (Python itself, git, pac, Edge, Word) ppp does
not install: the report names where they come from. Nothing here signs in or changes a setting.
"""
from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent.parent
BIDESIGN_REQUIREMENTS = PLUGIN / "bi-design" / "tools" / "requirements.txt"
MIN_PYTHON = (3, 10)


@dataclass
class Part:
    name: str
    serves: str          # what needs it
    ok: bool
    detail: str = ""     # where it was found, or how to get it
    required: bool = False
    package: str = ""    # PyPI package that ppp setup --install installs
    ffmpeg: bool = False  # ppp setup --install runs "playwright install ffmpeg"


FIND = ("import importlib.util, sys\n"
        "def found(m):\n"
        "    try:\n"
        "        return importlib.util.find_spec(m) is not None\n"
        "    except (ImportError, ValueError):\n"
        "        return False\n"
        "print('\\n'.join(m for m in sys.argv[1:] if not found(m)))\n")


def missing_modules(modules: list[str]) -> set[str]:
    """The modules the Python of ppp cannot import, looked up in a child process: ppp runs with python -I, which hides
    the packages installed with --user, while ppp walk, ppp guide and ppp run start their children without -I (review
    17.11.: the check reported python-pptx and pymupdf as missing although they were installed)."""
    if not modules:
        return set()
    try:
        proc = subprocess.run([sys.executable, "-B", "-c", FIND, *modules], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=60)
        if proc.returncode == 0:
            return {line.strip() for line in proc.stdout.splitlines() if line.strip()}
    except (OSError, subprocess.SubprocessError):
        pass
    out = set()
    for m in modules:  # fallback: in this process
        try:
            if importlib.util.find_spec(m) is None:
                out.add(m)
        except (ImportError, ValueError):
            out.add(m)
    return out


def _first(paths: list[Path]) -> Path | None:
    return next((p for p in paths if p.is_file()), None)


def edge() -> Path | None:
    if sys.platform == "win32":
        bases = [os.environ.get(v) for v in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA")]
        return _first([Path(b) / "Microsoft" / "Edge" / "Application" / "msedge.exe" for b in bases if b])
    if sys.platform == "darwin":
        return _first([Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge")])
    found = shutil.which("microsoft-edge") or shutil.which("microsoft-edge-stable")
    return Path(found) if found else None


def word() -> Path | None:
    if sys.platform == "win32":
        try:
            import winreg
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    with winreg.OpenKey(hive, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\Winword.exe") as key:
                        value = Path(winreg.QueryValue(key, None).strip('"'))
                        if value.is_file():
                            return value
                except OSError:
                    continue
        except ImportError:
            pass
        bases = [os.environ.get(v) for v in ("ProgramFiles", "ProgramFiles(x86)")]
        return _first([Path(b) / "Microsoft Office" / "root" / f"Office{n}" / "WINWORD.EXE"
                       for b in bases if b for n in (16, 15)])
    if sys.platform == "darwin":
        return _first([Path("/Applications/Microsoft Word.app/Contents/MacOS/Microsoft Word")])
    return None


def playwright_ffmpeg() -> Path | None:
    """The ffmpeg that Playwright downloads for recordings (ppp walk --video)."""
    custom = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if custom and custom != "0":
        base = Path(custom)
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "ms-playwright"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches" / "ms-playwright"
    else:
        base = Path.home() / ".cache" / "ms-playwright"
    found = sorted(base.glob("ffmpeg-*")) if base.is_dir() else []
    return found[-1] if found else None


REQUIREMENT_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def _requirements(path: Path) -> list[tuple[str, str, str]]:
    """(module, name, requirement for pip) for each line of a requirements file of bi-design; only presence counts."""
    modules = {"python-pptx": "pptx", "python-docx": "docx", "pymupdf": "pymupdf", "pillow": "PIL", "openpyxl": "openpyxl"}
    out = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.split("#")[0].split(";")[0].strip()  # no comment, no environment marker
            m = REQUIREMENT_NAME.match(line)
            if m:
                name = m.group()
                out.append((modules.get(name.lower(), name.lower().replace("-", "_")), name, line))
    return out


def parts() -> list[Part]:
    from . import agent, solution
    from .project import ToolError
    py = sys.version_info[:2]
    requirements = [r for r in _requirements(BIDESIGN_REQUIREMENTS) if r[0] != "docx"]
    missing = missing_modules(["playwright", "docx", *[module for module, _, _ in requirements]])
    found = []
    found.append(Part("Python", "ppp", py >= MIN_PYTHON, f"{sys.version.split()[0]} at {sys.executable}"
                      + ("" if py >= MIN_PYTHON else f": ppp needs {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer"), True))
    if sys.platform == "win32":
        recorded = agent.recorded_python()
        on_path = shutil.which("python")
        on_path = on_path if on_path and not agent._store_stub(on_path) else None
        found.append(Part("Python of the VS Code hooks", "the rules of ppp in VS Code", bool(recorded or on_path),
                          f"{recorded} (from {agent.PYTHON_FILE})" if recorded else
                          f"{on_path} on PATH" if on_path else
                          "none recorded and none on PATH: run ppp setup once with this Python"))
    git = shutil.which("git")
    found.append(Part("git", "every project", bool(git), git or "install Git for Windows or the git of your system", True))
    try:
        pac = solution.pac()
        found.append(Part("pac", "ppp unpack, ppp pack", True, pac))
    except ToolError:
        found.append(Part("pac", "ppp unpack, ppp pack", False, "install the VS Code extension Power Platform Tools"))
    found.append(Part("playwright", "ppp walk", "playwright" not in missing, "", package="playwright"))
    e = edge()
    found.append(Part("Microsoft Edge", "ppp walk", bool(e), str(e) if e else "install Microsoft Edge"))
    ff = playwright_ffmpeg()
    found.append(Part("ffmpeg of Playwright", "ppp walk --video", bool(ff), str(ff) if ff else "", ffmpeg=True))
    found.append(Part("python-docx", "ppp guide", "docx" not in missing, "", package="python-docx"))
    w = word()
    found.append(Part("Microsoft Word", "ppp guide --word", bool(w), str(w) if w else "install Microsoft Word"))
    for module, name, requirement in requirements:
        found.append(Part(name, "bi-design (bippt), ppp guide --kind deck", module not in missing, "", package=requirement))
    return found


def report(found: list[Part]) -> list[str]:
    lines = []
    for p in found:
        state = "ok" if p.ok else ("MISSING" if p.required else "missing")
        how = p.detail
        if not p.ok and (p.package or p.ffmpeg):
            how = "ppp setup --install"
        lines.append(f"  {state:8} {p.name:28} {p.serves}" + (f"  ({how})" if how else ""))
    required = [p.name for p in found if p.required and not p.ok]
    installable = [p.name for p in found if not p.ok and (p.package or p.ffmpeg)]
    other = [p.name for p in found if not p.ok and not p.required and not (p.package or p.ffmpeg)]
    if required:
        lines.append(f"RESULT: incomplete, required: {', '.join(required)}")
    elif installable or other:
        lines.append("RESULT: ppp works; missing for single commands: " + ", ".join(installable + other))
    else:
        lines.append("RESULT: complete")
    if installable:
        lines.append(f"  ppp setup --install installs: {', '.join(installable)}")
    return lines


def pip_command(packages: list[str]) -> list[str]:
    command = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "-q", "-U"]
    if sys.prefix == getattr(sys, "base_prefix", sys.prefix):
        command.append("--user")  # no virtual environment: group policies often block them
    return command + packages


def install(found: list[Part], run=subprocess.run) -> tuple[list[str], bool]:
    """Install the missing packages, then the ffmpeg of Playwright; returns the lines and whether all went through."""
    lines, ok = [], True
    packages = [p.package for p in found if not p.ok and p.package]
    if packages:
        command = pip_command(packages)
        lines.append("Running: " + " ".join(f'"{x}"' if " " in x else x for x in command))
        if run(command).returncode:
            lines.append("pip failed. Behind a proxy: pip config set global.proxy http://<proxy>:<port>, then again.")
            ok = False
    if ok and any(not p.ok and p.ffmpeg for p in found):
        command = [sys.executable, "-m", "playwright", "install", "ffmpeg"]
        lines.append("Running: " + " ".join(f'"{x}"' if " " in x else x for x in command))
        if run(command).returncode:
            lines.append("playwright install ffmpeg failed (ppp walk works without it, only --video needs it).")
            ok = False
    if not packages and not any(not p.ok and p.ffmpeg for p in found):
        lines.append("Nothing to install.")
    return lines, ok
