#!/usr/bin/env python3
"""Alfred · dry run — staged email → Gmail Drafts, resume only.

Guards the promises the draft path makes: the cover letter never rides along, a
missing resume is reported rather than silently swapped for whatever else is on
disk, /pause stops it, a second run does not duplicate nineteen drafts, and no
IMAP connection is ever opened.
"""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import approval_poll as ap  # noqa: E402
import email_send as es  # noqa: E402
import telegram_bot as tb  # noqa: E402

ok = True
appended: list = []


def check(label, got, want):
    global ok
    good = got == want
    ok = ok and good
    print(f"  [{'OK' if good else 'FAIL'}] {label}"
          + ("" if good else f"\n        got={got!r}\n        want={want!r}"))


def fake_append(msg):
    appended.append(msg)
    return "[Gmail]/Drafts"


def use_temp_state(td):
    tb._DATA = td
    tb.PAUSE_FLAG = os.path.join(td, "paused.flag")
    tb.APPROVED_QUEUE = os.path.join(td, "approved_queue.json")
    tb.EMAIL_DECISIONS = os.path.join(td, "email_decisions.json")
    tb.EMAIL_DRAFTS = os.path.join(td, "email_drafts.json")
    tb.JOB_DECISIONS = os.path.join(td, "job_decisions.json")
    tb.EMAIL_PREVIEWS = os.path.join(td, "email_previews.json")
    tb.GMAIL_DRAFTS = os.path.join(td, "gmail_drafts.json")


def make_job(td, with_resume=True):
    out = os.path.join(td, "output", "Acme_UX")
    os.makedirs(out, exist_ok=True)
    names = ["CoverLetter_Acme.pdf"] + (["Resume_Acme.pdf"] if with_resume else [])
    for n in names:
        with open(os.path.join(out, n), "wb") as fh:
            fh.write(b"%PDF-1.4 fake")
    with open(os.path.join(out, "email_message.txt"), "w", encoding="utf-8") as fh:
        fh.write("Subject: UX Designer — Kishan\n\nHi there,\n\nI'd love to apply.\n\nKishan")
    return {"job_id": "acme:1", "company": "Acme", "title": "UX Designer",
            "email": {"address": "hr@acme.com", "source": "career-page", "confidence": 90},
            "files": {"resume": os.path.join(out, "Resume_Acme.pdf"),
                      "cover_letter": os.path.join(out, "CoverLetter_Acme.pdf")},
            "output_dir": out}


_real_append, _real_smtp = es._imap_append, es._smtp_send
es._imap_append = fake_append
es._smtp_send = lambda m: (_ for _ in ()).throw(AssertionError("SMTP must never run here"))
os.environ.setdefault("GMAIL_ADDRESS", "kishan@example.com")

print("\nAlfred · Gmail draft dry run")
print("=" * 74)
try:
    print("\nresume_only picks by name, never by position")
    check("picks the resume out of both",
          es.resume_only(["/o/CoverLetter_A.pdf", "/o/Resume_A.pdf"]), ["/o/Resume_A.pdf"])
    check("a missing resume yields nothing, not the cover letter",
          es.resume_only(["/o/CoverLetter_A.pdf"]), [])
    check("case does not matter", es.resume_only(["/o/resume_a.pdf"]), ["/o/resume_a.pdf"])

    print("\nA staged job becomes one Gmail draft carrying the resume alone")
    with tempfile.TemporaryDirectory() as td:
        use_temp_state(td)
        appended.clear()
        job = make_job(td)
        tb.stage_email_draft(job)
        rec = ap.draft_to_gmail("acme:1")
        check("drafted", rec["draft"], "created")
        check("to the recruiter", rec["to"], "hr@acme.com")
        check("subject came from the tailored file", rec["subject"], "UX Designer — Kishan")
        check("resume attached, cover letter NOT", rec["attachments"], ["Resume_Acme.pdf"])
        check("exactly one message appended", len(appended), 1)
        check("no warning when the resume was there", rec.get("warning"), None)

        print("\nA second pass does not duplicate it")
        again = ap.draft_all()
        check("skipped", [d["draft"] for d in again["drafts"]], ["skipped"])
        check("and says why", again["drafts"][0]["reason"], "already in Gmail Drafts")
        check("nothing more appended", len(appended), 1)
        check("--redraft overrides deliberately",
              ap.draft_all(force=True)["drafts"][0]["draft"], "created")

    print("\nA job with no resume is drafted bare AND told so")
    with tempfile.TemporaryDirectory() as td:
        use_temp_state(td)
        appended.clear()
        job = make_job(td, with_resume=False)
        job["files"] = {"cover_letter": job["files"]["cover_letter"]}
        tb.stage_email_draft(job)
        rec = ap.draft_to_gmail("acme:1")
        check("still drafted", rec["draft"], "created")
        check("with nothing attached", rec["attachments"], [])
        check("and the warning names the fix",
              "attach it in Gmail" in (rec.get("warning") or ""), True)

    print("\n/pause stops drafting; a decided email is never re-drafted")
    with tempfile.TemporaryDirectory() as td:
        use_temp_state(td)
        appended.clear()
        tb.stage_email_draft(make_job(td))
        tb.set_pause(True)
        rec = ap.draft_to_gmail("acme:1")
        check("refused", rec["status"], "PAUSED")
        check("nothing appended", len(appended), 0)
        tb.set_pause(False)
        tb.record_email_decision("acme:1", "cancelled")
        check("a cancelled email drops out of the target set",
              ap.draft_all()["drafts"], [])

    print("\nAn IMAP failure is reported, never raised")
    with tempfile.TemporaryDirectory() as td:
        use_temp_state(td)
        tb.stage_email_draft(make_job(td))
        es._imap_append = lambda m: (_ for _ in ()).throw(OSError("login refused"))
        rec = ap.draft_to_gmail("acme:1")
        check("FAILED, not a traceback", rec["draft"], "failed")
        check("real error text carried", "login refused" in rec["error"], True)
        check("not recorded as drafted, so a retry works", tb.gmail_drafted("acme:1"), False)
        es._imap_append = fake_append
finally:
    es._imap_append, es._smtp_send = _real_append, _real_smtp

print("\n" + "=" * 74)
print(f"RESULT: {'PASS ✅' if ok else 'FAIL ❌'} — drafts carry the resume alone, never"
      " duplicate, honour /pause,\n report a bare draft honestly, and open no IMAP or"
      " SMTP connection.")
print("=" * 74 + "\n")
sys.exit(0 if ok else 1)
