"""Card guard (ARBEITSWEISE A-10): a question to the user belongs on a card (question tool), not in plain text.

Used by the Stop hook (sends the agent back once; Claude Code, and the agent host of VS Code, PLUGIN PL-16) and by
ppp usage, which counts plain-text questions in the session logs afterwards (VS Code where hooks do not run).
A heuristic: the last paragraph of the final answer of a turn asks something.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

QUESTION_TOOLS = {"AskUserQuestion", "ask_user", "askQuestions", "vscode_askQuestions"}
CODE = re.compile(r"```.*?```|`[^`\n]*`", re.S)
QUOTED = re.compile(r"[\"“„][^\"“”\n]*[\"”]")


def plain_question(text: str | None) -> str | None:
    """The question sentence in the last paragraph of the text, if there is one."""
    if not text:
        return None
    clean = QUOTED.sub("", CODE.sub("", text)).strip()
    paragraphs = [p for p in re.split(r"\n\s*\n", clean) if p.strip()]
    if not paragraphs:
        return None
    last = paragraphs[-1]
    for line in reversed([ln.strip() for ln in last.splitlines() if ln.strip()]):
        if line.startswith(("|", ">")):
            continue
        sentences = re.split(r"(?<=[.!?])\s+", line)
        for s in reversed(sentences):
            if s.rstrip("*_ )").endswith("?") and len(s) > 8:
                return s.strip()
    return None


REMINDER = ("Your last answer asks the user in plain text: {q!r}. Ask it with the question tool ({tool}) "
            "instead, the recommended answer first; text the user needs stays in the chat above it. If it was no "
            "question to the user, end your answer without it.")
QUESTION_TOOL = {"copilot": "ask_user", "claude-code": "AskUserQuestion"}


def log_tool(transcript: str) -> str:
    """Which tool wrote the session log: copilot (~/.copilot/session-state/<id>/events.jsonl, also when VS Code runs
    the hooks of the plugin), claude-code (<config>/projects/<folder>/<id>.jsonl), otherwise unknown."""
    path = Path(transcript.replace("\\", "/")) if transcript else None
    if path and path.name == "events.jsonl" and path.parent.parent.name == "session-state":
        return "copilot"
    if path and path.suffix == ".jsonl" and path.parent.parent.name == "projects":
        return "claude-code"
    return "unknown"


def last_turn(transcript: Path, tool: str, wait: float = 0.0) -> tuple[str, bool]:
    """(text of the final answer of the last turn, question tool used in that turn) from the log of that tool."""
    return copilot_last_turn(transcript, wait) if tool == "copilot" else claude_last_turn(transcript)


TURN_EVENTS = {"user.message", "assistant.turn_start", "assistant.message", "assistant.turn_end", "abort",
               "tool.execution_start", "tool.execution_complete"}


def copilot_turn_complete(lines: list[str]) -> bool:
    """True when the log holds the end of the turn: the newest model round ended with an answer without tool
    requests, or the user aborted it."""
    ended = False
    for line in reversed(lines[-400:]):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        typ = e.get("type")
        if typ not in TURN_EVENTS:
            continue
        if typ == "abort":
            return True
        if not ended:
            if typ != "assistant.turn_end":
                return False
            ended = True
        elif typ == "assistant.message":
            return not (e.get("data") or {}).get("toolRequests")
        elif typ != "assistant.turn_end":
            return False  # tools ran in this round, or the round has no message yet
    return False


def copilot_last_turn(events: Path, wait: float = 0.0) -> tuple[str, bool]:
    """The same from a Copilot log. VS Code may start the Stop hook (agentStop) a few milliseconds before the final
    answer is in events.jsonl (Mac, 20.10.), so the hook waits up to `wait` seconds for the end of the turn.
    agentStop also fires when a subagent ends (its events carry parentToolCallId); then the newest answer is the
    subagent's and nothing is judged."""
    deadline = time.monotonic() + wait
    while True:
        lines = events.read_text(encoding="utf-8", errors="replace").splitlines()
        if wait <= 0 or copilot_turn_complete(lines) or time.monotonic() >= deadline:
            break
        time.sleep(0.1)
    text = None
    asked = False
    newest = True
    for line in reversed(lines[-3000:]):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") == "user.message":
            break  # the user's prompt starts the turn
        if e.get("type") != "assistant.message":
            continue
        d = e.get("data") or {}
        if d.get("parentToolCallId"):
            if newest:
                return "", False
            continue
        newest = False
        names = {r.get("name") or r.get("toolName") for r in d.get("toolRequests") or [] if isinstance(r, dict)}
        if names & QUESTION_TOOLS:
            asked = True
        if text is None and d.get("content"):
            text = d["content"]
    return text or "", asked


def claude_last_turn(transcript: Path) -> tuple[str, bool]:
    """(text of the final assistant message of the last turn, question tool used in that turn)."""
    lines = transcript.read_text(encoding="utf-8", errors="replace").splitlines()
    text_parts: list[str] = []
    asked = False
    for line in reversed(lines[-400:]):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        msg = e.get("message") if isinstance(e.get("message"), dict) else {}
        if e.get("type") == "user":
            content = msg.get("content")
            if isinstance(content, str) or (isinstance(content, list) and any(
                    isinstance(b, dict) and b.get("type") == "text" for b in content)):
                break  # a real user prompt starts the turn
            continue
        if e.get("type") != "assistant":
            continue
        for b in reversed(msg.get("content") or []):
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use" and b.get("name") in QUESTION_TOOLS:
                asked = True
            elif b.get("type") == "text" and not text_parts:
                text_parts.append(b.get("text", ""))
    return (text_parts[0] if text_parts else ""), asked
