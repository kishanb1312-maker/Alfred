"""WarmApply · Application Agent DRY-RUN (OFFLINE — dual-channel + bounce throttle).

Simulates the application agent's DUAL-CHANNEL loop: every approved job gets BOTH a
portal application AND (if an email was found) a cold email — including single
best-guess addresses (the user accepted the bounce risk). NOTHING is sent/submitted:

  - email_send._smtp_send (the ONLY SMTP chokepoint) is monkeypatched to RAISE.
  - bounce_check._fetch_bounce_messages (the ONLY IMAP call) is never invoked —
    bounce messages are injected.
  - GMAIL_APP_PASSWORD is unset; the portal is only ever "fill + hand to human".

Scenarios:
  1. normal, dry_run=True  → both channels act; guessed email still queued; caps drop.
  2. global /pause         → halts everything.
  3. email-channel paused  → portal still runs, cold emails skipped (EMAIL_PAUSED).
  4. bounce auto-throttle  → a simulated high-bounce batch trips the throttle, sets
                             data/email_paused.flag, and returns a Telegram warning.
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bounce_check  # noqa: E402
import daily_caps  # noqa: E402
import email_send  # noqa: E402


# ---------------------------------------------------------------------------
# Network tripwires: SMTP + IMAP must never be called.
# ---------------------------------------------------------------------------

_smtp_calls = []


def _spy_smtp(msg):
    _smtp_calls.append(msg["To"])
    raise AssertionError("email_send._smtp_send called — dry-run must be offline!")


def _spy_imap(*a, **k):
    raise AssertionError("bounce_check._fetch_bounce_messages called — must be offline!")


email_send._smtp_send = _spy_smtp
bounce_check._fetch_bounce_messages = _spy_imap
os.environ.pop("GMAIL_APP_PASSWORD", None)               # no real login possible
os.environ["GMAIL_ADDRESS"] = "jobhunt.fake@example.com"  # From: for the demo only


# ---------------------------------------------------------------------------
# Fake approved queue — dual-channel jobs (company-research output shape).
# ---------------------------------------------------------------------------

def build_jobs(workdir: str):
    resume = os.path.join(workdir, "Resume.pdf")
    cover = os.path.join(workdir, "CoverLetter.pdf")
    for p, tag in ((resume, b"%PDF-1.4 fake resume\n"), (cover, b"%PDF-1.4 fake cover\n")):
        with open(p, "wb") as fh:
            fh.write(tag)
    files = {"resume": resume, "cover_letter": cover}

    return [
        {   # A: verified finder email → portal + email
            "job_id": "linkedin:FAKE-A1", "company": "Globex", "title": "SRE",
            "apply_portal": True, "portal": "linkedin_easy_apply",
            "cold_email": True, "contact_email": "priya.sharma@globex.example",
            "email_source": "hunter", "verified_mailbox": True,
            "email_subject": "SRE — Fake Candidate",
            "email_body": "Hi Priya,\n\nI'd love to be considered.\n\nBest,\nFake Candidate",
            "files": files,
        },
        {   # B: GUESSED email (pattern) → portal + email (still sends, per user choice)
            "job_id": "remoteok:FAKE-C3", "company": "Zephyr Labs", "title": "Platform",
            "apply_portal": True, "portal": "greenhouse",
            "cold_email": True, "contact_email": "alex.kim@zephyr.example",
            "email_source": "pattern", "verified_mailbox": False,
            "email_subject": "Platform Engineer — Fake Candidate",
            "email_body": "Hi Alex,\n\nI'd love to be considered.\n\nBest,\nFake Candidate",
            "files": files,
        },
        {   # C: no email found → portal ONLY
            "job_id": "indeed:FAKE-D4", "company": "Initech", "title": "DevOps",
            "apply_portal": True, "portal": "indeed",
            "cold_email": False, "contact_email": None,
            "email_source": "none", "verified_mailbox": False,
            "files": files,
        },
    ]


# ---------------------------------------------------------------------------
# Dual-channel processing loop (offline simulation of the application agent).
# ---------------------------------------------------------------------------

def process_queue(jobs, *, dry_run, paused, caps, counts_path, email_flag_path):
    """For each job do BOTH portal + email (guarded). Returns (log, sent_recipients)."""
    log = []
    sent_recipients = []

    if paused:  # global /pause halts EVERYTHING
        return [{"halted": True, "reason": "paused (data/paused.flag present)"}], []

    email_paused = bounce_check.is_email_paused(path=email_flag_path)

    for job in jobs:
        jid = job["job_id"]
        actions = {"job_id": jid, "company": job["company"], "portal": None, "email": None}

        # --- (a) Portal application (always, if apply_portal) ---
        if job.get("apply_portal", True):
            if daily_caps.remaining("apply", caps["applies_per_day"], path=counts_path) <= 0:
                actions["portal"] = {"action": "SKIP", "reason": "applies_per_day cap reached"}
            else:
                daily_caps.record("apply", path=counts_path)
                actions["portal"] = {"action": "FILL + HUMAN FINAL CLICK",
                                     "portal": job.get("portal"), "auto_submit": False}

        # --- (b) Cold email (if cold_email and an address exists) ---
        if job.get("cold_email") and job.get("contact_email") and job.get("email_source") != "none":
            if email_paused:
                actions["email"] = {"action": "SKIP", "reason": "email channel auto-paused (throttle)"}
            elif daily_caps.remaining("email", caps["emails_per_day"], path=counts_path) <= 0:
                actions["email"] = {"action": "SKIP", "reason": "emails_per_day cap reached"}
            else:
                msg = email_send.build_message(
                    to=job["contact_email"], subject=job["email_subject"],
                    body=job["email_body"],
                    attachments=[job["files"]["resume"], job["files"]["cover_letter"]])
                result = email_send.send(msg, dry_run=dry_run)
                daily_caps.record("email", path=counts_path)
                sent_recipients.append(job["contact_email"])
                actions["email"] = {"action": result["status"], "to": result["to"],
                                    "guessed": job["email_source"] == "pattern",
                                    "attachments": result.get("attachments")}
        elif not job.get("cold_email"):
            actions["email"] = {"action": "NONE", "reason": "no email found (portal-only)"}

        log.append(actions)
    return log, sent_recipients


def _print_log(log):
    for e in log:
        if e.get("halted"):
            print(f"  ⛔ HALTED — {e['reason']}")
            continue
        print(f"  • {e['job_id']} ({e['company']})")
        p = e["portal"]
        if p:
            if p["action"] == "SKIP":
                print(f"      portal: SKIP — {p['reason']}")
            else:
                print(f"      portal: {p['action']} [{p['portal']}] auto_submit={p['auto_submit']}")
        m = e["email"]
        if m:
            if m["action"] in ("SKIP", "NONE"):
                print(f"      email : {m['action']} — {m['reason']}")
            else:
                flag = " ⚠️guess" if m.get("guessed") else ""
                print(f"      email : {m['action']} → {m['to']}{flag}")


def main() -> int:
    print("=" * 74)
    print("WarmApply · Application Agent — DRY RUN (OFFLINE; dual-channel + throttle)")
    print("=" * 74)

    workdir = tempfile.mkdtemp(prefix="warmapply_apply_")
    counts_path = os.path.join(workdir, "daily_counts.json")
    email_flag = os.path.join(workdir, "email_paused.flag")
    caps = {"applies_per_day": 5, "emails_per_day": 5}

    print(f"\ncaps: {caps}   dry_run=True")
    print("approved queue: A(verified email), B(GUESSED email), C(no email) — all dual-channel\n")

    # ---- Scenario 1: normal, dry_run=True ---------------------------------
    print("SCENARIO 1 — not paused, dry_run=True (both channels act):")
    log1, sent1 = process_queue(build_jobs(workdir), dry_run=True, paused=False,
                                caps=caps, counts_path=counts_path, email_flag_path=email_flag)
    _print_log(log1)
    rem_apply = daily_caps.remaining("apply", caps["applies_per_day"], path=counts_path)
    rem_email = daily_caps.remaining("email", caps["emails_per_day"], path=counts_path)
    print(f"  caps after: apply={rem_apply} (5→{rem_apply}), email={rem_email} (5→{rem_email})")

    # ---- Scenario 2: global pause -----------------------------------------
    print("\nSCENARIO 2 — global /pause (data/paused.flag):")
    log2, _ = process_queue(build_jobs(workdir), dry_run=True, paused=True,
                            caps=caps, counts_path=counts_path, email_flag_path=email_flag)
    _print_log(log2)

    # ---- Scenario 3: email channel throttled (portal still runs) ----------
    print("\nSCENARIO 3 — email channel paused (data/email_paused.flag) — portal still runs:")
    bounce_check.set_email_pause(True, path=email_flag)
    counts3 = os.path.join(workdir, "counts3.json")
    log3, sent3 = process_queue(build_jobs(workdir), dry_run=True, paused=False,
                                caps=caps, counts_path=counts3, email_flag_path=email_flag)
    _print_log(log3)
    bounce_check.set_email_pause(False, path=email_flag)

    # ---- Scenario 4: bounce auto-throttle on a high-bounce batch ----------
    print("\nSCENARIO 4 — bounce auto-throttle (simulated high-bounce batch):")
    sent_batch = ["a@x.example", "b@y.example", "c@z.example"]
    fake_bounces = [
        {"from": "mailer-daemon@googlemail.com", "subject": "Delivery Status Notification (Failure)",
         "body": "failed: a@x.example"},
        {"from": "Mail Delivery Subsystem <mailer-daemon@googlemail.com>",
         "subject": "Undeliverable", "body": "b@y.example not found"},
        {"from": "postmaster@z.example", "subject": "Returned mail", "body": "c@z.example rejected"},
    ]
    report = bounce_check.apply_throttle(sent_batch, fake_bounces, path=email_flag)
    print(f"  sent={len(sent_batch)}  bounced={report['bounced']}")
    print(f"  throttle: tripped={report['throttle']['tripped']} "
          f"rate={report['throttle']['bounce_rate']} ({report['throttle']['reason']})")
    print(f"  email paused now: {bounce_check.is_email_paused(path=email_flag)}")
    if report["warning"]:
        print("  Telegram warning →")
        for line in report["warning"].splitlines():
            print(f"      {line}")
    bounce_check.set_email_pause(False, path=email_flag)  # clean up

    # ---- Assertions --------------------------------------------------------
    print("\n" + "-" * 74)
    print("Assertions:")
    failures = []
    by_id1 = {e["job_id"]: e for e in log1}

    # 1: both channels acted for A and B; C is portal-only.
    a, b, c = by_id1["linkedin:FAKE-A1"], by_id1["remoteok:FAKE-C3"], by_id1["indeed:FAKE-D4"]
    ok_dual = (a["portal"]["action"].startswith("FILL") and a["email"]["action"] == "DRY_RUN"
               and b["portal"]["action"].startswith("FILL") and b["email"]["action"] == "DRY_RUN"
               and c["portal"]["action"].startswith("FILL") and c["email"]["action"] == "NONE")
    failures += [] if ok_dual else ["dual-channel actions wrong"]
    print(f"  [{'OK' if ok_dual else 'XX'}] A+B do BOTH (portal+email DRY_RUN); C portal-only")

    # 2: the GUESSED email (B) is still sent (per the user's choice), flagged.
    ok_guess = b["email"]["action"] == "DRY_RUN" and b["email"]["guessed"] is True
    failures += [] if ok_guess else ["guessed email not queued/flagged"]
    print(f"  [{'OK' if ok_guess else 'XX'}] guessed email still queued + flagged ⚠️ (B)")

    # 3: caps decremented for BOTH channels (3 portal, 2 email).
    ok_caps = rem_apply == 2 and rem_email == 3   # 5-3 apply, 5-2 email
    failures += [] if ok_caps else [f"caps wrong (apply={rem_apply}, email={rem_email})"]
    print(f"  [{'OK' if ok_caps else 'XX'}] caps: 3 portal applies + 2 emails recorded "
          f"(apply→{rem_apply}, email→{rem_email})")

    # 4: global pause halts everything.
    ok_pause = len(log2) == 1 and log2[0].get("halted")
    failures += [] if ok_pause else ["global pause did not halt"]
    print(f"  [{'OK' if ok_pause else 'XX'}] global /pause halts everything")

    # 5: email-channel pause skips emails but portal still runs.
    a3 = {e["job_id"]: e for e in log3}["linkedin:FAKE-A1"]
    ok_epause = a3["portal"]["action"].startswith("FILL") and a3["email"]["action"] == "SKIP" \
        and len(sent3) == 0
    failures += [] if ok_epause else ["email-channel pause behaviour wrong"]
    print(f"  [{'OK' if ok_epause else 'XX'}] email-paused: portal runs, cold emails skipped")

    # 6: bounce throttle trips on the high-bounce batch and sets the flag.
    ok_throttle = report["throttle"]["tripped"] and report["paused_set"] and report["warning"]
    failures += [] if ok_throttle else ["bounce throttle did not trip"]
    print(f"  [{'OK' if ok_throttle else 'XX'}] bounce throttle tripped + warned "
          f"({len(report['bounced'])}/3 bounced)")

    # 7: zero network (SMTP + IMAP spies never fired).
    ok_offline = len(_smtp_calls) == 0
    failures += [] if ok_offline else [f"SMTP called: {_smtp_calls}"]
    print(f"  [{'OK' if ok_offline else 'XX'}] NO network (SMTP invoked {len(_smtp_calls)}×, "
          f"IMAP 0×)")

    print("\n" + "=" * 74)
    if failures:
        print("RESULT: FAIL ❌")
        for f in failures:
            print(f"  - {f}")
        print("=" * 74)
        return 1
    print("RESULT: PASS ✅ — dual-channel both actions, guesses sent, caps + pauses + "
          "bounce throttle enforced, fully offline.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
