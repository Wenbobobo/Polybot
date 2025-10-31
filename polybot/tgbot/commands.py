from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class ParsedCommand:
    cmd: str
    args: List[str]


def parse_command(text: str) -> ParsedCommand:
    t = (text or "").strip()
    if t.startswith("/"):
        t = t[1:]
    parts = [p for p in t.split() if p]
    if not parts:
        return ParsedCommand(cmd="", args=[])
    return ParsedCommand(cmd=parts[0].lower(), args=parts[1:])

