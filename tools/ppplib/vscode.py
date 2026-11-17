"""VS Code for ppp: the extensions and settings ppp sets up, in one place (PLUGIN PL-28).

The same definition builds the profile plugin/setup/ppp.code-profile (tools/vscode_profile.py) and is what
ppp setup --vscode brings into the Default profile without an import: the extensions with `code --install-extension`,
the settings merged into the user settings.json. Pinned and hidden models are UI state in VS Code's own database, which
VS Code holds while it runs; only the profile carries them. No setting that turns on further hooks (such as
chat.useClaudeHooks), and no choice that is each user's own (workspace trust, session sync, approvals).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Settings a profile other than the Default profile can carry too: VS Code takes settings of application scope, such as
# chat.plugins.marketplaces and extensions.autoUpdate, from the Default profile only (1.146.0). The marketplace comes
# with the install link and ~/.copilot/settings.json, extensions.autoUpdate is on by default.
SETTINGS = {
    "chat.plugins.enabled": True,
    "chat.defaultModel": "gpt-6.1-sol",            # the chat outside the Agents view; the core rules recommend it
    "git.autofetch": True,                        # ppp works with git pull: new states show early
    "git.confirmSync": False,
    "git.enableSmartCommit": True,
    "diffEditor.maxComputationTime": 0,           # diffs of large solution XML would stop otherwise
    "terminal.integrated.initialHint": False,
    "chat.viewSessions.orientation": "stacked",
}
# The model of the chat in the normal window is UI state, not a setting (export of the user's profile, 17.11.): the
# chosen model per picker and its thinking level and context size per model. The Agents view has a built-in profile of
# its own and takes them from ~/.copilot/settings.json (ppp setup --vscode); only pinned and hidden models reach it,
# once. 272,000 is the small context, whose price does not double.
AGENTS = "agent-host-copilotcli"
# Pinned and hidden models are kept per computer in the Agents view; the normal window copies them once from its
# profile (chatModelPreferences.agentsWindowMigrated), so a profile hides them on a fresh computer only (17.11.).
# Visible: GPT-6.1 Sol, Claude Opus 5.5, Claude Sonnet 5.5, Claude Haiku 5.5 and GPT-6 Astra as the second GPT model when
# Sol is not available (user, 17.11.). Hidden: every other model the Agents view offered on 17.11.2026, every Luna among
# them, since GPT-6 Luna misses the core rules; a model that comes later stays visible.
VISIBLE = ["gpt-6.1-sol", "claude-opus-5.5", "claude-sonnet-5.5", "claude-haiku-5.5", "gpt-6-astra"]
HIDDEN = ["auto", "hydrafusion", "hydrafusion-max", "claude-fable-5.2", "claude-fable-5.1", "claude-fable-5",
          "claude-sonnet-5", "claude-opus-4.8-fast", "claude-haiku-4.5", "gpt-6.1-terra", "gpt-6-sol", "gpt-6-luna",
          "gpt-5.6-sol", "gpt-5.6-luna", "gpt-5.3-codex", "mai-code-1.1-flash", "gemini-4-argon", "gemini-4-carbon",
          "gemini-4-hydrogen", "gemini-3.8-flash", "grok-4.7", "grok-4.6", "kimi-k3"]
GLOBAL_STATE = {
    f"chat.currentLanguageModel.panel.{AGENTS}": f"{AGENTS}:gpt-6.1-sol",
    f"chat.modelConfiguration.panel.{AGENTS}": json.dumps({
        f"{AGENTS}:gpt-6.1-sol": {"thinkingLevel": "high", "contextSize": 272000},
        f"{AGENTS}:claude-opus-5.5": {"thinkingLevel": "high", "contextSize": 200000}}),
    "chatModelPinned": json.dumps([f"{AGENTS}:gpt-6.1-sol", f"{AGENTS}:claude-opus-5.5"]),
    "chatModelVisibility": json.dumps({"hiddenModels": [f"{AGENTS}:{m}" for m in HIDDEN]}),
}
# id, uuid and display name as the Marketplace gives them (17.11.2026); applicationScoped as in the templates of VS Code.
# Not GitHub Copilot Chat: VS Code has it built in (1.146.0: GitHub.copilot-chat 0.74.0), so an import skips it.
EXTENSIONS = [
    ("microsoft-isvexptools.powerplatform-vscode", "b8680bb6-eaa9-481a-ae0b-83574fa58620", "Power Platform Tools", False),
    ("ms-python.python", "f1f59ae4-9318-4f3c-a9b5-81b2eaa5f8a5", "Python", False),
    # the extension pack of Python, which an import does not install by itself (1.146.0): Python Environments brings
    # the Python icon in the activity bar
    ("ms-python.vscode-python-envs", "b41d8e8a-b6d4-4202-8f07-7189bdda81be", "Python Environments", False),
    ("ms-python.vscode-pylance", "364d2426-116a-433a-a5d8-a5098dc3afbd", "Pylance", False),
    ("ms-python.debugpy", "4bd5d2c9-9d65-401a-b0b2-7498d9f17615", "Python Debugger", False),
    ("ms-vscode.powershell", "40d39ce9-c381-47a0-80c8-a6661f731eab", "PowerShell", False),
]


# --- the Default profile -------------------------------------------------------------------------------------------

def user_settings() -> Path:
    """settings.json of the Default profile of VS Code."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "Code" / "User" / "settings.json"


BLOCKED = ("gruppenrichtlinie", "group policy", "blocked by your system administrator", "applocker")


def _windows_direct(launcher: Path) -> list[str] | None:
    """Code.exe with cli.js, which code.cmd starts with ELECTRON_RUN_AS_NODE=1: a group policy may block the batch file
    code.cmd in the user folder while Code.exe may run (first run on the company computer, 17.11.)."""
    root = launcher.parent.parent
    exe = root / "Code.exe"
    if not exe.is_file():
        return None
    cli = None
    try:
        m = re.search(r'%~dp0\.\.\\([^"]*cli\.js)"', launcher.read_text(encoding="utf-8", errors="replace"))
        cli = root / m.group(1) if m else None
    except OSError:
        pass
    if not cli or not cli.is_file():
        found = list(root.glob("*/resources/app/out/cli.js")) + list(root.glob("resources/app/out/cli.js"))
        # commit folders are hashes: the newest by time, an older folder may stay behind after an update
        cli = max(found, key=lambda p: p.stat().st_mtime) if found else None
    return [str(exe), str(cli)] if cli else None


def code_command() -> list[str] | None:
    """How to start the command line of VS Code: on Windows Code.exe with cli.js directly, else code on PATH or where
    the installer puts it."""
    found = shutil.which("code")
    candidates = [Path(found)] if found else []
    if sys.platform == "win32":
        for var, sub in (("LOCALAPPDATA", "Programs"), ("ProgramFiles", "")):
            if os.environ.get(var):
                candidates.append(Path(os.environ[var]) / sub / "Microsoft VS Code" / "bin" / "code.cmd")
        for c in candidates:
            launcher = c if c.suffix.lower() == ".cmd" else c.with_suffix(".cmd")
            direct = _windows_direct(launcher) if launcher.is_file() else None
            if direct:
                return direct
    elif sys.platform == "darwin":
        candidates.append(Path("/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"))
    return next(([str(c)] for c in candidates if c.is_file()), None)


def _argv(code) -> list[str]:
    return [code] if isinstance(code, str) else list(code)


def _env(argv: list[str]) -> dict | None:
    if len(argv) == 2 and argv[1].lower().endswith("cli.js"):  # as code.cmd starts it
        return dict(os.environ, ELECTRON_RUN_AS_NODE="1", VSCODE_DEV="")
    return None


def extension_state(code, run=subprocess.run) -> tuple[list[str] | None, str]:
    """(missing extensions of ppp in the Default profile, problem). None with a problem when code cannot answer:
    "not found", "blocked by a group policy" or what code said."""
    if not code:
        return None, "not found"
    argv = _argv(code)
    try:
        proc = run([*argv, "--list-extensions"], capture_output=True, text=True, encoding="utf-8", errors="replace",
                   timeout=120, env=_env(argv))
    except FileNotFoundError:
        return None, "not found"
    except (OSError, subprocess.SubprocessError) as e:  # a policy may refuse the start itself (WinError 1260)
        return None, "blocked by a group policy" if any(b in str(e).lower() for b in BLOCKED) else str(e)
    said = f"{proc.stdout}\n{proc.stderr}".strip()
    if any(b in said.lower() for b in BLOCKED):
        return None, "blocked by a group policy"
    if proc.returncode:
        return None, (said.splitlines() or [f"exit code {proc.returncode}"])[-1]
    have = {line.strip().lower() for line in proc.stdout.splitlines() if line.strip()}
    return [i for i, _, _, _ in EXTENSIONS if i.lower() not in have], ""


def missing_extensions(code, run=subprocess.run) -> list[str] | None:
    return extension_state(code, run)[0]


def install_links(ids: list[str] | None = None) -> list[str]:
    """One link per extension: pasted into the address bar of the browser it opens the extension in VS Code, where one
    click on Install installs it; works where a group policy blocks the command line of VS Code."""
    return [f"vscode:extension/{i}" for i in (ids if ids is not None else [e[0] for e in EXTENSIONS])]


def install_extensions(code, ids: list[str], run=subprocess.run) -> tuple[list[str], bool]:
    argv = _argv(code)
    lines, ok = [], True
    for ext in ids:
        try:
            # output not captured: on a timeout Windows kills only cmd.exe, and the Code.exe behind it would keep a
            # captured pipe open (review 17.11.); code prints its own progress and errors
            proc = run([*argv, "--install-extension", ext], timeout=600, env=_env(argv))
            done = proc.returncode == 0
            reason = str(proc.stderr or "").strip().splitlines()[-1:] if not done else []
        except (OSError, subprocess.SubprocessError) as e:
            done, reason = False, [str(e)]
        lines.append(f"Installed the extension {ext}" if done else
                     f"Not installed: {ext} ({reason[0] if reason else 'code failed'}; your company may allow only "
                     f"approved extensions; or install it from vscode:extension/{ext})")
        ok = ok and done
    return lines, ok


class CommentedJSON(ValueError):
    """settings.json holds comments: ppp would lose them when it writes the file."""


def read_jsonc(text: str) -> dict:
    """The settings of VS Code as a dict. Trailing commas are fine (VS Code writes and accepts them); comments raise
    CommentedJSON, since writing the file back would lose them."""
    out, i, n, in_string = [], 0, len(text), False
    while i < n:
        c = text[i]
        if in_string:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_string = False
            i += 1
            continue
        if c == '"':
            in_string = True
        elif c == "/" and i + 1 < n and text[i + 1] in "/*":
            raise CommentedJSON("settings.json holds comments")
        elif c in "}]":
            j = len(out) - 1
            while j >= 0 and out[j] in " \t\r\n":
                j -= 1
            if j >= 0 and out[j] == ",":
                del out[j]
        out.append(c)
        i += 1
    cleaned = "".join(out).strip()
    data = json.loads(cleaned) if cleaned else {}
    if not isinstance(data, dict):
        raise ValueError("settings.json is no JSON object")
    return data


def read_settings(path: Path | None = None) -> dict:
    path = path or user_settings()
    return read_jsonc(path.read_text(encoding="utf-8-sig")) if path.is_file() else {}


def missing_settings(data: dict) -> list[str]:
    """Settings of ppp the user has not set; a value the user chose stays, only a Luna as model counts as missing."""
    out = [k for k in SETTINGS if k not in data]
    if "luna" in str(data.get("chat.defaultModel", "")).lower():
        out.append("chat.defaultModel")
    return out


def write_settings(path: Path | None = None) -> list[str]:
    """Add the missing settings of ppp to settings.json of the Default profile; back it up first and keep every other
    key and every value the user chose. Raises CommentedJSON or ValueError; then nothing is written."""
    path = path or user_settings()
    data = read_settings(path)
    missing = missing_settings(data)
    if not missing:
        return [f"{path}: the settings of ppp are there."]
    lines = []
    for k in missing:
        lines.append(f"Set {k}: {json.dumps(SETTINGS[k])}" + (f" (was {json.dumps(data[k])})" if k in data else ""))
        data[k] = SETTINGS[k]
    backup = write_json(path, data, indent=4)
    if backup:
        lines.insert(0, f"Backup: {backup}")
    lines.append(f"Written {path}.")
    return lines


def missing_as_json() -> str:
    """The settings of ppp as JSON to copy by hand into a settings.json that holds comments."""
    return ", ".join(f"{json.dumps(k)}: {json.dumps(v)}" for k, v in SETTINGS.items())


def write_json(path: Path, data: dict, indent: int) -> Path | None:
    """Back the file up, then replace it atomically; a symbolic link stays one (the file behind it is written).
    Returns the backup, None for a new file. On an error the temporary file goes again and OSError rises."""
    path = path.resolve() if path.is_symlink() else path
    backup = None
    if path.is_file():
        backup = path.with_name(f"{path.name}.bak-{datetime.now():%Y%m%d-%H%M%S-%f}")
        shutil.copy2(path, backup)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(json.dumps(data, indent=indent, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()
    return backup
