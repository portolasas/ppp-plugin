"""What ppp needs on this computer: check it, and install the missing Python packages (PLUGIN PL-29).

ppp setup --check lists each part with ok or missing and what it serves; ppp setup --install installs the missing
Python packages with pip into the Python that runs ppp (with --user outside a virtual environment, since group policies
often block virtual environments) and the ffmpeg of Playwright. Programs (Python itself, git, pac, Edge, Word) ppp does
not install: the report names where they come from. Nothing here signs in or changes a setting.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
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
    if RUNTIME_SETTINGS.parent.is_dir():  # the Copilot runtime of VS Code is there (not with Claude Code alone)
        found.append(runtime_part())
    found += vscode_parts()
    git = shutil.which("git")
    found.append(Part("git", "every project", bool(git), git or "install Git for Windows or the git of your system", True))
    try:
        pac = solution.pac()
        found.append(Part("pac", "ppp unpack, ppp pack", True, pac))
    except ToolError:
        found.append(Part("pac", "ppp unpack, ppp pack", False,
                          "comes with the VS Code extension Power Platform Tools: enable it under Agents view > "
                          "Customizations > Extensions and sign in when it asks"))
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


RUNTIME_SETTINGS = Path.home() / ".copilot" / "settings.json"
MARKETPLACE_REPO = "portolasas/ppp-plugin"
FORMER_REPOS = {"portolasas/bi-design"}  # replaced by bi-design in this marketplace (0.27.0): its copy would show twice
# The Copilot runtime, which runs the Agents view, takes the model of a new session from its own settings; the Agents
# view keeps no model state of a VS Code profile (17.11.: an imported profile left the thinking level at medium, these
# keys gave GPT-6.1 Sol, high, 272K after a restart of VS Code). contextTier default is the small context of 272K.
RUNTIME_WANTED = {"model": "gpt-6.1-sol", "effortLevel": "high", "contextTier": "default"}


def _read_runtime(path: Path) -> dict:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("not a JSON object")
    return data


def _markets(data: dict) -> dict:
    markets = data.get("extraKnownMarketplaces")
    return markets if isinstance(markets, dict) else {}


def _repos(data: dict) -> dict[str, str]:
    out = {}
    for name, entry in _markets(data).items():
        source = entry.get("source") if isinstance(entry, dict) else None
        if isinstance(source, dict) and source.get("repo"):
            out[name] = source["repo"]
    return out


def _in_use(data: dict, name: str, path: Path) -> bool:
    """Whether a plugin of the marketplace name is still enabled or installed (its copy would stay behind)."""
    enabled = data.get("enabledPlugins") if isinstance(data.get("enabledPlugins"), dict) else {}
    return any(k.endswith(f"@{name}") for k in enabled) or (path.parent / "installed-plugins" / name).is_dir()


NAME = "Model of the Agents view"
SERVES = "GPT-6.1 Sol, high, 272K in new sessions"


def runtime_part(path: Path | None = None) -> Part:
    """ok when model, thinking level and context are set (the user may have chosen others, but never a Luna, which
    misses the core rules), the marketplace is known and no former marketplace of bi-design is left."""
    path = path or RUNTIME_SETTINGS
    try:
        data = _read_runtime(path)
    except ValueError as e:  # json.JSONDecodeError is a ValueError
        return Part(NAME, SERVES, False, f"{path} is no plain JSON ({e}; comments are not allowed there): fix it by "
                                         "hand, then ppp setup --vscode")
    wrong = [f"{k} not set" for k in RUNTIME_WANTED if not data.get(k)]
    if "luna" in str(data.get("model", "")).lower():
        wrong.append(f"model {data['model']} misses the core rules")
    if MARKETPLACE_REPO not in _repos(data).values():
        wrong.append(f"marketplace {MARKETPLACE_REPO} missing")
    for name, repo in _repos(data).items():
        if repo in FORMER_REPOS:
            wrong.append(f"former marketplace {repo}" + (": uninstall its plugins first (Customizations)"
                                                         if _in_use(data, name, path) else ""))
    if wrong:
        return Part(NAME, SERVES, False, ", ".join(wrong) + " (ppp setup --vscode)")
    return Part(NAME, SERVES, True, ", ".join(f"{k} {data[k]}" for k in RUNTIME_WANTED))


def write_runtime(path: Path | None = None) -> list[str]:
    """Write model, thinking level, context and the marketplace into the settings of the Copilot runtime; back up the
    file first and keep every other key; remove a former marketplace of bi-design once none of its plugins is enabled
    or installed. Raises ValueError for a file that is no plain JSON object; then nothing is written."""
    path = path or RUNTIME_SETTINGS
    data = _read_runtime(path)
    if "extraKnownMarketplaces" in data and not isinstance(data["extraKnownMarketplaces"], dict):
        raise ValueError("extraKnownMarketplaces is not an object")
    lines = []
    for k, v in RUNTIME_WANTED.items():  # only what is missing, or a Luna: a model the user chose stays (review 17.11.)
        if not data.get(k) or (k == "model" and "luna" in str(data[k]).lower()):
            lines.append(f"Set {k}: {v}" + (f" (was {data[k]!r})" if k in data else ""))
            data[k] = v
    markets = data.setdefault("extraKnownMarketplaces", {})
    for name, repo in list(_repos(data).items()):
        if repo in FORMER_REPOS:
            if _in_use(data, name, path):
                lines.append(f"Kept the former marketplace {name} ({repo}): uninstall its plugins first "
                             "(Customizations), then run ppp setup --vscode again")
            else:
                del markets[name]
                lines.append(f"Removed the former marketplace {name} ({repo}): bi-design comes from {MARKETPLACE_REPO}")
    if MARKETPLACE_REPO not in _repos(data).values():
        name = "ppp" if "ppp" not in markets else "ppp-plugin"  # never replace an entry of another source
        markets[name] = {"source": {"source": "github", "repo": MARKETPLACE_REPO}}
        lines.append(f"Added the marketplace {name} ({MARKETPLACE_REPO})")
    if not any(not l.startswith("Kept") for l in lines):
        return lines + [f"{path} is already as ppp needs it."]
    from .vscode import write_json
    backup = write_json(path, data, indent=2)
    if backup:
        lines.insert(0, f"Backup: {backup}")
    lines.append(f"Written {path}.")
    return lines


def vscode_parts(run=subprocess.run) -> list[Part]:
    """The extensions and settings of ppp in the Default profile of VS Code, when VS Code is on this computer."""
    from . import vscode
    code = vscode.code_command()
    settings_file = vscode.user_settings()
    if not code and not settings_file.parent.is_dir():
        return []
    out = []
    missing, problem = vscode.extension_state(code, run)
    if missing is None:
        out.append(Part("VS Code extensions", "pac, Python, PowerShell in VS Code", False,
                        f"the command line of VS Code: {problem}; install each extension from its link, one click on "
                        f"Install in VS Code: {' '.join(vscode.install_links())}"))
    else:
        out.append(Part("VS Code extensions", "pac, Python, PowerShell in VS Code", not missing,
                        ", ".join(missing) + " missing (ppp setup --vscode)" if missing else "all there"))
    try:
        absent = vscode.missing_settings(vscode.read_settings(settings_file))
        out.append(Part("VS Code settings", "git, diffs and the model of the chat", not absent,
                        ", ".join(absent) + " not set (ppp setup --vscode)" if absent else str(settings_file)))
    except vscode.CommentedJSON:
        out.append(Part("VS Code settings", "git, diffs and the model of the chat", False,
                        f"{settings_file} holds comments, which ppp would lose: add by hand {vscode.missing_as_json()}"))
    except ValueError as e:
        out.append(Part("VS Code settings", "git, diffs and the model of the chat", False,
                        f"{settings_file} is no valid JSON ({e}): fix it, then ppp setup --vscode"))
    except OSError as e:
        out.append(Part("VS Code settings", "git, diffs and the model of the chat", False, f"{settings_file}: {e}"))
    return out


def setup_vscode(run=subprocess.run) -> tuple[list[str], bool]:
    """ppp setup --vscode: the settings of the Copilot runtime, the settings and the extensions of the Default profile.
    Each part on its own: one that cannot be done is reported, the others still run."""
    from . import vscode
    lines, ok = [], True
    for label, step in (("Agents view", write_runtime), ("VS Code settings", vscode.write_settings)):
        try:
            lines += step()
        except vscode.CommentedJSON:
            lines.append(f"{label}: {vscode.user_settings()} holds comments, which ppp would lose; nothing written. "
                         f"Add these settings by hand: {vscode.missing_as_json()}")
            ok = False
        except ValueError as e:
            lines.append(f"{label}: no valid JSON ({e}); nothing written. Fix the file, then ppp setup --vscode again.")
            ok = False
        except OSError as e:  # locked, read-only, an antivirus: the other parts still run
            lines.append(f"{label}: could not write ({e}); nothing changed. Close VS Code, then ppp setup --vscode again.")
            ok = False
    code = vscode.code_command()
    missing, problem = vscode.extension_state(code, run)
    if missing is None:
        lines.append(f"VS Code extensions: the command line of VS Code: {problem}. Install each extension from its "
                     "link instead (paste it into the address bar of the browser, then Install in VS Code):")
        lines += [f"  {link}" for link in vscode.install_links()]
        ok = False
    elif missing:
        done, fine = vscode.install_extensions(code, missing, run)
        lines += done
        ok = ok and fine
    else:
        lines.append("VS Code extensions: all there.")
    lines += ["Close all windows of VS Code and open it again: new sessions of the Agents view then start with "
              "GPT-6.1 Sol, high, 272K.",
              "Then, in the Agents view: Customizations > Extensions, enable each extension of ppp for the Agents view "
              "(an installed extension stays off there until enabled; pac comes with Power Platform Tools); sign in "
              "with the Microsoft work account when Power Platform Tools asks (pac needs it for environments and "
              "solutions); then start a new chat and say \"check ppp\" there (ppp setup --check)."]
    return lines, ok


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
    vscode = [p.name for p in found if not p.ok and "ppp setup --vscode" in p.detail]
    if required:
        lines.append(f"RESULT: incomplete, required: {', '.join(required)}")
    elif installable or other:
        lines.append("RESULT: ppp works; missing for single commands: " + ", ".join(installable + other))
    else:
        lines.append("RESULT: complete")
    if installable:
        lines.append(f"  ppp setup --install installs: {', '.join(installable)}")
    if vscode:
        lines.append(f"  ppp setup --vscode sets: {', '.join(vscode)}")
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
