"""Append immutable API observations to a local JSON Lines file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def append_records(path: str | Path, records: list[dict[str, Any]]) -> None:
    """Append records as UTF-8 JSONL, creating the parent directory if needed."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("a", encoding="utf-8", newline="\n") as output:
        for record in records:
            output.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            output.write("\n")
