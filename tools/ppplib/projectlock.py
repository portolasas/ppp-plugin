"""One call at a time against the tenant per project (review 14.11.): ppp connect, export, import, tenant and members
hold exchange/tenant/.lock while they run. Two calls at once would each pass every check before either reaches the
server (two imports, or two reads of which one failed in the trial of 13.11., C9). A lock whose process has ended (a
terminal that killed ppp) or that is older than STALE is taken over."""
from __future__ import annotations

import contextlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from .project import ToolError

STALE = 3 * 3600    # seconds; longer than any call of ppp (a move waits at most --wait plus its exports)


def _alive(pid: int) -> bool:
    """Whether a process with this ID runs; never sends it a signal (on Windows os.kill would end it)."""
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes
        kernel = ctypes.windll.kernel32
        handle = kernel.OpenProcess(0x1000, False, pid)        # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            return bool(kernel.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259   # STILL_ACTIVE
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def path(root: Path) -> Path:
    return root / "exchange" / "tenant" / ".lock"


@contextlib.contextmanager
def held(root: Path, command: str):
    """Hold the lock of the project for the call; refuse while another live call holds it."""
    lock = path(root)
    lock.parent.mkdir(parents=True, exist_ok=True)
    mine = json.dumps({"pid": os.getpid(), "command": command, "time": datetime.now().isoformat(timespec="seconds")})
    for _ in range(2):
        try:
            with open(lock, "x", encoding="utf-8") as f:
                f.write(mine)
            break
        except FileExistsError:
            try:
                other = json.loads(lock.read_text(encoding="utf-8"))
                age = (datetime.now() - datetime.fromisoformat(other["time"])).total_seconds()
                live = _alive(int(other["pid"])) and age < STALE
            except (OSError, ValueError, KeyError, TypeError):
                other, live = {}, False
            if live:
                raise ToolError(f"Another call of ppp runs in this project ({other.get('command', '?')}, process {other.get('pid')}, "
                                f"since {str(other.get('time', ''))[11:16]}): calls against the tenant run one at a time. Wait for it "
                                "to end, then run this command again.") from None
            with contextlib.suppress(OSError):
                lock.unlink()       # its process has ended, or it is stale: taken over
    else:
        raise ToolError(f"The lock {lock} could not be taken; run the command again.")
    try:
        yield
    finally:
        with contextlib.suppress(OSError, ValueError):
            if json.loads(lock.read_text(encoding="utf-8")).get("pid") == os.getpid():
                lock.unlink()
