"""Alfred · Approval Gate DRY-RUN (OFFLINE — asserts NO real HTTP calls).

Two halves, both offline:
  A. Build the EXACT outgoing card payload for a sample job — text, inline-keyboard
     JSON, and which PDFs would attach vs. be skipped (missing).
  B. Feed a FAKE getUpdates response (an "Approve" callback + a "/pause" message)
     through the real parser and show it yields the right {job_id, decision} and a
     pause signal.

Safety: telegram_bot._api (the ONE network chokepoint) is monkeypatched to a spy
that RAISES if called, and TELEGRAM_BOT_TOKEN is left unset — so any accidental
live call fails loudly. At the end we assert the spy was never invoked.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import telegram_bot as tb  # noqa: E402


# ---------------------------------------------------------------------------
# Network tripwire: replace the single HTTP chokepoint with a raising spy.
# ---------------------------------------------------------------------------

class _NetworkTouched(Exception):
    pass


_spy_calls = []


def _spy_api(method, data=None, files=None):
    _spy_calls.append(method)
    raise _NetworkTouched(f"_api('{method}') called — dry-run must be offline!")


tb._api = _spy_api  # any network attempt now raises


# ---------------------------------------------------------------------------
# Sample job (enriched + tailored shape).
# ---------------------------------------------------------------------------

FAKE_JOB = {
    "job_id": "linkedin:FAKE-A1",
    "title": "Site Reliability Engineer",
    "company": "Globex Systems",
    "company_analysis": {"website": "https://globex.example"},
    "location": "Remote (India)",
    "url": "https://example.com/fake/A1",
    "notion_url": "https://notion.so/fake-page-A1",
    "match": {"score": 91},
    "email": {"address": "priya.sharma@globex.example", "confidence": 92, "source": "hunter"},
    "what_i_changed": ("Summary rewrite + 2 bullet re-emphases (Kubernetes, AWS, "
                       "Terraform).\n(second line ignored in the one-liner)"),
}


def main() -> int:
    print("=" * 74)
    print("Alfred · Approval Gate — DRY RUN (OFFLINE; _api spy raises on call)")
    print("=" * 74)

    # ---- A. Outgoing card payload -----------------------------------------
    workdir = tempfile.mkdtemp(prefix="alfred_tg_")
    resume_pdf = os.path.join(workdir, "Resume_GlobexSystems.pdf")
    with open(resume_pdf, "wb") as fh:              # present → will attach
        fh.write(b"%PDF-1.4 fake resume for dry-run\n")
    cover_pdf = os.path.join(workdir, "CoverLetter_GlobexSystems.pdf")  # absent → skipped

    present, missing = tb.resolve_attachments(FAKE_JOB, resume_pdf, cover_pdf)
    card_text = tb.build_card_text(FAKE_JOB, missing)
    keyboard = tb.build_inline_keyboard(FAKE_JOB["job_id"])

    print("\nA) CARD TEXT (exactly what would be sent):")
    print("-" * 74)
    print(card_text)
    print("-" * 74)

    print("\nInline keyboard JSON (reply_markup):")
    print(json.dumps(keyboard, indent=2, ensure_ascii=False))

    print("\nAttachments:")
    for label, path in present:
        print(f"  ✅ attach   {label}: {os.path.basename(path)}")
    for label in missing:
        print(f"  ⏭️  skip     {label}: (file missing — noted in card)")

    # ---- B. Incoming updates parse ----------------------------------------
    fake_get_updates = {
        "ok": True,
        "result": [
            {
                "update_id": 1001,
                "callback_query": {
                    "id": "cbq-approve-1",
                    "data": tb.make_callback_data("approve", "linkedin:FAKE-A1"),
                    "from": {"id": 42, "first_name": "Kishan"},
                    "message": {"message_id": 555, "chat": {"id": 42}},
                },
            },
            {
                "update_id": 1002,
                "message": {"message_id": 556, "chat": {"id": 42}, "text": "/pause"},
            },
        ],
    }

    events, new_offset = tb.parse_updates(fake_get_updates, current_offset=1000)

    print("\n" + "=" * 74)
    print("B) PARSED getUpdates → events:")
    print(json.dumps(events, indent=2, ensure_ascii=False))
    print(f"new_offset = {new_offset}")

    # ---- Assertions --------------------------------------------------------
    print("\n" + "-" * 74)
    print("Assertions:")
    failures = []

    decisions = [e for e in events if e.get("type") == "decision"]
    commands = [e for e in events if e.get("type") == "command"]

    ok_decision = (len(decisions) == 1
                   and decisions[0]["job_id"] == "linkedin:FAKE-A1"
                   and decisions[0]["decision"] == "approve"
                   and decisions[0]["callback_query_id"] == "cbq-approve-1")
    failures += [] if ok_decision else ["Approve callback did not parse correctly"]
    print(f"  [{'OK' if ok_decision else 'XX'}] Approve → "
          f"{{job_id: {decisions[0]['job_id'] if decisions else None!r}, "
          f"decision: {decisions[0]['decision'] if decisions else None!r}}}")

    ok_pause = any(c.get("command") == "pause" for c in commands)
    failures += [] if ok_pause else ["/pause not detected"]
    print(f"  [{'OK' if ok_pause else 'XX'}] /pause detected → pause signal raised")

    ok_offset = new_offset == 1003
    failures += [] if ok_offset else [f"offset should advance to 1003, got {new_offset}"]
    print(f"  [{'OK' if ok_offset else 'XX'}] offset advances past processed updates "
          f"(→ {new_offset})")

    ok_attach = ([l for l, _ in present] == ["Resume"] and missing == ["Cover Letter"])
    failures += [] if ok_attach else ["attachment resolution wrong"]
    print(f"  [{'OK' if ok_attach else 'XX'}] attachments: present={[l for l,_ in present]}, "
          f"missing={missing}")

    ok_callback_fmt = (tb.parse_callback_data(
        tb.make_callback_data("skip", "adzuna:X")) == {"decision": "skip", "job_id": "adzuna:X"})
    failures += [] if ok_callback_fmt else ["callback_data round-trip broken"]
    print(f"  [{'OK' if ok_callback_fmt else 'XX'}] callback_data round-trips (make↔parse)")

    ok_offline = (len(_spy_calls) == 0)
    failures += [] if ok_offline else [f"network chokepoint was called: {_spy_calls}"]
    print(f"  [{'OK' if ok_offline else 'XX'}] NO real HTTP calls "
          f"(_api spy invoked {len(_spy_calls)} times)")

    print("\n" + "=" * 74)
    if failures:
        print("RESULT: FAIL ❌")
        for f in failures:
            print(f"  - {f}")
        print("=" * 74)
        return 1
    print("RESULT: PASS ✅ — card payload correct, updates parse right, fully offline.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
