from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class WriteResult:
    path: Path
    bytes_written: int


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_text_file(path: Path, content: str, encoding: str = "utf-8") -> WriteResult:
    ensure_parent(path)
    data = content.encode(encoding)
    path.write_bytes(data)
    return WriteResult(path=path, bytes_written=len(data))

