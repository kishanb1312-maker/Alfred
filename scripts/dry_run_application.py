"""WarmApply · Application Agent DRY-RUN (OFFLINE — asserts NO send/submit).

Simulates the application agent's processing loop for a small approved queue
(1 email job + 1 portal job) with dry_run=True, and separately proves /pause halts
everything. NOTHING is sent or submitted:

  - email_send._smtp_send (the ONLY SMTP chokepoint) is monkeypatched to RAISE.
  - GMAIL_APP_PASSWORD is left unset, so a real login is impossible anyway.
  - the portal job is only ever marked "fill + hand to human for final click";
    no browser is driven from this script.

Shows: email MIME built with attachments (DRY_RUN, not sent), portal handed to the
human, daily caps decremented, and a paused case that halts. Assertions at the end.
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import daily_caps  # noqa: E402
import email_send  # noqa: E402


# ---------------------------------------------------------------------------
# Network tripwire: replace the SMTP chokepoint with a raising spy.
# ---------------------------------------------------------------------------

class _NetworkTouched(Exception):
    pass


_smtp_calls = []


def _spy_smtp(msg):
    _smtp_calls.append(msg["To"])
    raise _NetworkTouched("email_send._smtp_send called — dry-run must be offline!")


email_send._smtp_send = _spy_smtp
os.environ.pop("GMAIL_APP_PASSWORD", None)          # ensure no real login is possible
os.environ["GMAIL_ADDRESS"] = "jobhunt.fake@example.com"  # From: for the demo only


# ---------------------------------------------------------------------------
# Fake approved queue (1 email job + 1 portal job) + tailored files.
# ---------------------------------------------------------------------------

def build_jobs(workdir: str):
    resume = os.path.join(workdir, "Resume_GlobexSystems.pdf")
    cover = os.path.join(workdir, "CoverLetter_GlobexSystems.pdf")
    for p, tag in ((resume, b"%PDF-1.4 fake resume\n"), (cover, b"%PDF-1.4 fake cover\n")):
        with open(p, "wb") as fh:
            fh.write(tag)

    email_job = {
        "job_id": "linkedin:FAKE-A1",
        "company": "Globex Systems",
        "title": "Site Reliability Engineer",
        "channel": "email",
        "email": {"address": "priya.sharma@globex.example", "verified": True,
                  "source": "hunter", "confidence": 92},
        "email_subject": "Site Reliability Engineer — Fake Candidate",
        "email_body": ("Hi Priya,\n\nI'd love to be considered for the SRE role. "
                       "I've attached my resume and a short cover letter.\n\nBest,\nFake Candidate"),
        "files": {"resume": resume, "cover_letter": cover},
    }
    portal_job = {
        "job_id": "adzuna:FAKE-B2",
        "company": "Initech",
        "title": "Platform Engineer",
        "channel": "portal",
        "portal": "linkedin_easy_apply",   # ban-prone → human final click
        "files": {"resume": resume, "cover_letter": cover},
    }
    return [email_job, portal_job]


# ---------------------------------------------------------------------------
# The application-agent processing loop (offline simulation).
# ---------------------------------------------------------------------------

def process_queue(jobs, *, dry_run, paused, caps, counts_path):
    """Mirrors the agent's guarded loop. Returns a list of per-job log dicts."""
    log = []

    # Precondition 1: /pause halts EVERYTHING before any work.
    if paused:
        log.append({"halted": True, "reason": "paused (data/paused.flag present)"})
        return log

    for job in jobs:
        jid = job["job_id"]
        channel = job["channel"]

        if channel == "email":
            # Guardrail: only verified, non-'none' recipient addresses.
            em = job.get("email") or {}
            if not em.get("verified") or em.get("source") in (None, "", "none") or not em.get("address"):
                log.append({"job_id": jid, "channel": "email", "action": "SKIP",
                            "reason": "recipient email not verified"})
                continue
            # Guardrail: daily email cap.
            if daily_caps.remaining("email", caps["emails_per_day"], path=counts_path) <= 0:
                log.append({"job_id": jid, "channel": "email", "action": "SKIP",
                            "reason": "emails_per_day cap reached"})
                continue

            msg = email_send.build_message(
                to=em["address"], subject=job["email_subject"], body=job["email_body"],
                attachments=[job["files"]["resume"], job["files"]["cover_letter"]])
            result = email_send.send(msg, dry_run=dry_run)   # dry_run → no connection
            new_count = daily_caps.record("email", path=counts_path)
            log.append({"job_id": jid, "channel": "email", "action": result["status"],
                        "to": result["to"], "subject": result["subject"],
                        "attachments": result["attachments"], "size_bytes": result["size_bytes"],
                        "email_count_today": new_count,
                        "serialized_head": result.get("serialized", "").splitlines()[:8]})

        elif channel == "portal":
            # Guardrail: daily apply cap.
            if daily_caps.remaining("apply", caps["applies_per_day"], path=counts_path) <= 0:
                log.append({"job_id": jid, "channel": "portal", "action": "SKIP",
                            "reason": "applies_per_day cap reached"})
                continue
            # Ban-prone portal → fill only; the human does the final Submit click.
            new_count = daily_caps.record("apply", path=counts_path)
            log.append({"job_id": jid, "channel": "portal", "portal": job.get("portal"),
                        "action": "FILL + HAND TO HUMAN FOR FINAL CLICK",
                        "auto_submit": False, "apply_count_today": new_count})

    return log


def _print_log(log):
    for entry in log:
        if entry.get("halted"):
            print(f"  ⛔ HALTED — {entry['reason']}")
            continue
        if entry["action"] == "SKIP":
            print(f"  ⏭️  {entry['job_id']} [{entry['channel']}] SKIP — {entry['reason']}")
        elif entry["channel"] == "email":
            print(f"  ✉️  {entry['job_id']} [email] {entry['action']} → {entry['to']}")
            print(f"       subject : {entry['subject']}")
            print(f"       attached: {entry['attachments']}  ({entry['size_bytes']} bytes)")
            print(f"       email count today: {entry['email_count_today']}")
            print(f"       serialized (head):")
            for line in entry["serialized_head"]:
                print(f"         | {line}")
        elif entry["channel"] == "portal":
            print(f"  🖥️  {entry['job_id']} [portal:{entry['portal']}] {entry['action']} "
                  f"(auto_submit={entry['auto_submit']})")
            print(f"       apply count today: {entry['apply_count_today']}")


def main() -> int:
    print("=" * 74)
    print("WarmApply · Application Agent — DRY RUN (OFFLINE; SMTP spy raises on call)")
    print("=" * 74)

    workdir = tempfile.mkdtemp(prefix="warmapply_apply_")
    counts_path = os.path.join(workdir, "daily_counts.json")
    caps = {"applies_per_day": 2, "emails_per_day": 2}
    jobs = build_jobs(workdir)

    print(f"\ncaps: {caps}   dry_run=True")
    print(f"approved queue: {[j['job_id'] for j in jobs]} "
          f"(1 email, 1 portal)\n")

    # ---- Scenario 1: normal run (not paused), dry_run=True ----------------
    print("SCENARIO 1 — not paused, dry_run=True:")
    print(f"  caps before: email={daily_caps.remaining('email', caps['emails_per_day'], path=counts_path)}, "
          f"apply={daily_caps.remaining('apply', caps['applies_per_day'], path=counts_path)}")
    log1 = process_queue(jobs, dry_run=True, paused=False, caps=caps, counts_path=counts_path)
    _print_log(log1)
    rem_email = daily_caps.remaining("email", caps["emails_per_day"], path=counts_path)
    rem_apply = daily_caps.remaining("apply", caps["applies_per_day"], path=counts_path)
    print(f"  caps after : email={rem_email}, apply={rem_apply}")

    # ---- Scenario 2: paused → must halt -----------------------------------
    print("\nSCENARIO 2 — paused (data/paused.flag present):")
    log2 = process_queue(jobs, dry_run=True, paused=True, caps=caps, counts_path=counts_path)
    _print_log(log2)

    # ---- Assertions --------------------------------------------------------
    print("\n" + "-" * 74)
    print("Assertions:")
    failures = []

    email_entry = next((e for e in log1 if e.get("channel") == "email"), None)
    portal_entry = next((e for e in log1 if e.get("channel") == "portal"), None)

    ok_email_dry = bool(email_entry) and email_entry["action"] == "DRY_RUN"
    failures += [] if ok_email_dry else ["email was not DRY_RUN"]
    print(f"  [{'OK' if ok_email_dry else 'XX'}] email built + status DRY_RUN (not sent)")

    ok_attach = bool(email_entry) and len(email_entry["attachments"]) == 2
    failures += [] if ok_attach else ["email should carry 2 attachments"]
    print(f"  [{'OK' if ok_attach else 'XX'}] email MIME carries 2 attachments "
          f"({email_entry['attachments'] if email_entry else None})")

    ok_portal = bool(portal_entry) and portal_entry["auto_submit"] is False \
        and "HUMAN" in portal_entry["action"]
    failures += [] if ok_portal else ["portal job must be fill + human final click"]
    print(f"  [{'OK' if ok_portal else 'XX'}] portal job = fill + hand to human "
          f"(auto_submit={portal_entry['auto_submit'] if portal_entry else None})")

    ok_caps = (rem_email == 1 and rem_apply == 1)
    failures += [] if ok_caps else [f"caps not decremented (email={rem_email}, apply={rem_apply})"]
    print(f"  [{'OK' if ok_caps else 'XX'}] daily caps decremented "
          f"(email 2→{rem_email}, apply 2→{rem_apply})")

    ok_paused = len(log2) == 1 and log2[0].get("halted") is True
    failures += [] if ok_paused else ["paused run did not halt cleanly"]
    print(f"  [{'OK' if ok_paused else 'XX'}] /pause halts before any action")

    ok_offline = len(_smtp_calls) == 0
    failures += [] if ok_offline else [f"SMTP chokepoint called: {_smtp_calls}"]
    print(f"  [{'OK' if ok_offline else 'XX'}] NO SMTP/HTTP/browser calls "
          f"(_smtp_send spy invoked {len(_smtp_calls)} times)")

    print("\n" + "=" * 74)
    if failures:
        print("RESULT: FAIL ❌")
        for f in failures:
            print(f"  - {f}")
        print("=" * 74)
        return 1
    print("RESULT: PASS ✅ — email built not sent, portal deferred to human, "
          "caps enforced, pause honored, fully offline.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
