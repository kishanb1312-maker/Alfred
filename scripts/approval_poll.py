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

It never touches Notion — it records decisions, sends cards, and prints a JSON summary the
calling agent turns into Notion updates. It does not send email either, unless explicitly
asked with `--send`, which hands the work to `email_gate.perform_send` and its guardrails
(`"cleared"` decision, `/pause`, bounce throttle, daily cap, `dry_run`, send-once). That flag
is what the always-on worker uses; a plain poll stays send-free.

Usage
-----
    approval_poll.py                       # poll once, dispatch, then sweep
    approval_poll.py --timeout 60          # long-poll up to 60s for an immediate tap
    approval_poll.py --send                # also send emails the user already cleared
    approval_poll.py --sweep               # only send the missing preview cards
    approval_poll.py --resend              # re-send EVERY undecided approved job's card
    approval_poll.py --preview-all         # card for every staged draft, approved or not
    approval_poll.py --notion-plan         # what Notion should say per job; no network
    approval_poll.py --preview <job_id>    # (re-)send one job's preview card
    approval_poll.py --stage <jobs.json>   # stage drafts from job objects OR Notion rows
                                           # (a row at "Approved" is recorded as approved,
                                           #  so its preview card gets sent by --sweep)
    approval_poll.py --stage rows.json --preview-all
                                           # the backlog one-liner: rehydrate every job
                                           # from a Notion export and card them all
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

def dispatch(events: List[Dict[str, Any]], send_emails: bool = False) -> Dict[str, Any]:
    """Act on parsed events. Returns a summary for the caller (and for Notion).

    `send_emails` decides what a Send tap means here: recorded only (the default, leaving
    the send to the application agent), or carried out immediately via `email_gate` — which
    is what lets a worker complete the whole flow with the user's laptop shut.
    """
    out: Dict[str, Any] = {
        "approved": [], "skipped": [], "email_cleared": [], "email_cancelled": [],
        "edits_applied": [], "previews": [], "sends": [], "commands": [], "errors": [],
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
            _ack(cq, ("Sending now 📧…" if send_emails else
                      "Send confirmed 📧 — Alfred will send it on the next apply run")
                 if first else "Already answered")
            if send_emails:
                try:
                    import email_gate
                    out["sends"].append(email_gate.perform_send(job_id))
                except Exception as exc:  # noqa: BLE001
                    out["errors"].append({"job_id": job_id,
                                          "error": f"{type(exc).__name__}: {exc}"})

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


def sweep(summary: Optional[Dict[str, Any]] = None,
          resend: bool = False, all_jobs: bool = False) -> Dict[str, Any]:
    """Send the preview card for every approved job that never got one.

    This is the self-heal for jobs already stuck: approved in a past run, Notion moved
    on, no second card. It is idempotent — a job drops out of `pending_email_previews()`
    the moment its card is sent.

    `resend=True` widens the target to every approved job still awaiting a Send/Cancel
    answer, whether or not a card was recorded as sent. A card Telegram accepted is not
    a card the user read, and "Alfred says it sent it, my phone says otherwise" has no
    other way out. Nothing is decided by re-showing a card, so the worst case is a
    duplicate message.

    `all_jobs=True` drops the approval requirement entirely: every staged draft still
    awaiting an answer gets its card. That is the bulk-backlog case — jobs already
    prepared and sitting in Notion, where the user has decided up front that they want
    to see each email and answer it one by one. It collapses the two gates into one for
    those jobs, which is a real change in posture and so is never the default; a card
    still sends no email, so the human is not skipped, only asked once instead of twice.

    Approved jobs with no draft at all get a one-line portal-only notice instead of a
    preview card — they can never satisfy the second gate, and silence there reads as a
    lost approval.
    """
    summary = summary if summary is not None else {"previews": [], "errors": []}
    summary.setdefault("previews", [])
    summary.setdefault("errors", [])
    summary.setdefault("notices", [])

    if all_jobs:
        targets = tb.undecided_drafts()
    elif resend:
        targets = tb.awaiting_email_answer()
    else:
        targets = tb.pending_email_previews()
    for job_id in targets:
        try:
            summary["previews"].append(send_preview(job_id))
        except Exception as exc:  # noqa: BLE001
            summary["errors"].append({"job_id": job_id, "error": f"{type(exc).__name__}: {exc}"})

    for job_id in tb.approved_without_draft():
        if tb.portal_notice_sent(job_id) and not resend:
            continue
        try:
            tb.send_portal_only_notice(tb.draft_job(job_id))
            summary["notices"].append({"job_id": job_id, "notice": "portal-only"})
        except Exception as exc:  # noqa: BLE001
            summary["errors"].append({"job_id": job_id, "error": f"{type(exc).__name__}: {exc}"})
    return summary


# ---------------------------------------------------------------------------
# The Notion half — planned here, applied by the agent that has the connector
# ---------------------------------------------------------------------------

_STATUS_BY_DECISION = {"approved": "Approved", "skipped": "Skipped"}


def notion_plan() -> List[Dict[str, Any]]:
    """The Status every locally-decided job should be showing in Notion, and why.

    No script in Alfred can write Notion — the connector lives in the agent host, and
    the always-on worker has none at all. So a tap recorded on disk and a Notion row
    still reading "Ready for Review" is the normal resting state between runs, not a
    bug, and the fix is for the calling agent to apply this list. Emitting it on every
    run (rather than leaving the agent to infer it from `approved`/`skipped`) is what
    makes a backlog of days-old taps recoverable in one pass instead of only the taps
    this particular poll happened to read.

    A job whose email has actually left is reported as "Applied": the send is the fact,
    and leaving it at "Approved" understates what already happened to the user.
    """
    import email_gate

    store = tb._read_json(tb.JOB_DECISIONS, {})
    if not isinstance(store, dict):
        store = {}

    plan: List[Dict[str, Any]] = []
    for job_id in sorted(set(store) | set(tb.approved_queue())):
        rec = store.get(job_id) if isinstance(store.get(job_id), dict) else {}
        decision = rec.get("decision") or ("approved" if job_id in tb.approved_queue() else None)
        status = _STATUS_BY_DECISION.get(decision or "")
        if not status:
            continue
        reason = f"tapped {decision}"
        sent = email_gate.already_sent(job_id)
        if status == "Approved" and isinstance(sent, dict) and sent.get("status") == "SENT":
            status, reason = "Applied", "email sent"
        plan.append({"job_id": job_id, "status": status,
                     "reason": reason, "decided_at": rec.get("ts")})
    return plan


def status() -> Dict[str, Any]:
    """Local state only — no network. What is approved, drafted, decided, pending."""
    drafts = tb._read_json(tb.EMAIL_DRAFTS, {})
    return {
        "paused": tb.is_paused(),
        "offset": tb.load_offset(),
        "approved": tb.approved_jobs(),
        "approved_queue": tb.approved_queue(),
        "staged_drafts": sorted(drafts) if isinstance(drafts, dict) else [],
        "awaiting_edit": tb.get_awaiting_edit(),
        "pending_email_previews": tb.pending_email_previews(),
        "awaiting_email_answer": tb.awaiting_email_answer(),
        "approved_without_draft": tb.approved_without_draft(),
        "undecided_drafts": tb.undecided_drafts(),
        "cleared_unsent": __import__("email_gate").cleared_unsent(),
        "notion_plan": notion_plan(),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _stage_from_file(path: str) -> Dict[str, Any]:
    """Stage email drafts from a job-object JSON file (one job, or a list).

    Accepts either canonical job objects or raw Notion rows — Notion is the only durable
    record of a job's recruiter address and tailored file paths, so rehydrating from it is
    how a job prepared days ago becomes emailable without re-running the pipeline.

    A job carrying `status: "Approved"` also has that approval recorded locally. Without
    this, a job approved before the local decision store existed reads as never-approved:
    Notion says Approved, Alfred has no record, and the job never qualifies for its email
    preview card. Recording it is what un-sticks exactly that job.
    """
    with open(path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if isinstance(payload, dict) and isinstance(payload.get("results"), list):
        payload = payload["results"]          # a raw Notion query response
    jobs = payload if isinstance(payload, list) else [payload]

    staged: List[Dict[str, Any]] = []
    for entry in jobs:
        if not isinstance(entry, dict):
            continue
        job = entry
        if "properties" in entry or "job_id" not in entry:
            import notion_schema
            job = notion_schema.job_from_row(entry)   # it is a Notion row, not a job
        job_id = job.get("job_id")
        if not job_id:
            staged.append({"job_id": None, "staged": False, "reason": "no Job ID"})
            continue

        approved = str(job.get("status") or "").strip().lower() == "approved"
        if approved:
            tb.record_job_decision(job_id, "approved")
            tb.enqueue_approved(job_id)

        draft = tb.stage_email_draft(job)
        staged.append({
            "job_id": job_id,
            "staged": draft is not None,
            "approved": approved,
            "to": (draft or {}).get("to"),
            "attachments": (draft or {}).get("attachments"),
            "reason": None if draft else "no recruiter address or no email_message.txt",
        })
    return {"staged": staged, "now_pending_preview": tb.pending_email_previews()}


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
    parser.add_argument("--resend", action="store_true",
                        help="re-send the preview card for EVERY approved job still "
                             "awaiting Send/Cancel, even one already marked as carded — "
                             "for when Alfred says it sent it and your phone disagrees")
    parser.add_argument("--preview-all", action="store_true",
                        help="send the email preview card for EVERY staged draft still "
                             "awaiting an answer, approved or not — the bulk backlog "
                             "case, for jobs already prepared and sitting in Notion")
    parser.add_argument("--notion-plan", action="store_true",
                        help="print the Status each decided job should be showing in "
                             "Notion, as JSON, for the agent to apply (no network)")
    parser.add_argument("--no-sweep", action="store_true",
                        help="poll and dispatch, but skip the missing-preview sweep")
    parser.add_argument("--preview", metavar="JOB_ID",
                        help="(re-)send the email preview card for one job")
    parser.add_argument("--stage", metavar="JOBS_JSON",
                        help="stage email draft(s) from job objects or exported Notion rows; "
                             "rows at Approved are recorded as approved")
    parser.add_argument("--send", action="store_true",
                        help="also send emails the user cleared (guardrails in email_gate)")
    parser.add_argument("--status", action="store_true",
                        help="print local state as JSON and exit (no network)")
    args = parser.parse_args(argv)

    if args.status:
        print(json.dumps(status(), indent=2))
        return 0

    if args.notion_plan:
        print(json.dumps({"notion_updates": notion_plan()}, indent=2))
        return 0

    if args.stage:
        staged = _stage_from_file(args.stage)
        if not (args.preview_all or args.sweep or args.resend):
            print(json.dumps(staged, indent=2))
            return 0
        # Staging and carding in one invocation: the two-command version leaves a
        # window where the drafts exist and the user's phone still shows nothing,
        # and that window is exactly where this flow keeps getting stuck.
        summary = sweep(resend=args.resend, all_jobs=args.preview_all)
        summary["staged"] = staged["staged"]
        summary["notion_updates"] = notion_plan()
        return _emit(summary)

    if args.preview:
        print(json.dumps(send_preview(args.preview), indent=2))
        return 0

    if args.sweep or args.resend or args.preview_all:
        summary = sweep(resend=args.resend, all_jobs=args.preview_all)
        summary["notion_updates"] = notion_plan()
        return _emit(summary)

    # The offset is committed AFTER dispatch, not by the poll: an offset advanced
    # first turns any failure below into a tap Telegram has already dropped, which
    # is the approval the user never gets back.
    events, new_offset = tb.poll_responses(timeout=args.timeout, commit=False)
    summary = dispatch(events, send_emails=args.send)
    summary["offset"] = new_offset
    summary["events"] = len(events)
    tb.save_offset(new_offset)
    if not args.no_sweep:
        sweep(summary, resend=args.resend)
    if args.send:
        import email_gate
        summary.setdefault("sends", []).extend(email_gate.send_cleared())
    summary["paused"] = tb.is_paused()
    summary["notion_updates"] = notion_plan()
    return _emit(summary)


if __name__ == "__main__":
    raise SystemExit(main())
