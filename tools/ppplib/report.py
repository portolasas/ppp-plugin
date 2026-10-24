"""Check reports: lines with a level and a message, closed by one RESULT line."""
from __future__ import annotations

OK, INFO, WARN, ERROR = "OK", "INFO", "WARN", "ERROR"


class Report:
    def __init__(self, title: str):
        self.title = title
        self.lines: list[tuple[str, str]] = []

    def add(self, level: str, message: str) -> None:
        self.lines.append((level, message))

    def ok(self, message: str) -> None:
        self.add(OK, message)

    def info(self, message: str) -> None:
        self.add(INFO, message)

    def warn(self, message: str) -> None:
        self.add(WARN, message)

    def error(self, message: str) -> None:
        self.add(ERROR, message)

    def count(self, level: str) -> int:
        return sum(1 for lvl, _ in self.lines if lvl == level)

    @property
    def errors(self) -> int:
        return self.count(ERROR)

    @property
    def warnings(self) -> int:
        return self.count(WARN)

    def result(self) -> str:
        if self.errors:
            return f"RESULT: ERROR ({self.errors} errors, {self.warnings} warnings)"
        if self.warnings:
            return f"RESULT: OK WITH WARNINGS ({self.warnings})"
        return "RESULT: OK"

    def text(self) -> str:
        out = [self.title]
        out += [f"[{lvl}]".ljust(8) + msg for lvl, msg in self.lines]
        out.append(self.result())
        return "\n".join(out)
