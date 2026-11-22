"""Alfred · source adapter — career-ops zero-token scanner.

Runs career-ops's `scan.mjs` (150+ ATS/board providers: Greenhouse, Lever, Ashby,
Workday, SmartRecruiters, Keka, Darwinbox, Zoho Recruit, TurboHire, ...) through
scripts/careerops_bridge.py and returns canonical Alfred jobs.

It costs no AI tokens: it is plain HTTP against public ATS APIs. Which companies
and which titles it reads is set in `portals.yml` (title_filter / location_filter /
tracked_companies), not by `roles`/`locations` here: those are passed for
interface compatibility and used only as a final title check.

No Node or no career-ops install -> [] with the reason in LAST_ERROR, so the
run continues with the other sources.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import careerops_bridge  # noqa: E402

SOURCE = "careerops_scan"
BROWSER = False
LAST_ERROR: Optional[str] = None
LAST_RECEIPT: Optional[Dict[str, Any]] = None


def _since_days() -> Optional[int]:
    try:
        import yaml
        import paths
        with open(paths.search_config(), "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh) or {}
        v = cfg.get("max_age_days")
        return int(v) if v else None
    except Exception:  # noqa: BLE001 — config problems surface in preflight, not here
        return None


def fetch(roles: Optional[List[str]] = None, locations: Optional[List[str]] = None,
          timeout: int = 15) -> List[Dict[str, Any]]:
    global LAST_ERROR, LAST_RECEIPT
    reason = careerops_bridge.unavailable_reason()
    if reason:
        LAST_ERROR = reason
        return []
    res = careerops_bridge.scan(since_days=_since_days())
    LAST_ERROR = res.get("error")
    LAST_RECEIPT = res.get("receipt")
    if LAST_ERROR:
        raise RuntimeError(LAST_ERROR)
    return res.get("jobs") or []
