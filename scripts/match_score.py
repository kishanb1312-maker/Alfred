"""Alfred · match_score — deterministic job/candidate match baseline.

Returns a 0–100 SIGNAL from skill/keyword overlap between a job description and
the user's profile. This is intentionally simple, pure, and offline: the
company-research agent treats it as one input and sets the final match.score
using its own reading of the JD vs the user's real experience.

Pure stdlib — no network, no third-party deps.

Public API (per the company-research definition):
    - baseline(job_text, profile) -> int      # 0–100 skill/keyword overlap

Also exposed for callers that want to explain the number:
    - baseline_detail(job_text, profile) -> dict
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


def _profile_skills(profile: Dict[str, Any]) -> Dict[str, float]:
    """Extract {skill: weight} from a profile dict.

    Sources:
      - `years_experience` map (weight scales gently with years),
      - an optional `skills` list (weight 1.0 each).
    A skill with 0 recorded years still counts as present (weight 1.0) — the
    user listed it — but years add emphasis.
    """
    skills: Dict[str, float] = {}

    years = profile.get("years_experience") or {}
    if isinstance(years, dict):
        for name, yrs in years.items():
            key = str(name).strip().lower()
            if not key:
                continue
            try:
                y = float(yrs)
            except (TypeError, ValueError):
                y = 0.0
            # Presence = 1.0, plus up to +1.0 for experience (capped at 5 yrs).
            skills[key] = 1.0 + min(max(y, 0.0), 5.0) / 5.0

    extra = profile.get("skills")
    if isinstance(extra, list):
        for name in extra:
            key = str(name).strip().lower()
            if key:
                skills.setdefault(key, 1.0)

    return skills


def _mentions(job_text: str, skill: str) -> bool:
    """True if `skill` appears in `job_text` (word-boundary, case-insensitive).

    Handles multi-word skills ("site reliability") and keeps a substring
    fallback for tokens that word boundaries don't play well with (e.g. "c++").
    """
    jt = job_text.lower()
    sk = skill.lower().strip()
    if not sk:
        return False
    pattern = r"(?<![a-z0-9])" + re.escape(sk) + r"(?![a-z0-9])"
    if re.search(pattern, jt):
        return True
    # Fallback for symbol-heavy skills where boundaries fail.
    if not sk.isalnum() and sk in jt:
        return True
    return False


def baseline_detail(job_text: str, profile: Dict[str, Any]) -> Dict[str, Any]:
    """Compute the baseline and return the supporting detail.

    Score = weighted fraction of the user's profile skills that the JD mentions,
    rounded to 0–100. No skills in profile → 0 (cannot assess overlap).
    """
    skills = _profile_skills(profile or {})
    if not skills:
        return {"score": 0, "matched": [], "missing": [], "total_skills": 0}

    matched: List[str] = []
    missing: List[str] = []
    matched_weight = 0.0
    total_weight = 0.0
    for skill, weight in skills.items():
        total_weight += weight
        if _mentions(job_text or "", skill):
            matched.append(skill)
            matched_weight += weight
        else:
            missing.append(skill)

    score = int(round(100 * matched_weight / total_weight)) if total_weight else 0
    score = max(0, min(100, score))
    return {
        "score": score,
        "matched": sorted(matched),
        "missing": sorted(missing),
        "total_skills": len(skills),
    }


def baseline(job_text: str, profile: Dict[str, Any]) -> int:
    """0–100 skill/keyword-overlap signal (deterministic, offline)."""
    return baseline_detail(job_text, profile)["score"]
