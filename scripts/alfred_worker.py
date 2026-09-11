#!/usr/bin/env python3
"""Alfred · worker — the always-on half, so your laptop can be shut.

What this solves
----------------
Everything downstream of a Telegram tap used to need the user's machine awake: the tap
sat in Telegram's queue until some run happened to poll for it. Approve at midnight with
the laptop closed and the email preview arrived whenever you next opened it — if the tap
survived Telegram's 24h retention at all.

This is a small process that just stays awake and does that polling. Long-poll, act on
every tap, sleep, repeat. Run it on anything that stays on — a Pi, a VPS, a free container
tier — and the whole email conversation works with your laptop off:

    Approve  -> the email preview card arrives within seconds
    Edit     -> reply, get the rewritten preview back
    Send     -> the email actually goes out, and you get the ✅ / ❌ confirmation
    Cancel   -> recorded; the portal application is untouched
    /pause   -> everything stops until /resume

What it deliberately cannot do
------------------------------
**The portal channel.** LinkedIn Easy Apply and friends need the signed-in browser on YOUR
machine; no server has your session, and driving one from a datacenter IP is how accounts
get banned. Portal applications still happen on your laptop during a normal Alfred run.
This worker is the email half.

**Finding, researching and tailoring jobs.** Those are agent stages that need Claude. The
worker only serves decisions on work already prepared and staged.

It also never touches Notion — it has no MCP connector. Notion catches up on your next
Alfred run, from the decision records this worker wrote.

Requirements on the host: Python + `requests` + `PyYAML`, a copy of the Alfred home
(`~/.alfred`, or `$ALFRED_HOME`) holding `config/search.yaml`, the staged drafts and the
tailored PDFs, and the four secrets in its `.env`. See `deploy/README.md`.

Usage:
    alfred_worker.py                  # run forever (this is the daemon)
    alfred_worker.py --once           # one cycle, then exit (for cron, or a smoke test)
    alfred_worker.py --no-send        # cards and edits only; never send an email
    alfred_worker.py --poll-timeout 50
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import approval_poll as ap  # noqa: E402
import email_gate  # noqa: E402
import telegram_bot as tb  # noqa: E402

# Telegram caps a long poll well under this; the HTTP read timeout sits above it so the
# socket never dies mid-poll and re-fetches updates it already had.
_DEFAULT_POLL_TIMEOUT = 50

# Network dies, Telegram 5xxs, the host's DNS blips. Back off rather than hammering, and
# cap the wait so a recovered link is picked up within a minute.
_BACKOFF_START = 2.0
_BACKOFF_MAX = 60.0

_running = True


def _stop(signum, _frame) -> None:
    """SIGTERM/SIGINT: finish the cycle in flight, then exit cleanly.

    Container platforms send SIGTERM on every deploy and restart; a worker that dies
    mid-send instead of mid-poll is how an email goes out twice.
    """
    global _running
    _running = False
    log(f"signal {signum} received — stopping after this cycle")


def log(message: str) -> None:
    """One line, stdout, flushed — journald/docker logs are the only view you get."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"{ts}  {message}", flush=True)


def _describe(summary: Dict[str, Any]) -> str:
    """A cycle in one line. Quiet cycles say nothing worth a log entry."""
    bits: List[str] = []
    for key, label in (("approved", "approved"), ("skipped", "skipped"),
                       ("edits_applied", "edited"), ("email_cleared", "cleared"),
                       ("email_cancelled", "cancelled")):
        if summary.get(key):
            bits.append(f"{label}={','.join(summary[key])}")
    previews = [p for p in summary.get("previews", []) if p.get("preview") == "sent"]
    if previews:
        bits.append(f"previews={len(previews)}")
    if summary.get("notices"):
        bits.append(f"portal-only-notices={len(summary['notices'])}")
    for send in summary.get("sends", []):
        bits.append(f"send:{send.get('job_id')}="
                    f"{send.get('status') or send.get('reason')}")
    for err in summary.get("errors", []):
        bits.append(f"ERROR:{err.get('job_id')}={err.get('error')}")
    return "  ".join(bits)


def cycle(send_emails: bool = True, poll_timeout: int = _DEFAULT_POLL_TIMEOUT) -> Dict[str, Any]:
    """One poll → dispatch → sweep pass. Raises only on a failed poll (the caller backs off).

    The two sweeps are what make the worker safe to restart: whatever it missed while it
    was down is picked up from the on-disk records rather than from the update stream.
    """
    events, offset = tb.poll_responses(timeout=poll_timeout, commit=False)
    summary = ap.dispatch(events, send_emails=send_emails)
    # Only now is it safe to tell Telegram we are done with these updates. Commit it
    # first and a crash between the poll and the card — the exact window a restarting
    # container lives in — destroys the tap rather than replaying it.
    tb.save_offset(offset)
    summary["offset"] = offset
    summary["events"] = len(events)

    ap.sweep(summary)                     # approved jobs still missing a preview card
    summary["notion_updates"] = ap.notion_plan()   # for the next Alfred run to apply
    if send_emails:
        summary.setdefault("sends", []).extend(email_gate.send_cleared())
    return summary


def serve(send_emails: bool = True, poll_timeout: int = _DEFAULT_POLL_TIMEOUT,
          once: bool = False) -> int:
    limits = email_gate.load_limits()
    log(f"alfred worker starting — home={tb._data_home()} "
        f"send_emails={send_emails} dry_run={limits['dry_run']} "
        f"email_cap={limits['emails_per_day']}")
    if not limits["config_read"]:
        log("WARNING: config/search.yaml unreadable — treating dry_run as ON, "
            "so no real email will be sent until it is fixed")
    if tb.is_paused():
        log("NOTE: /pause is set — taps are still recorded, nothing will be sent")

    backoff = _BACKOFF_START
    while _running:
        try:
            summary = cycle(send_emails=send_emails, poll_timeout=poll_timeout)
            backoff = _BACKOFF_START
            line = _describe(summary)
            if line:
                log(line)
        except KeyboardInterrupt:
            break
        except Exception as exc:  # noqa: BLE001 — a worker that exits on a blip is useless
            log(f"cycle failed ({type(exc).__name__}: {exc}) — retrying in {backoff:.0f}s")
            time.sleep(backoff)
            backoff = min(backoff * 2, _BACKOFF_MAX)
        if once:
            break
    log("alfred worker stopped")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="alfred_worker",
        description="Always-on Telegram worker: approve → email preview, edit → re-preview, "
                    "send → the email actually goes out. Email channel only; no portal, no Notion.")
    parser.add_argument("--once", action="store_true", help="one cycle, then exit")
    parser.add_argument("--no-send", action="store_true",
                        help="handle cards and edits but never send an email")
    parser.add_argument("--poll-timeout", type=int, default=_DEFAULT_POLL_TIMEOUT,
                        help=f"Telegram long-poll seconds (default {_DEFAULT_POLL_TIMEOUT})")
    parser.add_argument("--status", action="store_true",
                        help="print local state as JSON and exit (no network)")
    args = parser.parse_args(argv)

    if args.status:
        print(json.dumps(ap.status(), indent=2))
        return 0

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _stop)

    return serve(send_emails=not args.no_send, poll_timeout=args.poll_timeout,
                 once=args.once)


if __name__ == "__main__":
    raise SystemExit(main())
