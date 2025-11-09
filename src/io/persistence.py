"""Persistence helpers (placeholder)."""

from __future__ import annotations

from pathlib import Path
import json
from typing import Any


def write_json(path: str | Path, obj: Any):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as f:
        json.dump(obj, f, indent=2)
