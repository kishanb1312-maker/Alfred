#!/usr/bin/env python3
"""Alfred · approval_poll — turn Telegram taps into the next card, deterministically.

Why this exists
---------------
Both approval gates used to be driven by an agent following prose mid-run. That works
while the run is still going, and fails the moment it is not — which is the normal case:
the run sends the review card and ends, the user taps Approve an hour later, and the tap
is reconciled by a much later run. Reconciliation updated Notion and enqueued the job,
and there it stopped: the second gate (the email preview with Send / Edit / Cancel) was
described as "sent immediately after Approve", and nobody was there to send it. Notion
said Approved, the phone stayed quiet, and the email was never asked about again.

So the tap → next-card step is code, not instructions. Every tap gets its consequence in
the same process that read it, and a `--sweep` catches any approved job still missing its
preview card.

What it does NOT do: it never sends email and never touches Notion. It records decisions,
sends cards, and prints a JSON summary the calling agent uses to update Notion. The actual
recruiter email stays where it was — behind the application agent, gated on a `"cleared"`
decision, `dry_run`, `/pause`, and the daily caps.

Usage
-----
    approval_poll.py                       # poll once, dispatch, then sweep
    approval_poll.py --timeout 60          # long-poll up to 60s for an immediate tap
    approval_poll.py --sweep               # only send the missing preview cards
    approval_poll.py --preview <job_id>    # (re-)send one job's preview card
    approval_poll.py --stage <job.json>    # stage a job's email draft from its output dir
    approval_poll.py --status              # print local state as JSON; no network

One bad job never takes the pass down: a card that fails is caught, recorded under
`errors`, and the remaining jobs are still handled. But the exit code is **1 whenever any
error was recorded**, and the errors also go to stderr — a sweep that failed on every job
because the bot token is missing must not read as a clean run.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import email_send  # noqa: E402  builds the EmailMessage the preview is rendered from
import telegram_bot as tb  # noqa: E402


# ---------------------------------------------------------------------------
# Building the preview from a staged draft
# ---------------------------------------------------------------------------

def build_message_from_draft(draft: Dict[str, Any]):
    """The exact EmailMessage the draft describes — attachments and all."""
    return email_send.build_message(
        to=draft.get("to", ""),
        subject=draft.get("subject", ""),
        body=draft.get("body", ""),
        attachments=draft.get("attachments") or [],
    )


def send_preview(job_id: str, job: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Send the email-preview card for `job_id`. Returns a per-job result record.

    Refuses on a job with no staged draft (nothing tailored to preview) and on one
    whose Send/Cancel answer is already in — a decided email must not be re-asked.
    """
    draft = tb.load_draft(job_id)
    if draft is None:
        return {"job_id": job_id, "preview": "skipped", "reason": "no staged email draft"}
    decided = tb.email_decision(job_id)
    if decided is not None:
        return {"job_id": job_id, "preview": "skipped", "reason": f"already {decided}"}

    msg = build_message_from_draft(draft)
    message_id = tb.send_email_preview_card(job or tb.draft_job(job_id), msg)
    return {"job_id": job_id, "preview": "sent", "message_id": message_id,
            "to": draft.get("to")}


def _ack(callback_query_id: Optional[str], text: str) -> None:
    """Answer a tap so the client's spinner stops. Never fatal: an expired callback id
    (Telegram drops them after ~48h) must not stop the card that actually matters."""
    if not callback_query_id:
        return
    try:
        tb.answer_callback(callback_query_id, text)
    except Exception:  # noqa: BLE001 — the ack is a courtesy, the card is the point
        pass


# ---------------------------------------------------------------------------
# Dispatch — one event in, its consequence out
# ---------------------------------------------------------------------------

def dispatch(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Act on parsed events. Returns a summary for the caller (and for Notion)."""
    out: Dict[str, Any] = {
        "approved": [], "skipped": [], "email_cleared": [], "email_cancelled": [],
        "edits_applied": [], "previews": [], "commands": [], "errors": [],
    }

    for ev in events:
        etype = ev.get("type")

        if etype == "command":
            out["commands"].append(ev.get("command"))
            continue

        if etype == "text":
            job_id = tb.get_awaiting_edit()
            if not job_id:
                continue  # a stray message, not an edit — nothing is awaiting one
            draft = tb.apply_edit(job_id, ev.get("text", ""))
            if draft is None:
                out["errors"].append({"job_id": job_id, "error": "empty or unknown edit"})
                continue
            tb.clear_awaiting_edit()
            out["edits_applied"].append(job_id)
            try:
                out["previews"].append(send_preview(job_id))
            except Exception as exc:  # noqa: BLE001
                out["errors"].append({"job_id": job_id, "error": f"{type(exc).__name__}: {exc}"})
            continue

        if etype != "decision":
            continue

        job_id = ev.get("job_id", "")
        decision = ev.get("decision")
        cq = ev.get("callback_query_id")

        if decision == "approve":
            tb.record_job_decision(job_id, "approved")
            tb.enqueue_approved(job_id)
            out["approved"].append(job_id)
            has_draft = tb.load_draft(job_id) is not None
            _ack(cq, "Approved ✅ — sending the email preview…" if has_draft
                 else "Approved ✅ — portal only (no recruiter email found)")
            try:
                out["previews"].append(send_preview(job_id))
            except Exception as exc:  # noqa: BLE001 one bad job never ends the poll
                out["errors"].append({"job_id": job_id, "error": f"{type(exc).__name__}: {exc}"})

        elif decision == "skip":
            tb.record_job_decision(job_id, "skipped")
            out["skipped"].append(job_id)
            _ack(cq, "Skipped ⏭️")

        elif decision == "send":
            first = tb.record_email_decision(job_id, "cleared")
            out["email_cleared"].append(job_id)
            _ack(cq, "Send confirmed 📧 — Alfred will send it on the next apply run"
                 if first else "Already answered")

        elif decision == "cancel":
            first = tb.record_email_decision(job_id, "cancelled")
            out["email_cancelled"].append(job_id)
            _ack(cq, "Email cancelled 🚫 — the portal application still goes ahead"
                 if first else "Already answered")

        elif decision == "edit":
            _ack(cq, "Send me the new text ✏️")
            try:
                tb.send_edit_prompt(tb.draft_job(job_id))
            except Exception as exc:  # noqa: BLE001
                out["errors"].append({"job_id": job_id, "error": f"{type(exc).__name__}: {exc}"})

    return out


def sweep(summary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Send the preview card for every approved job that never got one.

    This is the self-heal for jobs already stuck: approved in a past run, Notion moved
    on, no second card. It is idempotent — a job drops out of `pending_email_previews()`
    the moment its card is sent.
    """
    summary = summary if summary is not None else {"previews": [], "errors": []}
    summary.setdefault("previews", [])
    summary.setdefault("errors", [])
    for job_id in tb.pending_email_previews():
        try:
            summary["previews"].append(send_preview(job_id))
        except Exception as exc:  # noqa: BLE001
            summary["errors"].append({"job_id": job_id, "error": f"{type(exc).__name__}: {exc}"})
    return summary


def status() -> Dict[str, Any]:
    """Local state only — no network. What is approved, drafted, decided, pending."""
    drafts = tb._read_json(tb.EMAIL_DRAFTS, {})
    return {
        "paused": tb.is_paused(),
        "offset": tb.load_offset(),
        "approved_queue": tb.approved_queue(),
        "staged_drafts": sorted(drafts) if isinstance(drafts, dict) else [],
        "awaiting_edit": tb.get_awaiting_edit(),
        "pending_email_previews": tb.pending_email_previews(),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _stage_from_file(path: str) -> Dict[str, Any]:
    """Stage the email draft for a job described by a canonical job-object JSON file."""
    with open(path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    jobs = payload if isinstance(payload, list) else [payload]
    staged: List[Dict[str, Any]] = []
    for job in jobs:
        draft = tb.stage_email_draft(job)
        staged.append({
            "job_id": job.get("job_id"),
            "staged": draft is not None,
            "to": (draft or {}).get("to"),
            "attachments": (draft or {}).get("attachments"),
            "reason": None if draft else "no recruiter address or no email_message.txt",
        })
    return {"staged": staged}


def _emit(summary: Dict[str, Any]) -> int:
    """Print the summary and exit non-zero if anything failed.

    The JSON alone is not enough of a signal: a sweep that failed on every job — no bot
    token, Telegram unreachable — otherwise exits 0 and the run reports success while the
    user's phone stays empty, which is the exact failure this script exists to end.
    """
    print(json.dumps(summary, indent=2))
    errors = summary.get("errors") or []
    for err in errors:
        print(f"approval_poll: {err.get('job_id')}: {err.get('error')}", file=sys.stderr)
    return 1 if errors else 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="approval_poll",
        description="Poll Telegram and act on every tap: approve → email preview card, "
                    "edit → re-preview, send/cancel → recorded. Sends no email.")
    parser.add_argument("--timeout", type=int, default=0,
                        help="long-poll window in seconds (0 = take what is queued)")
    parser.add_argument("--sweep", action="store_true",
                        help="only send preview cards for approved jobs missing one")
    parser.add_argument("--no-sweep", action="store_true",
                        help="poll and dispatch, but skip the missing-preview sweep")
    parser.add_argument("--preview", metavar="JOB_ID",
                        help="(re-)send the email preview card for one job")
    parser.add_argument("--stage", metavar="JOB_JSON",
                        help="stage the email draft(s) from a canonical job-object JSON")
    parser.add_argument("--status", action="store_true",
                        help="print local state as JSON and exit (no network)")
    args = parser.parse_args(argv)

    if args.status:
        print(json.dumps(status(), indent=2))
        return 0

    if args.stage:
        print(json.dumps(_stage_from_file(args.stage), indent=2))
        return 0

    if args.preview:
        print(json.dumps(send_preview(args.preview), indent=2))
        return 0

    if args.sweep:
        return _emit(sweep())

    events, new_offset = tb.poll_responses(timeout=args.timeout)
    summary = dispatch(events)
    summary["offset"] = new_offset
    summary["events"] = len(events)
    if not args.no_sweep:
        sweep(summary)
    summary["paused"] = tb.is_paused()
    return _emit(summary)


if __name__ == "__main__":
    raise SystemExit(main())
