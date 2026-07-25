"""WarmApply · daily_caps — per-day action counters (pure stdlib, no network).

The application-agent uses this to never exceed `caps.applies_per_day` /
`caps.emails_per_day`. Counts are kept per calendar day and per `kind` in
data/daily_counts.json (gitignored):

    { "2026-07-25": { "apply": 3, "email": 1 }, ... }

Public API:
    - remaining(kind, cap) -> int   # cap minus today's count, floored at 0
    - record(kind) -> int           # increment today's count, return new count
    - count(kind) -> int            # today's count for kind
    - reset_today() -> None         # clear today's counts (test helper)
"""

from __future__ import annotations

import json
import os
from datetime import date
from typing import Dict

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COUNTS_PATH = os.path.join(_REPO_ROOT, "data", "daily_counts.json")


def _today() -> str:
    return date.today().isoformat()


def _load(path: str) -> Dict[str, Dict[str, int]]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save(data: Dict[str, Dict[str, int]], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
    os.replace(tmp, path)


def count(kind: str, *, path: str = COUNTS_PATH) -> int:
    """Today's recorded count for `kind` (0 if none)."""
    return int(_load(path).get(_today(), {}).get(kind, 0))


def remaining(kind: str, cap: int, *, path: str = COUNTS_PATH) -> int:
    """How many more `kind` actions are allowed today given `cap` (>= 0)."""
    return max(0, int(cap) - count(kind, path=path))


def record(kind: str, *, path: str = COUNTS_PATH) -> int:
    """Increment today's count for `kind`; return the new count."""
    data = _load(path)
    today = _today()
    day = data.setdefault(today, {})
    day[kind] = int(day.get(kind, 0)) + 1
    _save(data, path)
    return day[kind]


def reset_today(*, path: str = COUNTS_PATH) -> None:
    """Clear today's counts (used by tests/dry-runs)."""
    data = _load(path)
    data.pop(_today(), None)
    _save(data, path)
