#!/usr/bin/env python3
"""Alfred · dry run — approve tap → email preview card, across runs.

The regression this guards: a job approved in Telegram whose Notion row flipped to
Approved but whose Send / Edit / Cancel card never arrived. It happened because the
second gate lived in prose executed mid-run, while the tap is normally reconciled by a
LATER run that no longer holds the job — nothing left on disk to build the email from,
so nothing was sent and nothing said so.

So this exercises the whole chain from on-disk state only, in a temp home, with the
Telegram API and SMTP both patched to prove nothing leaves the machine.
"""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import approval_poll as ap  # noqa: E402
import email_send as es  # noqa: E402
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


def texts_of(method="sendMessage"):
    return [s["data"].get("text", "") for s in sent if s["method"] == method]


def use_temp_state(td):
    """Point every state file at `td` — the module resolves them once, at import."""
    tb._DATA = td
    tb.STATE_PATH = os.path.join(td, "telegram_state.json")
    tb.PAUSE_FLAG = os.path.join(td, "paused.flag")
    tb.APPROVED_QUEUE = os.path.join(td, "approved_queue.json")
    tb.EMAIL_DECISIONS = os.path.join(td, "email_decisions.json")
    tb.EMAIL_DRAFTS = os.path.join(td, "email_drafts.json")
    tb.AWAITING_EDIT = os.path.join(td, "email_awaiting_edit.json")
    tb.JOB_DECISIONS = os.path.join(td, "job_decisions.json")
    tb.EMAIL_PREVIEWS = os.path.join(td, "email_previews.json")
    tb.PORTAL_NOTICES = os.path.join(td, "portal_only_notices.json")


def make_output_dir(td, subject_line=True):
    out = os.path.join(td, "output", "Acme_Senior_Product_Designer")
    os.makedirs(out, exist_ok=True)
    for name in ("Resume_Acme.pdf", "CoverLetter_Acme.pdf"):
        with open(os.path.join(out, name), "wb") as fh:
            fh.write(b"%PDF-1.4 fake")
    header = "Subject: Senior Product Designer — Kishan\n\n" if subject_line else ""
    with open(os.path.join(out, "email_message.txt"), "w", encoding="utf-8") as fh:
        fh.write(header + "Hi Sara,\n\nI'd love to be considered.\n\nKishan")
    return out


def job_for(out):
    return {
        "job_id": "wellfound:99",
        "company": "Acme",
        "title": "Senior Product Designer",
        "location": "Remote",
        "url": "https://acme.example/jobs/99",
        "notion_url": "https://notion.so/abc",
        "match": {"score": 82},
        "email": {"address": "hr@acme.com", "confidence": 90, "source": "hunter"},
        "files": {"resume": os.path.join(out, "Resume_Acme.pdf"),
                  "cover_letter": os.path.join(out, "CoverLetter_Acme.pdf")},
        "what_i_changed": "Re-emphasized design-systems bullets.",
    }


print("\n" + "=" * 74)
print("Alfred dry run — approve → email preview card (offline, sends nothing)")
print("=" * 74 + "\n")

tb._api = fake_api
tb._chat_id = lambda: "123"
_smtp_guard = es._smtp_send
es._smtp_send = lambda m: (_ for _ in ()).throw(
    AssertionError("SMTP reached in a dry run — the send chokepoint leaked"))

try:
    print("Staging — the draft is written BEFORE the card, from the tailored files")
    with tempfile.TemporaryDirectory() as td:
        use_temp_state(td)
        out = make_output_dir(td)
        job = job_for(out)

        check("email_message.txt Subject: line parsed",
              tb.parse_email_message("Subject: A title\n\nBody here"),
              {"subject": "A title", "body": "Body here"})
        check("no Subject: line → all body",
              tb.parse_email_message("Just a body")["body"], "Just a body")

        draft = tb.stage_email_draft(job)
        check("draft staged", draft is not None, True)
        check("recipient from company-research", draft["to"], "hr@acme.com")
        check("subject from the tailored file", draft["subject"],
              "Senior Product Designer — Kishan")
        check("body from the tailored file", "I'd love to be considered." in draft["body"], True)
        check("both PDFs attached", [os.path.basename(a) for a in draft["attachments"]],
              ["Resume_Acme.pdf", "CoverLetter_Acme.pdf"])
        check("job snapshot rides along so a later run can render the card",
              tb.draft_job("wellfound:99")["company"], "Acme")

        check("a job with no recruiter address stages nothing",
              tb.stage_email_draft({"job_id": "x:1", "email": {}}), None)
        check("a job with no tailored email text stages nothing",
              tb.stage_email_draft({"job_id": "x:2", "email": {"address": "a@b.com"}}), None)

        tb.apply_edit("wellfound:99", "User's own words")
        check("staging never clobbers an edit the user already made",
              tb.stage_email_draft(job)["body"], "User's own words")

    print("\nsend_review_card stages the draft itself — no agent has to remember")
    with tempfile.TemporaryDirectory() as td:
        use_temp_state(td)
        sent.clear()
        out = make_output_dir(td)
        job = job_for(out)
        tb.send_review_card(job, job["files"]["resume"], job["files"]["cover_letter"])
        check("review card sent", sent[0]["method"], "sendMessage")
        check("both PDFs uploaded", sum(1 for s in sent if s["method"] == "sendDocument"), 2)
        check("draft staged as a side effect", tb.load_draft("wellfound:99")["to"], "hr@acme.com")
        check("staged but NOT pending a card — the user has not approved yet",
              tb.pending_email_previews(), [])

    print("\nTHE REGRESSION — a tap reconciled by a LATER run still gets its card")
    with tempfile.TemporaryDirectory() as td:
        use_temp_state(td)
        out = make_output_dir(td)
        job = job_for(out)
        tb.send_review_card(job, job["files"]["resume"], job["files"]["cover_letter"])

        # New run, new process: only the files on disk survive. The tap arrives now.
        sent.clear()
        events, _ = tb.parse_updates({"result": [{
            "update_id": 5,
            "callback_query": {"id": "cb1", "data": "approve|wellfound:99"},
        }]}, 0)
        summary = ap.dispatch(events)

        check("approve recorded durably", tb.job_decision("wellfound:99"), "approved")
        check("queued for the application agent", tb.approved_queue(), ["wellfound:99"])
        check("preview card sent in the same pass",
              [p["preview"] for p in summary["previews"]], ["sent"])
        preview = [t for t in texts_of() if "READY TO SEND" in t]
        check("card is the email preview", len(preview), 1)
        check("shows the real recipient", "hr@acme.com" in preview[0], True)
        check("shows the real attachments", "Resume_Acme.pdf" in preview[0], True)
        kb = [s for s in sent if "READY TO SEND" in s["data"].get("text", "")][0]["data"]
        check("carries Send / Edit / Cancel",
              [b["text"] for b in __import__("json").loads(kb["reply_markup"])["inline_keyboard"][0]],
              ["📧 Send", "✏️ Edit", "🚫 Cancel"])
        check("tap acknowledged", any(s["method"] == "answerCallbackQuery" for s in sent), True)
        check("nothing left pending", tb.pending_email_previews(), [])

    print("\nSelf-heal — a job already stuck (approved, no card) gets swept up")
    with tempfile.TemporaryDirectory() as td:
        use_temp_state(td)
        out = make_output_dir(td)
        job = job_for(out)
        tb.stage_email_draft(job)
        tb.record_job_decision("wellfound:99", "approved")   # approved by an older run

        sent.clear()
        check("sweep finds it", tb.pending_email_previews(), ["wellfound:99"])
        result = ap.sweep()
        check("card sent by the sweep", [p["preview"] for p in result["previews"]], ["sent"])
        sent.clear()
        check("second sweep is a no-op — no duplicate cards", ap.sweep()["previews"], [])
        check("and sent nothing", sent, [])

        # An approved job whose queue entry was already drained still counts as approved.
        tb.record_email_decision("wellfound:99", "cancelled")
        check("a decided email is never re-asked", tb.pending_email_previews(), [])

    print("\nEdit — prompt, capture, re-preview; nothing is decided by editing")
    with tempfile.TemporaryDirectory() as td:
        use_temp_state(td)
        out = make_output_dir(td)
        tb.stage_email_draft(job_for(out))
        tb.record_job_decision("wellfound:99", "approved")

        sent.clear()
        events, _ = tb.parse_updates({"result": [{
            "update_id": 1, "callback_query": {"id": "cb2", "data": "edit|wellfound:99"}}]}, 0)
        ap.dispatch(events)
        check("edit prompt sent", any("EDITING" in t for t in texts_of()), True)
        check("capture armed", tb.get_awaiting_edit(), "wellfound:99")
        check("no decision recorded by an edit", tb.email_decision("wellfound:99"), None)

        sent.clear()
        events, _ = tb.parse_updates({"result": [{
            "update_id": 2,
            "message": {"text": "Subject: Rewritten\nMy own words"}}]}, 0)
        summary = ap.dispatch(events)
        check("edit applied", summary["edits_applied"], ["wellfound:99"])
        check("capture disarmed", tb.get_awaiting_edit(), None)
        check("draft carries the new subject", tb.load_draft("wellfound:99")["subject"], "Rewritten")
        check("attachments survived the edit",
              len(tb.load_draft("wellfound:99")["attachments"]), 2)
        re_preview = [t for t in texts_of() if "READY TO SEND" in t]
        check("preview re-sent with the new words", "My own words" in re_preview[0], True)

        sent.clear()
        check("a stray message with nothing awaiting an edit is ignored",
              ap.dispatch(tb.parse_updates({"result": [
                  {"update_id": 3, "message": {"text": "hello?"}}]}, 0)[0])["edits_applied"], [])

    print("\nSend / Cancel / Skip — recorded, acknowledged, and email-free")
    with tempfile.TemporaryDirectory() as td:
        use_temp_state(td)
        out = make_output_dir(td)
        tb.stage_email_draft(job_for(out))
        sent.clear()
        events, _ = tb.parse_updates({"result": [
            {"update_id": 1, "callback_query": {"id": "a", "data": "send|wellfound:99"}},
            {"update_id": 2, "callback_query": {"id": "b", "data": "cancel|other:1"}},
            {"update_id": 3, "callback_query": {"id": "c", "data": "skip|other:2"}},
        ]}, 0)
        summary = ap.dispatch(events)
        check("Send recorded as cleared", tb.email_decision("wellfound:99"), "cleared")
        check("Cancel recorded", tb.email_decision("other:1"), "cancelled")
        check("Skip recorded durably", tb.job_decision("other:2"), "skipped")
        check("every tap acknowledged",
              sum(1 for s in sent if s["method"] == "answerCallbackQuery"), 3)
        check("Cancel's ack says the portal still goes ahead",
              any("portal" in (s["data"].get("text") or "")
                  for s in sent if s["method"] == "answerCallbackQuery"), True)
        check("a Send tap sends no email here — that stays with the application agent",
              summary["email_cleared"], ["wellfound:99"])

    print("\nPortal-only job — approve is answered honestly, no phantom email card")
    with tempfile.TemporaryDirectory() as td:
        use_temp_state(td)
        sent.clear()
        events, _ = tb.parse_updates({"result": [{
            "update_id": 1, "callback_query": {"id": "d", "data": "approve|portal:7"}}]}, 0)
        summary = ap.dispatch(events)
        check("approved anyway", summary["approved"], ["portal:7"])
        check("no preview claimed", [p["preview"] for p in summary["previews"]], ["skipped"])
        check("ack says portal only",
              any("portal only" in (s["data"].get("text") or "") for s in sent), True)
        check("no email preview card went out",
              [t for t in texts_of() if "READY TO SEND" in t], [])

    print("\nA tap is only confirmed to Telegram AFTER it has had its consequence")
    with tempfile.TemporaryDirectory() as td:
        use_temp_state(td)
        sent.clear()
        updates = {"result": [{"update_id": 4100,
                               "callback_query": {"id": "z", "data": "approve|wellfound:99"}}]}
        tb._api = lambda m, data=None, files=None: updates
        events, new_offset = tb.poll_responses(commit=False)
        check("the tap was read", [e["decision"] for e in events], ["approve"])
        check("but the offset is NOT yet advanced — a crash here replays the tap",
              tb.load_offset(), 0)
        tb._api = fake_api
        ap.dispatch(events)
        tb.save_offset(new_offset)
        check("committed only once the approve was acted on", tb.load_offset(), 4101)

    print("\nAn approved job with no draft is told so, instead of going quiet")
    with tempfile.TemporaryDirectory() as td:
        use_temp_state(td)
        sent.clear()
        tb.record_job_decision("portal:7", "approved")
        tb.enqueue_approved("portal:7")
        check("invisible to the old preview sweep", tb.pending_email_previews(), [])
        check("but visible as approved-without-draft", tb.approved_without_draft(), ["portal:7"])
        summary = ap.sweep()
        check("a portal-only notice goes out",
              [n["job_id"] for n in summary["notices"]], ["portal:7"])
        check("and it says why", any("PORTAL-ONLY" in t for t in texts_of()), True)
        sent.clear()
        check("said once, not on every sweep", ap.sweep()["notices"], [])

    print("\n--resend puts back a card Alfred sent but the user never saw")
    with tempfile.TemporaryDirectory() as td:
        use_temp_state(td)
        out = make_output_dir(td)
        job = job_for(out)
        tb.stage_email_draft(job)
        tb.record_job_decision(job["job_id"], "approved")
        tb.mark_preview_sent(job["job_id"], 4242)        # Telegram took it; the phone didn't
        sent.clear()
        check("nothing pending — the record says it was carded",
              tb.pending_email_previews(), [])
        check("yet the job is still waiting for an answer",
              tb.awaiting_email_answer(), ["wellfound:99"])
        check("a plain sweep leaves the user stuck", ap.sweep()["previews"], [])
        summary = ap.sweep(resend=True)
        check("--resend sends it again", [p["preview"] for p in summary["previews"]], ["sent"])
        check("and it is the real email preview",
              any("READY TO SEND" in t for t in texts_of()), True)
        tb.record_email_decision(job["job_id"], "cancelled")
        sent.clear()
        check("a decided email drops out of the target list entirely",
              tb.awaiting_email_answer(), [])
        check("so --resend never re-asks it",
              ap.sweep(resend=True)["previews"], [])
        check("and no card was put on the wire", texts_of(), [])

    print("\nThe Notion half is emitted as a plan, since no script can write Notion")
    with tempfile.TemporaryDirectory() as td:
        use_temp_state(td)
        import email_gate
        email_gate.EMAIL_SENT = os.path.join(td, "email_sent.json")
        tb.record_job_decision("wellfound:99", "approved")
        tb.record_job_decision("remoteok:12", "skipped")
        plan = {row["job_id"]: row["status"] for row in ap.notion_plan()}
        check("approve → Approved", plan.get("wellfound:99"), "Approved")
        check("skip → Skipped", plan.get("remoteok:12"), "Skipped")
        email_gate.record_sent("wellfound:99", "SENT", to="hr@acme.com")
        plan = {row["job_id"]: row["status"] for row in ap.notion_plan()}
        check("a job whose email actually left reads Applied, not Approved",
              plan.get("wellfound:99"), "Applied")

    print("\nThe backlog case: a Notion export becomes one card per job, in one command")
    with tempfile.TemporaryDirectory() as td:
        use_temp_state(td)
        out = make_output_dir(td)
        sent.clear()

        # Two rows exactly as Notion returns them: one still at Ready for Review
        # (never approved — the case the old sweep could not reach), one with no
        # recruiter address at all.
        import json as _json
        import notion_schema as ns
        rows = {"results": [
            {"url": "https://notion.so/aaa", "properties": {
                ns.JOB_ID: {"rich_text": [{"plain_text": "wellfound:99"}]},
                ns.COMPANY: {"title": [{"plain_text": "Acme"}]},
                ns.ROLE: {"rich_text": [{"plain_text": "Senior Product Designer"}]},
                ns.HR_EMAIL: {"email": "hr@acme.com"},
                ns.STATUS: {"select": {"name": "Ready for Review"}},
                ns.RESUME_FILE: {"rich_text": [
                    {"plain_text": os.path.join(out, "Resume_Acme.pdf")}]},
                ns.COVER_LETTER_FILE: {"rich_text": [
                    {"plain_text": os.path.join(out, "CoverLetter_Acme.pdf")}]},
            }},
            {"url": "https://notion.so/bbb", "properties": {
                ns.JOB_ID: {"rich_text": [{"plain_text": "portal:7"}]},
                ns.COMPANY: {"title": [{"plain_text": "Globex"}]},
                ns.STATUS: {"select": {"name": "Ready for Review"}},
            }},
        ]}
        rows_path = os.path.join(td, "notion_rows.json")
        with open(rows_path, "w", encoding="utf-8") as fh:
            _json.dump(rows, fh)

        staged = ap._stage_from_file(rows_path)
        by_id = {r["job_id"]: r for r in staged["staged"]}
        check("the row with an address staged a draft", by_id["wellfound:99"]["staged"], True)
        check("and kept the recruiter address", by_id["wellfound:99"]["to"], "hr@acme.com")
        check("the row without one did not, and says why",
              by_id["portal:7"]["reason"], "no recruiter address or no email_message.txt")
        check("neither was silently marked approved",
              tb.approved_jobs(), [])

        check("so the normal sweep reaches nothing — this is the old dead end",
              ap.sweep()["previews"], [])
        summary = ap.sweep(all_jobs=True)
        check("--preview-all cards it anyway",
              [(p["job_id"], p["preview"]) for p in summary["previews"]],
              [("wellfound:99", "sent")])
        check("and it is the real email, built from the draft",
              any("READY TO SEND" in t and "hr@acme.com" in t for t in texts_of()), True)
        check("with the real attachments named",
              any("Resume_Acme.pdf" in t and "CoverLetter_Acme.pdf" in t
                  for t in texts_of()), True)

        sent.clear()
        check("answering one takes it out of the set",
              (tb.record_email_decision("wellfound:99", "cleared"),
               ap.sweep(all_jobs=True)["previews"])[1], [])

    print("\nPause still works through the same poll")
    with tempfile.TemporaryDirectory() as td:
        use_temp_state(td)
        tb._api = lambda m, data=None, files=None: {"ok": True, "result": [
            {"update_id": 1, "message": {"text": "/pause"}}]}
        events, _ = tb.poll_responses()
        check("/pause flag set by the poll", tb.is_paused(), True)
        check("reported to the caller", ap.dispatch(events)["commands"], ["pause"])
        tb._api = fake_api
finally:
    es._smtp_send = _smtp_guard

print("\n" + "=" * 74)
print(f"RESULT: {'PASS ✅' if ok else 'FAIL ❌'} — the draft is staged before the card, an"
      " approve tap reconciled by any later run\n gets its Send/Edit/Cancel preview, and a"
      " job stuck without one is swept up. No Telegram call, no SMTP.")
print("=" * 74 + "\n")
sys.exit(0 if ok else 1)
