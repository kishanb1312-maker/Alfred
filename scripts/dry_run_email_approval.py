#!/usr/bin/env python3
"""Alfred · dry run — the second Telegram gate (email preview → Send/Cancel).

Offline. Exercises the callback vocabulary, the preview text built from a real
EmailMessage, and the decision store that gates the email channel. Sends nothing:
no Telegram API call, no SMTP connection.
"""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import telegram_bot as tb  # noqa: E402
import email_send as es  # noqa: E402

ok = True


def check(label, got, want):
    global ok
    good = got == want
    ok = ok and good
    print(f"  [{'OK' if good else 'FAIL'}] {label}"
          + ("" if good else f"\n        got={got!r}\n        want={want!r}"))


print("\n" + "=" * 74)
print("Alfred dry run — email approval gate (offline, sends nothing)")
print("=" * 74 + "\n")

print("Callback vocabulary — both gates share one parser")
check("approve", tb.parse_callback_data("approve|j:1"), {"decision": "approve", "job_id": "j:1"})
check("skip", tb.parse_callback_data("skip|j:1"), {"decision": "skip", "job_id": "j:1"})
check("send", tb.parse_callback_data("send|j:1"), {"decision": "send", "job_id": "j:1"})
check("cancel", tb.parse_callback_data("cancel|j:1"), {"decision": "cancel", "job_id": "j:1"})
check("unknown decision rejected", tb.parse_callback_data("delete|j:1"), None)
check("empty job_id rejected", tb.parse_callback_data("send|"), None)

print("\nCallback payloads stay inside Telegram's 64-byte cap")
long_id = "linkedin_easy_apply:4012345678"
for d in ("approve", "skip", "send", "cancel"):
    payload = tb.make_callback_data(d, long_id)
    check(f"{d} payload {len(payload)}B ≤ 64", len(payload.encode()) <= 64, True)

print("\nKeyboards")
kb = tb.build_email_keyboard("j:1")["inline_keyboard"][0]
check("two buttons", len(kb), 2)
check("Send carries send|", kb[0]["callback_data"], "send|j:1")
check("Cancel carries cancel|", kb[1]["callback_data"], "cancel|j:1")

print("\nPreview is built from the REAL message")
with tempfile.TemporaryDirectory() as td:
    resume = os.path.join(td, "Kishan_Resume.pdf")
    with open(resume, "wb") as fh:
        fh.write(b"%PDF-1.4 fake")
    missing = os.path.join(td, "never_built.pdf")  # deliberately absent
    msg = es.build_message(
        to="hr@acme.com",
        subject="Application: Senior Product Designer",
        body="Hi Sara,\n\nI'd love to be considered.\n\nKishan",
        attachments=[resume, missing],
        from_addr="me@gmail.com",
    )
    job = {"job_id": "wellfound:99", "company": "Acme", "title": "Senior Product Designer"}
    text = tb.build_email_preview_text(job, msg)

    check("From shown", "me@gmail.com" in text, True)
    check("To shown", "hr@acme.com" in text, True)
    check("Subject shown", "Application: Senior Product Designer" in text, True)
    check("body shown", "I'd love to be considered." in text, True)
    check("attached file named", "Kishan_Resume.pdf" in text, True)
    check("file that failed to build is NOT claimed", "never_built.pdf" in text, False)
    check("says Cancel spares the portal", "does NOT cancel the portal" in text.replace("\n", " "), True)
    check("fits one Telegram message (4096)", len(text) < 4096, True)

    empty = es.build_message(to="a@b.com", subject="s", body="b", from_addr="me@gmail.com")
    check("no attachments → warns rather than staying silent",
          "nothing will be attached" in tb.build_email_preview_text(job, empty), True)

    long_body = es.build_message(to="a@b.com", subject="s", body="x" * 5000,
                                 from_addr="me@gmail.com")
    check("long body truncated, card still valid",
          len(tb.build_email_preview_text(job, long_body)) < 4096, True)

print("\nDecision store gates the email channel")
with tempfile.TemporaryDirectory() as td:
    tb.EMAIL_DECISIONS = os.path.join(td, "email_decisions.json")
    tb._DATA = td

    check("no answer yet → None (must NOT send)", tb.email_decision("j:1"), None)
    check("first Send recorded", tb.record_email_decision("j:1", "cleared"), True)
    check("reads back cleared", tb.email_decision("j:1"), "cleared")
    check("duplicate tap is a no-op", tb.record_email_decision("j:1", "cleared"), False)

    check("Cancel recorded", tb.record_email_decision("j:2", "cancelled"), True)
    check("reads back cancelled", tb.email_decision("j:2"), "cancelled")
    check("cancelled cannot be flipped to cleared by a stray tap",
          (tb.record_email_decision("j:2", "cleared"), tb.email_decision("j:2")),
          (False, "cancelled"))

    try:
        tb.record_email_decision("j:3", "approve")
        check("invalid decision rejected", "no raise", "ValueError")
    except ValueError:
        check("invalid decision rejected", True, True)

    check("unknown job still None", tb.email_decision("never-seen"), None)

print("\n" + "=" * 74)
print(f"RESULT: {'PASS ✅' if ok else 'FAIL ❌'} — two-gate flow: preview built from the real"
      " message, email sends only on an explicit Send tap. Nothing sent.")
print("=" * 74 + "\n")
sys.exit(0 if ok else 1)
