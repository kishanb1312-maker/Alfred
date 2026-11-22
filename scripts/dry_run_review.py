"""Alfred · manual review gate DRY-RUN (OFFLINE — no SMTP).

Proves the approval step that replaced Telegram:

  1. add_for_review + pending_review: best score first; decided jobs leave the list,
  2. approve: portal approved + queued; the email is NOT cleared unless asked,
  3. approve --email: clears the email in the same explicit step,
  4. skip: never queued, its email auto-cancelled; first answer wins,
  5. unknown job / approve-after-skip are refused,
  6. stage_email_draft: body from email_message.txt, CV PDF attached (no cover
     letter), never overwrites an edited draft; no address -> no draft,
  7. apply_edit: subject + body replaced, empty edit refused,
  8. email_gate.perform_send: refuses uncleared, sends cleared under dry_run only
     once, refuses while /pause is set — SMTP is a tripwire that must never fire,
  9. the CLI (`alfred review`, `approve`, `skip`) prints and records the same.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TMP = tempfile.mkdtemp(prefix="alfred_review_")
os.environ["ALFRED_HOME"] = TMP
for d in ("data", "config", "output/Acme_PD", "output/Zen_UX"):
    os.makedirs(os.path.join(TMP, d), exist_ok=True)
with open(os.path.join(TMP, "config", "search.yaml"), "w", encoding="utf-8") as fh:
    fh.write("dry_run: true\ncaps:\n  emails_per_day: 5\n")

import email_gate  # noqa: E402
import email_send  # noqa: E402
import review_store as rs  # noqa: E402

_smtp = []
email_send._smtp_send = lambda msg: (_smtp.append(msg["To"]),
                                     (_ for _ in ()).throw(AssertionError("SMTP called")))


def job(jid, company, score, email=None):
    out = os.path.join(TMP, "output", f"{company}_{'PD' if company == 'Acme' else 'UX'}")
    pdf = os.path.join(out, f"cv-{company.lower()}.pdf")
    with open(pdf, "wb") as fh:
        fh.write(b"%PDF-1.4 fake\n")
    with open(os.path.join(out, "email_message.txt"), "w", encoding="utf-8") as fh:
        fh.write(f"Subject: Product Designer — {company}\n\nHi, I saw the role… [FAKE]\n")
    return {"job_id": jid, "company": company, "title": "Product Designer", "score": score,
            "report": os.path.join(TMP, "reports", f"{jid}.md"), "cv_pdf": pdf,
            "output_dir": out, "contact_email": email, "fact_check": "pass"}


def main() -> int:
    print("=" * 70)
    print("Alfred · manual review gate — DRY RUN (offline)")
    print("=" * 70)
    failures = []

    def check(ok, label):
        failures.extend([] if ok else [label])
        print(f"  [{'OK' if ok else 'XX'}] {label}")

    a = job("gh:acme:1", "Acme", "4.6/5", "priya@acme.example")
    z = job("lever:zen:2", "Zen", "4.1/5", "hr@zen.example")
    n = job("ashby:none:3", "Acme", "4.3/5", None)
    for j in (z, a, n):
        rs.add_for_review(j)
    order = [j["job_id"] for j in rs.pending_review()]
    check(order == ["gh:acme:1", "ashby:none:3", "lever:zen:2"], "pending_review(): best score first")

    d1 = rs.stage_email_draft(a)
    check(d1 and d1["to"] == "priya@acme.example" and d1["subject"] == "Product Designer — Acme"
          and [os.path.basename(p) for p in rs.load_draft(a["job_id"])["attachments"]] == ["cv-acme.pdf"],
          "stage_email_draft(): subject/body from file, only the CV attached")
    check(rs.stage_email_draft(n) is None, "stage_email_draft(): no address → no draft")
    rs.stage_email_draft(z)
    rs.apply_edit(z["job_id"], "Subject: Edited subject\n\nMy own words.")
    again = rs.stage_email_draft(z)
    check(again["subject"] == "Edited subject" and again["body"] == "My own words.",
          "apply_edit() replaces subject+body; re-staging never overwrites the edit")
    check(rs.apply_edit(z["job_id"], "   ") is None, "empty edit refused")

    r = rs.approve(a["job_id"])
    check(r["ok"] and rs.is_approved(a["job_id"]) and a["job_id"] in rs.approved_queue()
          and rs.email_decision(a["job_id"]) is None,
          "approve(): portal approved + queued; email NOT cleared")
    res_unclear = email_gate.perform_send(a["job_id"])
    check(res_unclear["sent"] is False and "not cleared" in res_unclear["reason"],
          "email_gate refuses an approved job whose email was not cleared")

    r2 = rs.approve(z["job_id"], with_email=True)
    check(r2["email"] == "cleared" and rs.email_decision(z["job_id"]) == "cleared",
          "approve(--email): clears the email in the same explicit step")
    rs.set_pause(True)
    paused = email_gate.perform_send(z["job_id"])
    rs.set_pause(False)
    check(paused["sent"] is False and "/pause" in paused["reason"], "email_gate refuses while /pause is set")
    sent = email_gate.perform_send(z["job_id"])
    twice = email_gate.perform_send(z["job_id"])
    check(sent["status"] == "DRY_RUN" and twice["sent"] is False and "already" in twice["reason"],
          "email_gate under dry_run: DRY_RUN once, then refuses as already done")

    s = rs.skip(n["job_id"])
    check(s["ok"] and rs.job_decision(n["job_id"]) == "skipped" and n["job_id"] not in rs.approved_queue(),
          "skip(): recorded, never queued")
    check(rs.approve(n["job_id"])["ok"] is False and rs.approve("nope")["ok"] is False,
          "approve-after-skip and unknown job are refused")
    check(rs.record_job_decision(a["job_id"], "skipped") is False, "first answer wins")
    check(rs.pending_review() == [], "decided jobs leave the review list")

    # location priority: remote abroad first, then India, then on-site abroad, then unknown
    cases = {
        "Remote — Worldwide": "remote_abroad", "Remote (US)": "remote_abroad",
        "Bengaluru": "india", "Remote, India": "india", "Pune, Maharashtra": "india",
        "Berlin, Germany": "onsite_abroad", "": "unknown",
    }
    ok_b = all(rs.location_bucket({"location": loc}) == want for loc, want in cases.items())
    ok_tag = (rs.location_bucket({"location": "London", "workplace": "remote"}) == "remote_abroad"
              and rs.location_bucket({"location": "Somewhere", "region": "india"}) == "india")
    check(ok_b and ok_tag, "location_bucket(): remote abroad / India / on-site abroad / unknown")
    for jid, loc, sc in (("p:1", "Berlin, Germany", "4.9/5"), ("p:2", "Bengaluru", "4.8/5"),
                         ("p:3", "Remote — Worldwide", "4.1/5"), ("p:4", "Remote (EMEA)", "4.6/5"),
                         ("p:5", "", "5.0/5")):
        rs.add_for_review({"job_id": jid, "company": "X", "title": "Designer", "location": loc, "score": sc})
    ranked = [j["job_id"] for j in rs.pending_review(["remote_abroad", "india", "onsite_abroad"])]
    check(ranked == ["p:4", "p:3", "p:2", "p:1", "p:5"],
          f"pending_review(): remote abroad first (by score), then India, then on-site abroad → {ranked}")
    for jid in ("p:1", "p:2", "p:3", "p:4", "p:5"):
        rs.skip(jid)

    buf = io.StringIO()
    with redirect_stdout(buf):
        rs._cli(["list"])
        rs._cli(["queue"])
    out = buf.getvalue()
    check("0 job(s) waiting" in out and "gh:acme:1" in out and "lever:zen:2" in out,
          "CLI: list + queue print the same state")

    check(rs.remove_from_queue(a["job_id"]) and a["job_id"] not in rs.approved_queue()
          and rs.is_approved(a["job_id"]), "remove_from_queue(): drained but still recorded as approved")
    check(_smtp == [], f"SMTP never called ({len(_smtp)}×)")

    print("\n" + "=" * 70)
    if failures:
        print("RESULT: FAIL ❌")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("RESULT: PASS ✅ — manual approve/skip, separate email clear, drafts, gate; offline.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
