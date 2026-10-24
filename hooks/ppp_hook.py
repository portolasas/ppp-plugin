"""Hooks of ppp (PLUGIN PL-12): SessionStart, Stop, PreCompact. Only in ppp projects (project.json).
Claude Code runs them; VS Code runs them in the Agents view (agent host), where the IT allows them, and the Stop hook
then reads the Copilot log. In the session target Local the policy ChatHooks switches them off (PL-16).

SessionStart  core rules (only Claude Code; in VS Code the agent ppp brings them, PL-17), settings, tool call and
              STATE.md as context (at most 10,000 characters, a limit of Claude Code).
Stop          card guard: a question in plain text sends the agent back once (A-10); usage note per session (PL-13).
PreCompact    tells the user to save the state and start a new chat; the model gets nothing.
A hook never blocks because of its own error: when in doubt it lets the turn pass.
Call: python -I ppp_hook.py <event>, hook input as JSON on stdin.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

LIMIT = 10_000


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


def from_vscode(data: dict) -> bool:
    """VS Code (agent host) sends camelCase keys such as sessionId; Claude Code sends session_id."""
    return "sessionId" in data and "session_id" not in data


def session_start(data: dict, root: Path) -> dict:
    from ppplib import agent
    settings = agent.read_settings()
    try:
        config = json.loads((root / "project.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        config = {}
    head = [] if from_vscode(data) else [agent.body()]
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
    return {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text[:LIMIT]}}


def stop(data: dict, root: Path) -> dict | None:
    from ppplib import agent, cardguard
    home = agent.PPP_HOME
    session = data.get("session_id") or data.get("sessionId") or ""
    transcript = data.get("transcript_path") or data.get("transcriptPath") or ""
    tool = cardguard.log_tool(transcript)  # VS Code runs these hooks in the agent host (PL-16)
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


def pre_compact(data: dict, root: Path) -> dict:
    from ppplib import agent
    german = ((agent.read_settings() or {}).get("language") or "de").lower().startswith("de")
    message = ("ppp: Der Kontext wird gleich verdichtet. Besser: Stand sichern (Haltepunkt) und einen neuen Chat starten."
               if german else "ppp: the context is about to be compacted. Better: save the state (stopping point) and start a new chat.")
    return {"systemMessage": message}


def main() -> int:
    event = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        raw = sys.stdin.read() if not sys.stdin.isatty() else ""
        data = json.loads(raw) if raw.strip() else {}
        root = project_root(data.get("cwd") or "")
        if root is None:
            return 0
        handler = {"SessionStart": session_start, "Stop": stop, "PreCompact": pre_compact}.get(event)
        out = handler(data, root) if handler else None
        if out:
            sys.stdout.reconfigure(encoding="utf-8")
            print(json.dumps(out, ensure_ascii=False))
    except Exception as ex:  # noqa: BLE001 – a hook must never block the work
        print(f"ppp hook {event}: {type(ex).__name__}: {ex}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
