#!/usr/bin/env python3
"""Send Alfred review cards through the 1.4.0 two-gate Telegram sender.

Gate 1 (this script): the review card — Approve / Skip.
Gate 2 (approval-gate at poll time): the email preview — Send / Edit / Cancel.
Nothing here sends an application; it only puts cards in front of the human.

api.telegram.org drops connections mid-upload often enough that a plain run
loses cards, so every call is retried and state is written after each card:
a crash costs one card, and re-running resumes instead of double-sending.
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402  single source of truth for paths (§4)
import telegram_bot as tb  # noqa: E402

# Deriving these from __file__ breaks the moment the script runs from the plugin
# root — CLAUDE_PLUGIN_ROOT holds the code, never the user's data.
TAILOR = os.path.join(paths.data_dir(), "tailor_output.json")
HISTORY = paths.applied_history_path()
SENT = os.path.join(paths.data_dir(), "approval_sent.json")

RETRIES = 4


def _retry(fn, *a, **kw):
    """Telegram transport errors are transient; retry with backoff."""
    for attempt in range(1, RETRIES + 1):
        try:
            return fn(*a, **kw)
        except Exception as exc:                     # noqa: BLE001 - transport-agnostic
            if attempt == RETRIES:
                raise
            print(f"    transport error ({type(exc).__name__}), retry {attempt}/{RETRIES - 1}",
                  flush=True)
            time.sleep(2 * attempt)
    return None


def _files(job):
    f = job.get("files") or job.get("artifacts") or {}
    return f.get("resume_pdf"), (f.get("cover_letter") or f.get("cover_letter_pdf"))


def _save(cards, skipped):
    import email_gate  # lazy: only needed to record the run's real dry_run
    json.dump({
        "run": {"stage": "approval-gate", "sender": "1.4.0 two-gate",
                "sent_at": tb._now_iso(),
                "dry_run": email_gate.load_limits()["dry_run"]},
        "cards": cards,
        "skipped": skipped,
        "awaiting_decision": [c["job_id"] for c in cards],
        "stage6_run": False,
    }, open(SENT, "w"), indent=1, ensure_ascii=False)


def main() -> int:
    jobs = json.load(open(TAILOR))
    history = json.load(open(HISTORY)) if os.path.exists(HISTORY) else {}
    applied = {j for j, v in history.items() if v.get("status") == "applied"}

    # Resume support: never re-send a card this file already records.
    prev = json.load(open(SENT)) if os.path.exists(SENT) else {}
    cards = [c for c in (prev.get("cards") or []) if c.get("sender", "").startswith("1.4.0")]
    already = {c["job_id"] for c in cards}
    skipped = []

    jobs.sort(key=lambda j: -((j.get("match") or {}).get("score") or 0))

    for job in jobs:
        jid = job.get("job_id")
        if jid in already:
            print(f"  skip (already sent this run) {job.get('company')}", flush=True)
            continue
        if jid in applied:
            skipped.append((jid, "already applied"))
            continue
        resume, cover = _files(job)
        missing = [p for p in (resume, cover)
                   if not p or not os.path.exists(tb._resolved(p))]
        if missing:
            skipped.append((jid, f"missing attachment: {missing}"))
            continue

        mid = _retry(tb.send_review_card, job,
                     tb._resolved(resume), tb._resolved(cover))
        cards.append({
            "job_id": jid,
            "company": job.get("company"),
            "score": (job.get("match") or {}).get("score"),
            "channel": job.get("channel"),
            "contact_email": job.get("contact_email"),
            "message_id": mid,
            "sender": "1.4.0 two-gate (telegram_bot.send_review_card)",
        })
        _save(cards, skipped)                        # persist after every card
        print(f"  sent [{mid}] {job.get('company')}", flush=True)
        time.sleep(1.0)                              # stay inside the rate limit

    _save(cards, skipped)
    print(f"\nsent {len(cards)} cards, skipped {len(skipped)}", flush=True)
    for jid, why in skipped:
        print(f"  skipped {jid}: {why}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
