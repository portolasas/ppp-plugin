"""Hooks of ppp (PLUGIN PL-12): SessionStart, Stop, PreCompact. Only in ppp projects (project.json).
Each tool has its own hook file that names it (PL-5, PL-18): hooks/hooks.json passes `claude` for Claude Code,
com.github.copilot/hooks/hooks.json passes `copilot` for VS Code, which runs them in the Agents view (agent host);
in the session target Local the policy ChatHooks switches them off (PL-16).

SessionStart  core rules (only Claude Code; in VS Code the plugin agent ppp brings them, PL-4), settings, tool call and
              STATE.md as context (at most 10,000 characters, a limit of Claude Code): for VS Code as additionalContext
              at the top level, for Claude Code in hookSpecificOutput. Keeps the tool call in ~/.ppp/tool-call.txt.
Stop          card guard: a question in plain text sends the agent back once (A-10); usage note per session (PL-13).
PreCompact    tells the user to save the state and start a new chat; the model gets nothing.
A hook never blocks because of its own error: when in doubt it lets the turn pass.
Call: python -I ppp_hook.py <event> <copilot|claude>, hook input as JSON on stdin (keys in snake_case or camelCase).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

LIMIT = 10_000
TOOLS = {"copilot": "copilot", "claude": "claude-code"}  # argument of the hook file -> tool name in logs and cardguard


def project_root(cwd: str):
    start = Path(cwd or ".").resolve()
    for folder in (start, *start.parents):
        if (folder / "project.json").is_file():
            return folder
    return None


def append(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def session_start(data: dict, root: Path, tool: str) -> dict:
    from ppplib import agent
    agent.write_tool_call()
    settings = agent.read_settings()
    try:
        config = json.loads((root / "project.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        config = {}
    head = [] if tool == "copilot" else [agent.body()]
    head += ["## This session",
             f"- Project: {config.get('name', root.name)} in {root}",
             f"- Tool call: {agent.tool_command()} <command>"]
    if settings:
        head.append(f"- Settings: language {settings.get('language')}, guidance {settings.get('guidance')}")
    else:
        head.append("- ~/.ppp/settings.json is missing: before anything else ask language and guidance on one card.")
    text = "\n".join(head) + "\n"
    state = root / "STATE.md"
    if state.is_file():
        content = state.read_text(encoding="utf-8", errors="replace")
        room = LIMIT - len(text) - 200
        if len(content) > room:
            content = content[:max(room, 0)] + "\n[…] STATE.md is longer; read the rest from the file."
        text += "\n## STATE.md\n" + content
    if tool == "copilot":  # the agent host drops hookSpecificOutput (Nachtest 4, 25.10.)
        return {"additionalContext": text[:LIMIT]}
    return {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text[:LIMIT]}}


def stop(data: dict, root: Path, tool: str) -> dict | None:
    from ppplib import agent, cardguard
    home = agent.PPP_HOME
    session = data.get("session_id") or data.get("sessionId") or ""
    transcript = data.get("transcript_path") or data.get("transcriptPath") or ""
    tool = TOOLS[tool]
    usage = home / "usage.jsonl"
    seen = usage.read_text(encoding="utf-8", errors="replace") if usage.is_file() else ""
    if session and f'"{session}"' not in seen:
        append(usage, {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "tool": tool,
                       "project": root.name, "session": session, "log": transcript})
    text = data.get("last_assistant_message")
    asked = False
    if transcript and Path(transcript).is_file():
        from_log, asked = cardguard.last_turn(Path(transcript), tool, wait=3.0)
        text = text if isinstance(text, str) and text else from_log
    question = cardguard.plain_question(text if isinstance(text, str) else "")
    if not question:
        return None
    returned = not data.get("stop_hook_active")
    append(home / "cardguard.jsonl", {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                     "tool": tool, "project": root.name, "session": session,
                                     "returned": returned, "question_tool_used": asked})
    if not returned:
        return None  # only once per turn
    return {"decision": "block",
            "reason": cardguard.REMINDER.format(q=question[:160], tool=cardguard.QUESTION_TOOL.get(tool, "AskUserQuestion"))}


def pre_compact(data: dict, root: Path, tool: str) -> dict:
    from ppplib import agent
    german = ((agent.read_settings() or {}).get("language") or "de").lower().startswith("de")
    message = ("ppp: Der Kontext wird gleich verdichtet. Besser: Stand sichern (Haltepunkt) und einen neuen Chat starten."
               if german else "ppp: the context is about to be compacted. Better: save the state (stopping point) and start a new chat.")
    return {"systemMessage": message}


def main() -> int:
    event = sys.argv[1] if len(sys.argv) > 1 else ""
    tool = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] in TOOLS else "claude"
    try:
        raw = sys.stdin.read() if not sys.stdin.isatty() else ""
        data = json.loads(raw) if raw.strip() else {}
        root = project_root(data.get("cwd") or "")
        if root is None:
            return 0
        handler = {"SessionStart": session_start, "Stop": stop, "PreCompact": pre_compact}.get(event)
        out = handler(data, root, tool) if handler else None
        if out:
            sys.stdout.reconfigure(encoding="utf-8")
            print(json.dumps(out, ensure_ascii=False))
    except Exception as ex:  # noqa: BLE001 – a hook must never block the work
        print(f"ppp hook {event}: {type(ex).__name__}: {ex}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
