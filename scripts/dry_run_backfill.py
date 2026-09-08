#!/usr/bin/env python3
"""Alfred · dry run — rehydrating jobs from Notion so a prepared backlog can be emailed.

The jobs prepared before the two-gate fix have no local trace of their recruiter address:
the enriched job object lived in the agent turn that built it. Notion kept it — HR Email,
Job ID, the tailored file paths, the Status — so a Notion row is enough to stage the email
draft and get the preview card out without re-running the pipeline.

This proves the round trip: job -> Notion row -> job -> staged draft -> preview card,
including the specific case of a row already at "Approved" whose local approval record
was never written. Offline; Telegram patched.
"""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import approval_poll as ap  # noqa: E402
import notion_schema as ns  # noqa: E402
import telegram_bot as tb  # noqa: E402

ok = True
sent: list = []


def check(label, got, want):
    global ok
    good = got == want
    ok = ok and good
    print(f"  [{'OK' if good else 'FAIL'}] {label}"
          + ("" if good else f"\n        got={got!r}\n        want={want!r}"))


def fake_api(method, data=None, files=None):
    sent.append({"method": method, "data": data or {}, "files": files})
    return {"ok": True, "result": {"message_id": len(sent)}}


def use_temp_home(td):
    data = os.path.join(td, "data")
    os.makedirs(data, exist_ok=True)
    tb._DATA = data
    for name, leaf in (("APPROVED_QUEUE", "approved_queue.json"),
                       ("EMAIL_DECISIONS", "email_decisions.json"),
                       ("EMAIL_DRAFTS", "email_drafts.json"),
                       ("AWAITING_EDIT", "email_awaiting_edit.json"),
                       ("JOB_DECISIONS", "job_decisions.json"),
                       ("EMAIL_PREVIEWS", "email_previews.json"),
                       ("PAUSE_FLAG", "paused.flag")):
        setattr(tb, name, os.path.join(data, leaf))
    return data


def prepared_job(td):
    """A job as a real run leaves it: tailored files on disk, email text written."""
    out = os.path.join(td, "output", "Acme_Designer")
    os.makedirs(out, exist_ok=True)
    resume = os.path.join(out, "Resume_Acme.pdf")
    cover = os.path.join(out, "CoverLetter_Acme.pdf")
    for path in (resume, cover):
        with open(path, "wb") as fh:
            fh.write(b"%PDF-1.4 fake")
    with open(os.path.join(out, "email_message.txt"), "w", encoding="utf-8") as fh:
        fh.write("Subject: Senior Product Designer — Kishan\n\nHi Sara,\n\nReal body.\n\nKishan")
    return {
        "job_id": "wellfound:99", "company": "Acme", "title": "Senior Product Designer",
        "location": "Remote", "url": "https://acme.example/jobs/99",
        "company_analysis": {"website": "https://acme.example"},
        "match": {"score": 82},
        "email": {"address": "hr@acme.com", "recipient_name": "Sara",
                  "confidence": 90, "source": "hunter"},
        "files": {"resume": resume, "cover_letter": cover},
        "what_i_changed": "Re-emphasized design-systems bullets.",
    }


print("\n" + "=" * 74)
print("Alfred dry run — Notion rehydration → staged draft → preview card (offline)")
print("=" * 74 + "\n")

tb._api = fake_api
tb._chat_id = lambda: "123"

print("Round trip — a job survives being written to Notion and read back")
with tempfile.TemporaryDirectory() as td:
    use_temp_home(td)
    job = prepared_job(td)
    row = {"url": "https://notion.so/abc",
           "properties": ns.row_properties(job, status="Approved")}
    back = ns.job_from_row(row)

    check("Job ID survives", back["job_id"], "wellfound:99")
    check("company survives", back["company"], "Acme")
    check("role survives", back["title"], "Senior Product Designer")
    check("recruiter address survives — the field nothing else kept",
          back["email"]["address"], "hr@acme.com")
    check("recruiter name survives", back["email"]["recipient_name"], "Sara")
    check("email source survives", back["email"]["source"], "hunter")
    check("match score survives", back["match"]["score"], 82)
    check("resume path survives", back["files"]["resume"], job["files"]["resume"])
    check("cover letter path survives", back["files"]["cover_letter"],
          job["files"]["cover_letter"])
    check("status is carried so an approval can be rehydrated", back["status"], "Approved")
    check("notion url captured", back["notion_url"], "https://notion.so/abc")
    check("channel read from the multi-select", back["channel"], "email")

    check("a bare properties map works too (query vs fetch shapes differ)",
          ns.job_from_row(ns.row_properties(job))["job_id"], "wellfound:99")
    check("a row with no Job ID is dropped, never half-staged",
          ns.jobs_from_rows([{"properties": ns.row_properties({"company": "X"})}]), [])

print("\nTHE BACKLOG CASE — Notion says Approved, Alfred has no record of it")
with tempfile.TemporaryDirectory() as td:
    data = use_temp_home(td)
    job = prepared_job(td)
    export = os.path.join(td, "rows.json")
    with open(export, "w", encoding="utf-8") as fh:
        import json
        json.dump({"results": [{"url": "https://notion.so/abc",
                                "properties": ns.row_properties(job, status="Approved")}]}, fh)

    check("before: Alfred has no idea this was approved", tb.is_approved("wellfound:99"), False)
    check("and nothing is pending a card", tb.pending_email_previews(), [])

    result = ap._stage_from_file(export)
    check("draft staged from the Notion row", result["staged"][0]["staged"], True)
    check("recipient recovered", result["staged"][0]["to"], "hr@acme.com")
    check("both PDFs attached",
          [os.path.basename(a) for a in result["staged"][0]["attachments"]],
          ["Resume_Acme.pdf", "CoverLetter_Acme.pdf"])
    check("approval rehydrated from the row's status",
          tb.job_decision("wellfound:99"), "approved")
    check("queued for the application agent", tb.approved_queue(), ["wellfound:99"])
    check("NOW it is pending its preview card", result["now_pending_preview"],
          ["wellfound:99"])

    sent.clear()
    swept = ap.sweep()
    check("sweep sends the card", [p["preview"] for p in swept["previews"]], ["sent"])
    card = [s["data"]["text"] for s in sent if "READY TO SEND" in s["data"].get("text", "")]
    check("the real email is previewed", "hr@acme.com" in card[0], True)
    check("with the real attachments", "Resume_Acme.pdf" in card[0], True)
    check("nothing left pending", tb.pending_email_previews(), [])

print("\nRe-running the backfill is safe")
with tempfile.TemporaryDirectory() as td:
    use_temp_home(td)
    job = prepared_job(td)
    export = os.path.join(td, "rows.json")
    import json
    rows = [{"properties": ns.row_properties(job, status="Approved")}]
    with open(export, "w", encoding="utf-8") as fh:
        json.dump(rows, fh)

    ap._stage_from_file(export)
    sent.clear()
    ap.sweep()
    first_cards = len([s for s in sent if "READY TO SEND" in s["data"].get("text", "")])

    tb.apply_edit("wellfound:99", "My hand-written version")
    ap._stage_from_file(export)          # backfill again
    check("a re-run never clobbers an edit the user made",
          tb.load_draft("wellfound:99")["body"], "My hand-written version")
    check("queue not duplicated", tb.approved_queue(), ["wellfound:99"])
    sent.clear()
    ap.sweep()
    second_cards = len([s for s in sent if "READY TO SEND" in s["data"].get("text", "")])
    check("and no duplicate card is sent", (first_cards, second_cards), (1, 0))

print("\nRows that must NOT produce an email")
with tempfile.TemporaryDirectory() as td:
    use_temp_home(td)
    job = prepared_job(td)
    import json

    portal_only = dict(job, email={"address": None, "source": "none"}, job_id="portal:7")
    skipped = dict(job, job_id="skip:8")
    export = os.path.join(td, "rows.json")
    with open(export, "w", encoding="utf-8") as fh:
        json.dump([{"properties": ns.row_properties(portal_only, status="Approved")},
                   {"properties": ns.row_properties(skipped, status="Skipped")}], fh)

    result = ap._stage_from_file(export)
    by_id = {r["job_id"]: r for r in result["staged"]}
    check("portal-only job stages no email", by_id["portal:7"]["staged"], False)
    check("a Skipped row is not resurrected as approved",
          tb.job_decision("skip:8"), None)
    check("neither is pending a preview card", result["now_pending_preview"], [])

print("\n" + "=" * 74)
print(f"RESULT: {'PASS ✅' if ok else 'FAIL ❌'} — a job prepared days ago is recoverable from"
      " its Notion row alone:\n staged, its approval rehydrated, its preview card sent — and"
      " re-running it changes nothing.")
print("=" * 74 + "\n")
sys.exit(0 if ok else 1)
