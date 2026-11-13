"""Hooks of ppp (PLUGIN PL-12): SessionStart, Stop, PreCompact, PreToolUse. Only in ppp projects (project.json).
Each tool has its own hook file that names it (PL-5, PL-18): hooks/hooks.json passes `claude` for Claude Code,
com.github.copilot/hooks/hooks.json passes `copilot` for VS Code, which runs them in the Agents view (agent host);
in the session target Local the policy ChatHooks switches them off (PL-16).

SessionStart  core rules (only Claude Code; in VS Code the plugin agent ppp brings them, PL-4), settings, tool call and
              STATE.md as context (at most 10,000 characters, a limit of Claude Code): for VS Code as additionalContext
              at the top level, for Claude Code in hookSpecificOutput. Keeps the tool call in ~/.ppp/tool-call.txt.
Stop          card guard: a question in plain text sends the agent back once (A-10); usage note per session (PL-13).
PreCompact    tells the user to save the state and start a new chat; the model gets nothing.
PreToolUse    in a connected project (project.json names an environment) refuses a command line that calls pac itself;
              the tenant is reached through ppp only (VERBUNDEN VB-17). It reads the command line and nothing else: it
              catches the habit, not every detour. For a direct call it is the only technical guard; the allowlist in
              ppplib/tenant.py protects the calls ppp makes itself, a direct pac call of the agent goes past it.
A hook never blocks because of its own error: when in doubt it lets the turn pass.
Call: python -I ppp_hook.py <event> <copilot|claude>, hook input as JSON on stdin (keys in snake_case or camelCase).
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

LIMIT = 10_000
TOOLS = {"copilot": "copilot", "claude": "claude-code"}  # argument of the hook file -> tool name in logs and cardguard
# Sections of STATE.md that go first when it does not fit; the manual changes stand near the end of the template and were
# the first to be cut (review 07.11.: in Claude Code about 3,000 characters remain beside the core rules).
FIRST = ("Active package", "Next step", "Manual changes in the tenant")
# pac where a shell takes its command from: at the start, after a separator, after a shell keyword (do, then, else, !),
# after a wrapper such as cmd /c, bash -lc, xargs, iex or dotnet tool run; by name or by path, quoted or not. A word pac
# further back (an argument, a text in quotes) is not a call.
_WRAPPER = (r"(?:(?:sudo|call|exec|start|command|env|time|nohup|winpty|xargs|do|then|else|elif|if|while|until"
            r"|iex|invoke-expression|dotnet(?:\s+tool\s+run)?|start-process(?:\s+-filepath)?|cmd(?:\.exe)?\s+/[ck]"
            r"|(?:bash|sh|zsh|pwsh|powershell)(?:\.exe)?(?:\s+-\w+)*\s+-(?:\w*c|command))\s+[\"']?|!\s*|\w+=\S*\s+)*")
PAC_CALL = re.compile(r"(?:^|[\n;|&({`]|\$\()\s*" + _WRAPPER
                      + r"""(?:"[^"\n]*[\\/]|'[^'\n]*[\\/]|[^\s"'|;&()]*[\\/]|["'])?pac(?:\.exe|\.cmd|\.bat)?["']?(?=\s|$|[;|&)])""",
                      re.I)
TERMINAL = re.compile(r"bash|shell|terminal|command|exec", re.I)
DENIED = ("ppp: this project is connected to the tenant (environment {alias}), and this command calls pac itself. Never call pac "
          "there: the tool carries the checks a direct call skips. The tenant: ppp connect, ppp export, ppp import, ppp tenant. "
          "An export or a package on disk: ppp unpack, ppp pack. What these do not offer goes to the user on a card. If the "
          "command only quotes pac in a text, write that text with the file tool.")


def state_within(content: str, room: int) -> str:
    """STATE.md within room characters: unchanged when it fits. Else its head, the sections of FIRST in that order, then
    the other sections in file order. Within each group whole sections go first, then the first one that did not fit, cut."""
    if len(content) <= room:
        return content
    head, *sections = content.split("\n## ")
    sections = ["## " + s.rstrip("\n") + "\n" for s in sections]
    title = lambda s: s[3:].split("\n", 1)[0].strip()
    rank = lambda s: next((i for i, f in enumerate(FIRST) if title(s).startswith(f)), None)
    text, left = head.rstrip("\n")[:room] + "\n", []
    for group in (sorted((s for s in sections if rank(s) is not None), key=rank),
                  [s for s in sections if rank(s) is None]):
        rest = []
        for s in group:
            if len(text) + len(s) <= room:
                text += s
            else:
                rest.append(s)
        for n, s in enumerate(rest):
            if n == 0 and room - len(text) > 200:
                text += s[:room - len(text)] + "…\n"
                left.append(title(s) + " (cut)")
            else:
                left.append(title(s))
    if len(head) > room:
        left.insert(0, "the start (cut)")
    names = ", ".join(left[:6]) + (f" and {len(left) - 6} more" if len(left) > 6 else "")
    return text + f"\n[…] STATE.md is longer; read the rest from the file. Missing or cut here: {names}."


def is_ppp_config(path: Path) -> bool:
    """A project.json of ppp: a JSON object with structureVersion (int) and prefix (str). Both are required by
    structure.py for every ppp project and together they are in no Nx or .NET project.json."""
    try:
        config = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return False
    return (isinstance(config, dict) and isinstance(config.get("structureVersion"), int)
            and not isinstance(config.get("structureVersion"), bool) and isinstance(config.get("prefix"), str))


def project_root(cwd: str):
    start = Path(cwd or ".").resolve()
    for folder in (start, *start.parents):
        if (folder / "project.json").is_file():
            return folder if is_ppp_config(folder / "project.json") else None  # a foreign project.json: not ours
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
             f"- Project: {config.get('name', root.name)} in {root}"
             + (" (storage local: commit, never pull or push; ppp backup on request)" if config.get("storage") == "local" else ""),
             f"- Tool call: {agent.tool_command()} <command>"]
    if isinstance(settings, dict) and settings:
        publisher = agent.publisher_of(settings)  # a broken entry counts as not set
        head.append(f"- Settings: language {settings.get('language')}, guidance {settings.get('guidance')}"
                    + (f", publisher {publisher['uniqueName']} (prefix {publisher['prefix']})" if publisher else ""))
        if not publisher:
            head.append("- Publisher: not set. Before a solution is created, ask for it on one card (ppp-intake) and save it "
                        "with ppp settings.")
    else:
        head.append("- ~/.ppp/settings.json is missing: before anything else ask language, guidance and publisher on one card "
                    "(the publisher may be skipped if the user has none yet).")
    text = "\n".join(head) + "\n"
    state = root / "STATE.md"
    if state.is_file():
        content = state.read_text(encoding="utf-8", errors="replace")
        text += "\n## STATE.md\n" + state_within(content, max(LIMIT - len(text) - 400, 0))
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


def command_lines(data: dict) -> list[str]:
    """What a tool call would run: the field command; for a terminal tool that names it otherwise, every text it passes."""
    given = data.get("tool_input", data.get("toolInput"))
    if isinstance(given, str):
        try:
            given = json.loads(given)
        except ValueError:
            given = {"command": given}
    if not isinstance(given, dict):
        return []
    if isinstance(given.get("command"), str):
        return [given["command"]]
    name = str(data.get("tool_name") or data.get("toolName") or "")
    return [v for v in given.values() if isinstance(v, str)] if TERMINAL.search(name) else []


def pre_tool_use(data: dict, root: Path, tool: str) -> dict | None:
    lines = command_lines(data)
    if not any(PAC_CALL.search(line) for line in lines):
        return None
    try:
        alias = json.loads((root / "project.json").read_text(encoding="utf-8-sig")).get("environment")
    except (OSError, ValueError, AttributeError):
        return None
    if not isinstance(alias, str) or not alias:
        return None  # offline: the tenant is out of reach anyway, and the rules name ppp pack and ppp unpack
    answer = {"permissionDecision": "deny", "permissionDecisionReason": DENIED.format(alias=alias)}
    if tool == "copilot":  # both forms refuse in the agent host (pac test round 1, H3 and H4); this one names no event
        return answer
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", **answer}}


def main() -> int:
    event = sys.argv[1] if len(sys.argv) > 1 else ""
    tool = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] in TOOLS else "claude"
    try:
        raw = sys.stdin.read() if not sys.stdin.isatty() else ""
        data = json.loads(raw) if raw.strip() else {}
        root = project_root(data.get("cwd") or "")
        if root is None:
            return 0
        handler = {"SessionStart": session_start, "Stop": stop, "PreCompact": pre_compact, "PreToolUse": pre_tool_use}.get(event)
        out = handler(data, root, tool) if handler else None
        if out:
            sys.stdout.reconfigure(encoding="utf-8")
            print(json.dumps(out, ensure_ascii=False))
    except Exception as ex:  # noqa: BLE001 – a hook must never block the work
        print(f"ppp hook {event}: {type(ex).__name__}: {ex}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
