"""Usage per session from the session logs of Copilot and Claude Code (successor of PPP-KOSTEN, PLUGIN PL-13).

Recorded for evaluation from outside: no budget, no target value, no hint to the agent (ANFORDERUNGEN W18).
Copilot: ~/.copilot/session-state/<id>/events.jsonl, AIU from the cumulative counter totalNanoAiu.
Claude Code: ~/.claude/projects/<folder>/<id>.jsonl, tokens per model (subscription, no AIU).
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .cardguard import QUESTION_TOOLS, plain_question

PERIOD_STARTS = (1, 9, 17, 25)  # Copilot budget quarters of the month (AUFTRAG)


@dataclass
class Session:
    tool: str
    sid: str
    path: Path
    project: str = "?"
    start: datetime | None = None
    end: datetime | None = None
    aiu: float = 0.0
    tokens: Counter = field(default_factory=Counter)  # input, cache_read, cache_write, output
    models: Counter = field(default_factory=Counter)  # requests per model
    subagents: int = 0
    questions: int = 0  # final answers that ask the user in plain text (card guard, A-10)


def period_start(today: date, starts=PERIOD_STARTS) -> date:
    days = [d for d in starts if d <= today.day]
    if days:
        return today.replace(day=days[-1])
    prev = (today.replace(day=1) - timedelta(days=1))
    return prev.replace(day=min(starts[-1], prev.day))


def _time(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _lines(path: Path):
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                yield json.loads(line)
            except ValueError:
                continue


def _project(cwd: str | None) -> str:
    if not cwd:
        return "?"
    parts = [p for p in cwd.replace("\\", "/").rstrip("/").split("/") if p]
    while parts and parts[-1].startswith(".git"):
        parts.pop()
    return parts[-1] if parts else "?"


def copilot(home: Path, since: datetime) -> list[Session]:
    out = []
    for events in sorted((home / ".copilot" / "session-state").glob("*/events.jsonl")):
        if datetime.fromtimestamp(events.stat().st_mtime, timezone.utc) < since:
            continue
        s = Session("copilot", events.parent.name, events)
        before = last = 0.0
        shutdown = None
        for e in _lines(events):
            t, d = _time(e.get("timestamp")), e.get("data") or {}
            typ = e.get("type")
            if typ == "session.start":
                s.start = _time(d.get("startTime")) or t
                s.project = _project((d.get("context") or {}).get("cwd"))
            elif typ in ("session.usage_checkpoint", "session.shutdown") and d.get("totalNanoAiu") is not None:
                value = d["totalNanoAiu"] / 1e9
                if t and t < since:
                    before = value
                else:
                    last = max(last, value)
                if typ == "session.shutdown":
                    shutdown = d
            elif typ == "assistant.message" and d.get("model") and (not t or t >= since):
                s.models[d["model"]] += 1
                if not d.get("toolRequests") and not d.get("parentToolCallId") and plain_question(d.get("content")):
                    s.questions += 1
            elif typ == "subagent.started" and (not t or t >= since):
                s.subagents += 1
            if t:
                s.end = t
        s.aiu = max(0.0, last - before)
        if shutdown and (s.start is None or s.start >= since):
            details = shutdown.get("tokenDetails") or {}
            for key in ("input", "cache_read", "cache_write", "output"):
                s.tokens[key] += (details.get(key) or {}).get("tokenCount", 0)
        if s.project == "?":
            ws = events.parent / "workspace.yaml"
            if ws.is_file():
                for line in ws.read_text(encoding="utf-8", errors="replace").splitlines():
                    if line.startswith("cwd:"):
                        s.project = _project(line[4:].strip())
                        break
        out.append(s)
    return out


def claude(home: Path, since: datetime) -> list[Session]:
    """A resumed session copies earlier requests into its new file; each request counts once (oldest file first)."""
    out, seen = [], set()
    for log in sorted((home / ".claude" / "projects").glob("*/*.jsonl"), key=lambda f: f.stat().st_mtime):
        subagents = sorted((log.parent / log.stem / "subagents").glob("*.jsonl"))
        newest = max(f.stat().st_mtime for f in [log, *subagents])
        if datetime.fromtimestamp(newest, timezone.utc) < since:
            continue
        s = Session("claude-code", log.stem, log, subagents=len(subagents))
        for path in [log, *subagents]:
            for e in _lines(path):
                t = _time(e.get("timestamp"))
                if e.get("cwd") and s.project == "?":
                    s.project = _project(e["cwd"])
                if t and path == log:
                    s.start = s.start or t
                    s.end = t
                msg = e.get("message") if isinstance(e.get("message"), dict) else None
                if e.get("type") != "assistant" or not msg or not msg.get("usage") or (t and t < since):
                    continue
                key = e.get("requestId") or msg.get("id")
                if key in seen:
                    continue
                seen.add(key)
                u = msg["usage"]
                s.tokens["input"] += u.get("input_tokens", 0)
                s.tokens["cache_read"] += u.get("cache_read_input_tokens", 0)
                s.tokens["cache_write"] += u.get("cache_creation_input_tokens", 0)
                s.tokens["output"] += u.get("output_tokens", 0)
                s.models[msg.get("model", "?")] += 1
                blocks = [b for b in msg.get("content") or [] if isinstance(b, dict)]
                if msg.get("stop_reason") == "end_turn" and path == log and not any(
                        b.get("type") == "tool_use" and b.get("name") in QUESTION_TOOLS for b in blocks):
                    if plain_question(" ".join(b.get("text", "") for b in blocks if b.get("type") == "text")):
                        s.questions += 1
        if s.tokens or s.models:
            out.append(s)
    return out


def collect(home: Path, since: datetime, project: str = "") -> list[Session]:
    sessions = [s for s in copilot(home, since) + claude(home, since) if s.aiu or s.tokens or s.models]
    if project:
        sessions = [s for s in sessions if project.lower() in s.project.lower()]
    return sorted(sessions, key=lambda s: s.end or datetime.min.replace(tzinfo=timezone.utc))


def _mio(n: int) -> str:
    return f"{n / 1e6:.2f}M" if n >= 10_000 else str(n)


def table(sessions: list[Session], since: datetime) -> list[str]:
    out = [f"Usage since {since.date().isoformat()} ({len(sessions)} sessions; tokens: input/cache read/cache write/output)"]
    for s in sessions:
        when = (s.end or s.start).astimezone().strftime("%Y-%m-%d %H:%M") if (s.end or s.start) else "?"
        models = ", ".join(f"{m} {n}" for m, n in s.models.most_common())
        tok = "/".join(_mio(s.tokens[k]) for k in ("input", "cache_read", "cache_write", "output"))
        aiu = f"{s.aiu:8.1f} AIU" if s.tool == "copilot" else "         -  "
        sub = (f", {s.subagents} subagents" if s.subagents else "") + (f", {s.questions} plain-text questions" if s.questions else "")
        out.append(f"  {when}  {s.tool:<11} {s.project:<24} {aiu}  {tok}  [{models}{sub}]")
    by_project: dict = defaultdict(lambda: [0.0, 0])
    for s in sessions:
        by_project[(s.tool, s.project)][0] += s.aiu
        by_project[(s.tool, s.project)][1] += sum(s.tokens.values())
    out.append("Per project:")
    for (tool, proj), (aiu, tok) in sorted(by_project.items(), key=lambda x: (-x[1][0], -x[1][1])):
        out.append(f"  {tool:<11} {proj:<24} " + (f"{aiu:8.1f} AIU  " if tool == "copilot" else "") + f"{_mio(tok)} tokens")
    return out


def as_json(sessions: list[Session]) -> list[dict]:
    return [{"tool": s.tool, "session": s.sid, "project": s.project, "log": str(s.path),
             "start": s.start.isoformat() if s.start else None, "end": s.end.isoformat() if s.end else None,
             "aiu": round(s.aiu, 3), "tokens": dict(s.tokens), "models": dict(s.models), "subagents": s.subagents,
             "plainTextQuestions": s.questions}
            for s in sessions]
