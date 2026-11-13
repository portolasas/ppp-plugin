"""The core rules of ppp: one source (plugin/com.github.copilot/agents/ppp.agent.md) for VS Code and Claude Code.

VS Code loads it as the plugin agent ppp (PLUGIN PL-4, PL-17); Claude Code gets the same text from the SessionStart
hook (PL-5). The tool call comes from the hook and is kept in ~/.ppp/tool-call.txt for sessions without hooks (PL-16).
Before 0.2.0 `ppp setup` copied the agent to ~/.copilot/agents/; such a copy would hide the plugin agent.
Personal settings: ~/.ppp/settings.json (ARBEITSWEISE A-14). The environment variable PPP_HOME, when set and not empty,
names another folder for ~/.ppp (for trials and tests; the ordinary user does not set it).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from . import VERSION
from .project import (ToolError, check_option_prefix, check_publisher_display, check_publisher_name,
                      check_publisher_prefix)

PLUGIN = Path(__file__).resolve().parent.parent.parent
SOURCE = PLUGIN / "com.github.copilot" / "agents" / "ppp.agent.md"
TOOL = PLUGIN / "tools" / "ppp.py"
REPO = PLUGIN.parent
AGENT_COPY = Path.home() / ".copilot" / "agents" / "ppp.agent.md"


def home_folder() -> Path:
    """The personal folder of ppp: the environment variable PPP_HOME when it is set and not empty (made absolute, ~
    resolved), else ~/.ppp. Settings, tool call, usage and card guard notes and the sessions mark are derived from
    PPP_HOME below."""
    given = os.environ.get("PPP_HOME", "").strip()
    return Path(os.path.abspath(os.path.expanduser(given))) if given else Path.home() / ".ppp"


PPP_HOME = home_folder()
SETTINGS = PPP_HOME / "settings.json"
TOOL_CALL = PPP_HOME / "tool-call.txt"
MARKETPLACE = "portolasas/ppp-plugin"
GUIDANCE = ("beginner", "standard", "experienced")
MARK = re.compile(r"<!-- ppp agent (\S+) source ([0-9a-f]{12}) -->")  # the mark of the copies before 0.2.0


def tool_command() -> str:
    """The call of the command line with absolute paths, as the agent uses it in a terminal."""
    if sys.platform == "win32":
        return f'python -I "{TOOL}"'
    exe = "python3" if shutil.which("python3") else "python"
    return f'{exe} -I "{TOOL}"'


def write_tool_call() -> None:
    """Keeps the tool call of this copy of the plugin in ~/.ppp/tool-call.txt for sessions without hooks (PL-16)."""
    call = tool_command() + "\n"
    try:
        if not TOOL_CALL.is_file() or TOOL_CALL.read_text(encoding="utf-8") != call:
            PPP_HOME.mkdir(parents=True, exist_ok=True)
            TOOL_CALL.write_text(call, encoding="utf-8", newline="\n")
    except OSError:
        pass


def body() -> str:
    """The rules without the front matter, for the Claude Code hook."""
    text = SOURCE.read_text(encoding="utf-8")
    if text.startswith("---"):
        text = text[text.index("\n---", 3) + 4:]
    return text.strip() + "\n"


def _development_clone() -> bool:
    return (REPO / ".claude-plugin" / "marketplace.json").is_file()


def setup() -> list[str]:
    """Removes an agent copy of ppp before 0.2.0 and shows the entries for the installation (PL-17)."""
    lines = []
    if AGENT_COPY.is_file():
        if MARK.search(AGENT_COPY.read_text(encoding="utf-8", errors="replace")):
            AGENT_COPY.unlink()
            lines += [f"Removed the old agent copy {AGENT_COPY}: the agent ppp now comes with the plugin.", ""]
        else:
            lines += [f"Not removed: {AGENT_COPY} has no mark of ppp but hides the agent ppp of the plugin; "
                      "rename or remove it yourself.", ""]
    write_tool_call()
    lines += [f"Tool call: {tool_command()} (kept in {TOOL_CALL})", "",
              f"VS Code: Settings > chat.plugins.marketplaces > 'Add Item' > {MARKETPLACE} (if not there yet;",
              "or Customizations > Browse > Configure Marketplaces > Add Marketplace), install ppp from the marketplace,",
              "then 'Developer: Reload Window' and choose the agent 'ppp' once in the agent picker (it stays chosen)."]
    if _development_clone():
        lines.append(f'  development clone instead of the marketplace: "chat.pluginLocations": {{ {json.dumps(str(PLUGIN))}: true }}')
    lines += ["", "Claude Code: once per computer", f"  /plugin marketplace add {MARKETPLACE}", "  /plugin install ppp@ppp"]
    if _development_clone():
        lines.append(f"  development clone instead: /plugin marketplace add {REPO}, then /plugin install ppp@ppp-dev")
    return lines


def agent_note() -> str | None:
    """A warning for ppp check: a file ~/.copilot/agents/ppp.agent.md hides the agent ppp of the plugin (PL-17)."""
    if not AGENT_COPY.is_file():
        return None
    if MARK.search(AGENT_COPY.read_text(encoding="utf-8", errors="replace")):
        return f"S the old agent copy {AGENT_COPY} hides the agent ppp of the plugin; run ppp setup, it removes the copy"
    return f"S {AGENT_COPY} hides the agent ppp of the plugin; rename or remove it"


def _git(*args: str, timeout: float) -> subprocess.CompletedProcess:
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never")  # never wait for a login prompt
    return subprocess.run(["git", "-C", str(REPO), *args], env=env, capture_output=True, text=True, timeout=timeout)


def _version_in(repo: Path) -> str:
    init = repo / "plugin" / "tools" / "ppplib" / "__init__.py"
    m = re.search(r'^VERSION\s*=\s*"([^"]+)"', init.read_text(encoding="utf-8"), re.M) if init.is_file() else None
    return m.group(1) if m else "?"


def update_clone(timeout: float = 10) -> str | None:
    """ppp check brings the ppp clone this tool runs from up to date at the start of a session: git pull --ff-only when
    it is behind its upstream, has no local changes and no own commits; otherwise a warning. Reason: on 2026-10-23/24
    the company computer still ran 0.0.1 a day after 0.0.2. Silent offline, outside a clone (a copy of the plugin from a
    marketplace) and with PPP_NO_FETCH=1 (tests)."""
    if os.environ.get("PPP_NO_FETCH") or not (REPO / ".git").exists() or not shutil.which("git"):
        return None
    try:
        _git("fetch", "--quiet", timeout=timeout)
        behind = _git("rev-list", "--count", "HEAD..@{u}", timeout=timeout).stdout.strip()
        if not behind.isdigit() or behind == "0":
            return None
        ahead = _git("rev-list", "--count", "@{u}..HEAD", timeout=timeout).stdout.strip()
        dirty = _git("status", "--porcelain", "--untracked-files=no", timeout=timeout).stdout.strip()
        if ahead != "0" or dirty:
            return (f"S ppp {VERSION} in {REPO} is {behind} commits behind its upstream and has local "
                    + ("commits" if ahead != "0" else "changes") + "; tell the user to update ppp by hand (AKTUALISIEREN.md)")
        pull = _git("pull", "--ff-only", "--quiet", timeout=4 * timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if pull.returncode:
        return f"S ppp {VERSION} in {REPO} could not be updated ({pull.stderr.strip()[:200]}); tell the user (AKTUALISIEREN.md)"
    return (f"S ppp updated from {VERSION} to {_version_in(REPO)} (git pull); it applies from the next session. "
            "Tell the user: in VS Code 'Developer: Reload Window' brings the new agent, skills and hooks")


def read_settings() -> dict | None:
    try:
        return json.loads(SETTINGS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def publisher_of(settings: object) -> dict | None:
    """The publisher in the settings (uniqueName, displayName, prefix, optionValuePrefix) when all four values are valid;
    None when there is none, it is no object or a value is wrong. Never raises: the hook relies on that."""
    given = settings.get("publisher") if isinstance(settings, dict) else None
    if not isinstance(given, dict):
        return None
    try:
        return {"uniqueName": check_publisher_name(given.get("uniqueName")),
                "displayName": check_publisher_display(given.get("displayName")),
                "prefix": check_publisher_prefix(given.get("prefix")),
                "optionValuePrefix": check_option_prefix(given.get("optionValuePrefix"))}
    except ToolError:
        return None


def merge_publisher(current: object, given: dict) -> dict:
    """The publisher after a change: the saved one with the given values (None means not given) put over it. Without a
    saved publisher, name, prefix and option value prefix must come together; the display name is then the name."""
    saved = publisher_of(current)
    merged = dict(saved or {})
    merged.update({k: v for k, v in given.items() if v is not None})
    if not saved:
        missing = [flag for key, flag in (("uniqueName", "--publisher-name"), ("prefix", "--publisher-prefix"),
                                          ("optionValuePrefix", "--publisher-option-prefix")) if key not in merged]
        if missing:
            raise ToolError("No publisher saved yet: give --publisher-name, --publisher-prefix and --publisher-option-prefix "
                            "together (missing: " + ", ".join(missing) + "), or --publisher-from <unpacked solution>.")
        merged.setdefault("displayName", merged["uniqueName"])
    return {"uniqueName": check_publisher_name(merged["uniqueName"]),
            "displayName": check_publisher_display(merged["displayName"]),
            "prefix": check_publisher_prefix(merged["prefix"]),
            "optionValuePrefix": check_option_prefix(merged["optionValuePrefix"])}


def write_settings(language: str | None, guidance: str | None, sessions: str | None = None,
                   backup: str | None = None, publisher: dict | None = None) -> dict:
    current = read_settings() or {}
    if language:
        current["language"] = language
    if guidance:
        if guidance not in GUIDANCE:
            raise ToolError(f"guidance must be one of {', '.join(GUIDANCE)}")
        current["guidance"] = guidance
    if sessions:
        folder = Path(sessions).expanduser().resolve()
        if not folder.is_dir():
            raise ToolError(f"Folder not found: {folder}")
        current["sessionsRepo"] = str(folder)
    if backup:
        folder = Path(backup).expanduser().resolve()
        if not folder.is_dir():
            raise ToolError(f"Folder not found: {folder}")
        current["backupFolder"] = str(folder)  # local projects, ABLAGE AB-5
    if publisher:  # uniqueName, displayName, prefix, optionValuePrefix; None for a value not given
        current["publisher"] = merge_publisher(current, publisher)
    missing = [k for k in ("language", "guidance") if k not in current]
    if missing:
        raise ToolError("missing: " + ", ".join(f"--{k}" for k in missing))
    PPP_HOME.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return current
