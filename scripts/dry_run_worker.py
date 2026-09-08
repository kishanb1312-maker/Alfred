#!/usr/bin/env python3
"""Alfred · dry run — the always-on worker and the email gate it sends through.

This is the one script in Alfred that can put a real email in front of a real recruiter
with nobody watching, so its guardrails get tested hardest. SMTP is patched to explode:
any check that passes while `_smtp_send` fires is a failed check, not a passing one.

Covers: send-once, cleared-only, /pause, bounce throttle, daily cap, dry_run, the
give-up-after-N-failures loop guard, portable attachment paths across machines, and one
full laptop-off round trip (approve → preview → send → confirmation).
"""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import alfred_worker as worker  # noqa: E402
import approval_poll as ap  # noqa: E402
import bounce_check  # noqa: E402
import daily_caps  # noqa: E402
import email_gate as eg  # noqa: E402
import email_send as es  # noqa: E402
import telegram_bot as tb  # noqa: E402

ok = True
sent: list = []
smtp_calls: list = []


def check(label, got, want):
    global ok
    good = got == want
    ok = ok and good
    print(f"  [{'OK' if good else 'FAIL'}] {label}"
          + ("" if good else f"\n        got={got!r}\n        want={want!r}"))


def fake_api(method, data=None, files=None):
    sent.append({"method": method, "data": data or {}, "files": files})
    return {"ok": True, "result": {"message_id": len(sent)}}


def notices():
    return [s["data"].get("text", "") for s in sent if s["method"] == "sendMessage"]


def use_temp_home(td, *, dry_run=False, emails_per_day=10):
    """Point every module's state at a throwaway Alfred home."""
    data = os.path.join(td, "data")
    cfg = os.path.join(td, "config")
    os.makedirs(data, exist_ok=True)
    os.makedirs(cfg, exist_ok=True)
    with open(os.path.join(cfg, "search.yaml"), "w", encoding="utf-8") as fh:
        fh.write(f"dry_run: {'true' if dry_run else 'false'}\n"
                 f"caps:\n  emails_per_day: {emails_per_day}\n")

    tb._DATA = data
    for name, leaf in (("STATE_PATH", "telegram_state.json"), ("PAUSE_FLAG", "paused.flag"),
                       ("APPROVED_QUEUE", "approved_queue.json"),
                       ("EMAIL_DECISIONS", "email_decisions.json"),
                       ("EMAIL_DRAFTS", "email_drafts.json"),
                       ("AWAITING_EDIT", "email_awaiting_edit.json"),
                       ("JOB_DECISIONS", "job_decisions.json"),
                       ("EMAIL_PREVIEWS", "email_previews.json")):
        setattr(tb, name, os.path.join(data, leaf))
    eg.EMAIL_SENT = os.path.join(data, "email_sent.json")
    eg.EMAIL_FAILURES = os.path.join(data, "email_send_failures.json")
    daily_caps.COUNTS_PATH = os.path.join(data, "daily_counts.json")
    bounce_check.EMAIL_PAUSE_FLAG = os.path.join(data, "email_paused.flag")
    eg.load_limits = lambda: {"dry_run": dry_run, "emails_per_day": emails_per_day,
                              "config_read": True}
    return data


def staged_job(td, home_relative=True):
    """A job with its email staged exactly as a real run would leave it."""
    out = os.path.join(td, "output", "Acme_Designer")
    os.makedirs(out, exist_ok=True)
    resume = os.path.join(out, "Resume_Acme.pdf")
    with open(resume, "wb") as fh:
        fh.write(b"%PDF-1.4 fake")
    with open(os.path.join(out, "email_message.txt"), "w", encoding="utf-8") as fh:
        fh.write("Subject: Senior Product Designer — Kishan\n\nHi Sara,\n\nReal body.\n\nKishan")
    job = {"job_id": "wellfound:99", "company": "Acme", "title": "Senior Product Designer",
           "email": {"address": "hr@acme.com", "source": "hunter", "confidence": 90},
           "files": {"resume": resume}}
    tb.stage_email_draft(job)
    return job


print("\n" + "=" * 74)
print("Alfred dry run — always-on worker + email gate (SMTP patched to explode)")
print("=" * 74 + "\n")

tb._api = fake_api
tb._chat_id = lambda: "123"
_smtp_guard = es._smtp_send


def exploding_smtp(msg):
    smtp_calls.append(msg["To"])
    raise AssertionError("SMTP fired when it must not have")


es._smtp_send = exploding_smtp

try:
    print("Guardrails — every one of these must refuse BEFORE SMTP")
    with tempfile.TemporaryDirectory() as td:
        use_temp_home(td)
        staged_job(td)
        smtp_calls.clear()

        check("no Send tap yet → refused",
              eg.perform_send("wellfound:99")["reason"], "not cleared by the user")

        tb.record_email_decision("other:1", "cancelled")
        check("Cancel tapped → refused",
              eg.perform_send("other:1")["reason"], "user cancelled this email")

        tb.record_email_decision("wellfound:99", "cleared")
        tb.set_pause(True)
        check("/pause set → refused",
              "pause" in eg.perform_send("wellfound:99")["reason"], True)
        tb.set_pause(False)

        bounce_check.set_email_pause(True)
        check("bounce throttle → refused",
              "throttled" in eg.perform_send("wellfound:99")["reason"], True)
        bounce_check.set_email_pause(False)

        check("no draft → refused",
              eg.perform_send("ghost:1")["reason"], "not cleared by the user")

        check("NOTHING reached SMTP through any of those", smtp_calls, [])
        check("and no confirmation was faked", notices(), [])

    print("\nDaily cap — the worker cannot outrun emails_per_day")
    with tempfile.TemporaryDirectory() as td:
        use_temp_home(td, emails_per_day=1)
        staged_job(td)
        tb.record_email_decision("wellfound:99", "cleared")
        daily_caps.record("email")  # today's one allowance already spent
        smtp_calls.clear()
        check("cap reached → refused",
              "daily email cap" in eg.perform_send("wellfound:99")["reason"], True)
        check("SMTP untouched", smtp_calls, [])

    print("\ndry_run — prepares everything, connects to nothing")
    with tempfile.TemporaryDirectory() as td:
        use_temp_home(td, dry_run=True)
        staged_job(td)
        tb.record_email_decision("wellfound:99", "cleared")
        sent.clear(); smtp_calls.clear()

        result = eg.perform_send("wellfound:99")
        check("reported as a dry run", result["status"], "DRY_RUN")
        check("not counted as sent", result["sent"], False)
        check("SMTP never opened", smtp_calls, [])
        check("user still told what would have gone",
              any("DRY RUN" in t for t in notices()), True)
        check("cap not spent on a dry run", daily_caps.count("email"), 0)
        check("recorded, so a loop does not repeat it", eg.cleared_unsent(), [])

    print("\nA real send — once, and only once")
    with tempfile.TemporaryDirectory() as td:
        use_temp_home(td)
        staged_job(td)
        tb.record_email_decision("wellfound:99", "cleared")
        sent.clear()
        es._smtp_send = lambda msg: smtp_calls.append(msg["To"])
        smtp_calls.clear()

        result = eg.perform_send("wellfound:99")
        check("sent", result["sent"], True)
        check("to the researched recipient", smtp_calls, ["hr@acme.com"])
        check("resume actually attached", result["attachments"], ["Resume_Acme.pdf"])
        check("counted against the daily cap", daily_caps.count("email"), 1)
        check("user got the ✅ confirmation", any("✅ SENT" in t for t in notices()), True)

        smtp_calls.clear()
        check("a second call refuses", eg.perform_send("wellfound:99")["reason"],
              "already SENT")
        check("SMTP not reopened", smtp_calls, [])
        check("and it stops qualifying for the sweep", eg.cleared_unsent(), [])
        es._smtp_send = exploding_smtp

    print("\nA failing send — reported, retried, then given up on (no notice storm)")
    with tempfile.TemporaryDirectory() as td:
        use_temp_home(td)
        staged_job(td)
        tb.record_email_decision("wellfound:99", "cleared")
        sent.clear()
        es._smtp_send = lambda msg: (_ for _ in ()).throw(
            RuntimeError("SMTPAuthenticationError: 535"))

        first = eg.perform_send("wellfound:99")
        check("failure surfaced, not swallowed", first["status"], "FAILED")
        check("real error text sent to the user",
              any("535" in t for t in notices()), True)
        check("NOT recorded as sent — a fixed cause can still send", eg.already_sent("wellfound:99"), None)
        check("still queued for retry", eg.cleared_unsent(), ["wellfound:99"])

        eg.perform_send("wellfound:99")
        eg.perform_send("wellfound:99")
        before = len(notices())
        check("gives up after 3 attempts",
              "gave up" in eg.perform_send("wellfound:99")["reason"], True)
        check("and goes quiet — no notice on the refusal", len(notices()), before)
        eg.clear_failures("wellfound:99")
        check("clearing the failure re-arms it",
              eg.perform_send("wellfound:99")["status"], "FAILED")
        es._smtp_send = exploding_smtp

    print("\nPortable drafts — staged on the laptop, sent from the worker host")
    with tempfile.TemporaryDirectory() as laptop, tempfile.TemporaryDirectory() as host:
        use_temp_home(laptop)
        staged_job(laptop)
        raw = tb._read_json(tb.EMAIL_DRAFTS, {})["wellfound:99"]["attachments"]
        check("stored relative to the Alfred home, not as a laptop path",
              [os.path.isabs(a) for a in raw], [False])

        # Copy the home to a different path, exactly as rsync to the worker would.
        import shutil
        shutil.copytree(os.path.join(laptop, "data"), os.path.join(host, "data"))
        shutil.copytree(os.path.join(laptop, "output"), os.path.join(host, "output"))
        use_temp_home(host)
        resolved = tb.load_draft("wellfound:99")["attachments"]
        check("resolves against the NEW home", resolved[0].startswith(host), True)
        check("and the PDF is really there", os.path.exists(resolved[0]), True)

        tb.record_email_decision("wellfound:99", "cleared")
        es._smtp_send = lambda msg: smtp_calls.append(msg["To"])
        smtp_calls.clear()
        result = eg.perform_send("wellfound:99")
        check("sends from the worker WITH the attachment",
              (result["sent"], result["attachments"]), (True, ["Resume_Acme.pdf"]))
        es._smtp_send = exploding_smtp

    print("\nLaptop-off round trip — one worker cycle, tap to confirmation")
    with tempfile.TemporaryDirectory() as td:
        use_temp_home(td)
        staged_job(td)
        sent.clear()
        smtp_calls.clear()
        es._smtp_send = lambda msg: smtp_calls.append(msg["To"])

        # Approve, then Send — both taps queued while the laptop was shut.
        updates = {"result": [
            {"update_id": 1, "callback_query": {"id": "a", "data": "approve|wellfound:99"}},
            {"update_id": 2, "callback_query": {"id": "b", "data": "send|wellfound:99"}},
        ]}
        tb._api = lambda m, data=None, files=None: (
            updates if m == "getUpdates" else fake_api(m, data, files))
        summary = worker.cycle(send_emails=True, poll_timeout=0)
        tb._api = fake_api

        check("approve recorded", summary["approved"], ["wellfound:99"])
        check("preview card sent", any("READY TO SEND" in t for t in notices()), True)
        check("email actually sent in the same cycle", smtp_calls, ["hr@acme.com"])
        check("confirmation delivered", any("✅ SENT" in t for t in notices()), True)
        check("nothing left outstanding",
              (tb.pending_email_previews(), eg.cleared_unsent()), ([], []))
        es._smtp_send = exploding_smtp

    print("\n--no-send worker still runs the cards, never the mail")
    with tempfile.TemporaryDirectory() as td:
        use_temp_home(td)
        staged_job(td)
        tb.record_email_decision("wellfound:99", "cleared")
        sent.clear(); smtp_calls.clear()
        updates = {"result": [{"update_id": 1, "callback_query": {
            "id": "a", "data": "approve|wellfound:99"}}]}
        tb._api = lambda m, data=None, files=None: (
            updates if m == "getUpdates" else fake_api(m, data, files))
        summary = worker.cycle(send_emails=False, poll_timeout=0)
        tb._api = fake_api
        check("approve handled", summary["approved"], ["wellfound:99"])
        check("no send attempted", summary.get("sends", []), [])
        check("SMTP untouched", smtp_calls, [])

    print("\nA broken config is read as dry_run ON, never as permission to send")
    with tempfile.TemporaryDirectory() as td:
        data = use_temp_home(td)
        import importlib
        import paths as _paths
        _paths.DATA_HOME = td
        importlib.reload(eg)
        eg.EMAIL_SENT = os.path.join(data, "email_sent.json")
        with open(os.path.join(td, "config", "search.yaml"), "w", encoding="utf-8") as fh:
            fh.write("dry_run: [this is not valid yaml\n")
        limits = eg.load_limits()
        check("unparseable config → dry_run ON", limits["dry_run"], True)
        check("and says it could not read it", limits["config_read"], False)
finally:
    es._smtp_send = _smtp_guard

print("\n" + "=" * 74)
print(f"RESULT: {'PASS ✅' if ok else 'FAIL ❌'} — the worker completes approve → preview →"
      " send → confirmation with no laptop,\n and every guardrail (cleared-only, send-once,"
      " /pause, throttle, cap, dry_run) refuses before SMTP.")
print("=" * 74 + "\n")
sys.exit(0 if ok else 1)
