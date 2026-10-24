"""The core rules of ppp: one source (plugin/core/ppp.agent.md) for the VS Code agent and the Claude Code hook.

VS Code: `ppp setup` copies it to ~/.copilot/agents/ppp.agent.md with the tool call filled in (PLUGIN PL-17); the Agents
view applies agents from that folder. Claude Code: the SessionStart hook adds the same text (PL-4, PL-5).
Personal settings: ~/.ppp/settings.json (ARBEITSWEISE A-14).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from . import VERSION
from .project import ToolError

PLUGIN = Path(__file__).resolve().parent.parent.parent
SOURCE = PLUGIN / "core" / "ppp.agent.md"
TOOL = PLUGIN / "tools" / "ppp.py"
REPO = PLUGIN.parent
AGENT_COPY = Path.home() / ".copilot" / "agents" / "ppp.agent.md"
PPP_HOME = Path.home() / ".ppp"
SETTINGS = PPP_HOME / "settings.json"
GUIDANCE = ("beginner", "standard", "experienced")
MARK = re.compile(r"<!-- ppp agent (\S+) source ([0-9a-f]{12}) -->")


def tool_command() -> str:
    """The call of the command line with absolute paths, as the agent uses it in a terminal."""
    if sys.platform == "win32":
        return f'python -I "{TOOL}"'
    exe = "python3" if shutil.which("python3") else "python"
    return f'{exe} -I "{TOOL}"'


def source_hash() -> str:
    return hashlib.sha256(SOURCE.read_bytes()).hexdigest()[:12]


def render(command: str | None = None) -> str:
    text = SOURCE.read_text(encoding="utf-8").replace("{{PPP}}", command or tool_command())
    return text.rstrip("\n") + f"\n\n<!-- ppp agent {VERSION} source {source_hash()} -->\n"


def body(command: str | None = None) -> str:
    """The rules without the front matter, for the Claude Code hook."""
    text = SOURCE.read_text(encoding="utf-8").replace("{{PPP}}", command or tool_command())
    if text.startswith("---"):
        text = text[text.index("\n---", 3) + 4:]
    return text.strip() + "\n"


def setup() -> list[str]:
    AGENT_COPY.parent.mkdir(parents=True, exist_ok=True)
    AGENT_COPY.write_text(render(), encoding="utf-8", newline="\n")
    plugin_path = json.dumps(str(PLUGIN))
    return [
        f"Agent written: {AGENT_COPY}",
        f"Tool call in it: {tool_command()}",
        "",
        "VS Code: add to the user settings (JSON) if not there yet, then 'Developer: Reload Window' and choose the",
        "agent 'ppp' once in the agent picker (it stays chosen):",
        '  "chat.plugins.enabled": true,',
        f'  "chat.pluginLocations": {{ {plugin_path}: true }}',
        "",
        "Claude Code: once per computer",
        f"  /plugin marketplace add {REPO}",
        "  /plugin install ppp@ppp-dev",
        "",
        "Run 'ppp setup' again after every git pull that changes plugin/core/ppp.agent.md; 'ppp check' reports an outdated copy.",
    ]


def agent_note() -> str | None:
    """A warning for ppp check if the VS Code agent copy is missing or outdated."""
    if not AGENT_COPY.is_file():
        return None
    m = MARK.search(AGENT_COPY.read_text(encoding="utf-8", errors="replace"))
    if not m or m.group(2) != source_hash():
        return f"S the VS Code agent {AGENT_COPY} is outdated; run ppp setup"
    return None


def clone_note(timeout: float = 10) -> str | None:
    """A warning for ppp check if the ppp clone this tool runs from is behind its upstream: on 2026-10-23/24 the company
    computer still ran 0.0.1 a day after 0.0.2. Silent offline, outside a clone and with PPP_NO_FETCH=1 (tests)."""
    if os.environ.get("PPP_NO_FETCH") or not (REPO / ".git").exists() or not shutil.which("git"):
        return None
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    try:
        subprocess.run(["git", "-C", str(REPO), "fetch", "--quiet"], env=env, capture_output=True, timeout=timeout)
        behind = subprocess.run(["git", "-C", str(REPO), "rev-list", "--count", "HEAD..@{u}"], env=env,
                                capture_output=True, text=True, timeout=timeout).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return None
    if not behind.isdigit() or behind == "0":
        return None
    return (f"S ppp {VERSION} in {REPO} is {behind} commits behind its upstream; tell the user to update ppp "
            "(AKTUALISIEREN.md: git pull, ppp setup, Reload Window)")


def read_settings() -> dict | None:
    try:
        return json.loads(SETTINGS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write_settings(language: str | None, guidance: str | None) -> dict:
    current = read_settings() or {}
    if language:
        current["language"] = language
    if guidance:
        if guidance not in GUIDANCE:
            raise ToolError(f"guidance must be one of {', '.join(GUIDANCE)}")
        current["guidance"] = guidance
    missing = [k for k in ("language", "guidance") if k not in current]
    if missing:
        raise ToolError("missing: " + ", ".join(f"--{k}" for k in missing))
    PPP_HOME.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return current
