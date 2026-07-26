"""WarmApply · RemoteOK + dispatch DRY-RUN (OFFLINE — asserts zero network).

Part A — RemoteOK normalizer:
    Feed a saved sample of the RemoteOK JSON (metadata element + fake jobs) through
    the REAL normalizer + role filter. Print the canonical jobs and assert the shape.

Part B — dispatch (search all sources, first-in-order wins a duplicate):
    Two FAKE sources share one duplicate job; the order also includes a
    not-implemented source and an erroring source. Prove every source is queried,
    the run survives the bad ones, and the FIRST source in order wins the dup.

Safety: remoteok.requests is replaced with a tripwire that RAISES on any HTTP call;
we assert it was never touched. No network, no real sources.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import source_dispatch  # noqa: E402
from sources import remoteok  # noqa: E402


# ---------------------------------------------------------------------------
# Network tripwire: any HTTP via remoteok.requests raises.
# ---------------------------------------------------------------------------

class _Tripwire:
    def __init__(self):
        self.calls = []

    def get(self, *args, **kwargs):
        self.calls.append(args)
        raise AssertionError("network call attempted — dry-run must be offline!")


_tripwire = _Tripwire()
remoteok.requests = _tripwire  # type: ignore


# ---------------------------------------------------------------------------
# Saved sample of the RemoteOK feed (element 0 = legal/metadata; rest = fake jobs)
# ---------------------------------------------------------------------------

SAMPLE_FEED = [
    {"legal": "RemoteOK API — sample metadata element (skipped)"},
    {
        "id": 111, "position": "Senior Product Designer", "company": "Acme",
        "location": "Worldwide", "tags": ["design", "figma", "ux"],
        "url": "https://remoteok.com/remote-jobs/111",
        "date": "2026-07-20T09:00:00+00:00",
        "description": "<p>Own the <b>design system</b> &amp; ship polished UI.</p>",
    },
    {
        "id": 222, "position": "UX Designer", "company": "Globex",
        "location": "Remote", "tags": ["ux", "research"],
        "url": "https://remoteok.com/remote-jobs/222",
        "date": "2026-07-22T09:00:00+00:00",
        "description": "Run usability studies and prototype flows.",
    },
    {
        "id": 333, "position": "Backend Engineer", "company": "Initech",
        "location": "Remote", "tags": ["python", "django"],
        "url": "https://remoteok.com/remote-jobs/333",
        "date": "2026-07-23T09:00:00+00:00",
        "description": "Build APIs.",
    },
    {
        "id": 444, "position": "Product Manager", "company": "Umbrella",
        "location": "Remote", "tags": ["product", "roadmap"],
        "url": "https://remoteok.com/remote-jobs/444",
        "date": "2026-07-24T09:00:00+00:00",
        "description": "Own the roadmap.",
    },
]

ROLES = ["Product Designer", "UX Designer", "UI Designer"]

CANONICAL_KEYS = {
    "job_id", "source", "title", "company", "company_domain", "location",
    "url", "posted_date", "easy_apply", "description_snippet", "found_at",
}


# ---------------------------------------------------------------------------
# Fake sources for the dispatch test.
# ---------------------------------------------------------------------------

class FakeSource:
    def __init__(self, jobs, raise_exc=False):
        self._jobs = jobs
        self._raise = raise_exc

    def fetch(self, roles=None, locations=None, timeout=15):
        if self._raise:
            raise RuntimeError("simulated source failure")
        return [dict(j) for j in self._jobs]


def part_a() -> list:
    print("A) RemoteOK normalizer — sample feed → canonical jobs:")
    jobs = remoteok.normalize_feed(SAMPLE_FEED, ROLES)
    print(json.dumps(jobs, indent=2, ensure_ascii=False))
    return jobs


def part_b():
    print("\n" + "=" * 74)
    print("B) dispatch — all sources queried, first-in-order wins the duplicate:")

    # A duplicate job shared by two sources (same company + normalized title,
    # different job_id/source). "alpha" precedes "beta" in the order → alpha wins.
    dup_alpha = {"job_id": "alpha:1", "source": "alpha", "company": "Acme",
                 "title": "Product Designer", "url": "https://a/1"}
    dup_beta = {"job_id": "beta:9", "source": "beta", "company": "acme",
                "title": "product   designer", "url": "https://b/9"}
    alpha_only = {"job_id": "alpha:2", "source": "alpha", "company": "Globex",
                  "title": "UX Designer", "url": "https://a/2"}
    beta_only = {"job_id": "beta:2", "source": "beta", "company": "Initech",
                 "title": "UI Designer", "url": "https://b/2"}

    registry = {
        "alpha": FakeSource([dup_alpha, alpha_only]),
        "beta": FakeSource([dup_beta, beta_only]),
        "boom": FakeSource([], raise_exc=True),      # errors → [] and continues
    }
    # Includes "ghost" (not implemented) and "boom" (errors) between the two real ones.
    order = ["alpha", "ghost", "boom", "beta"]

    tmp_history = os.path.join(tempfile.mkdtemp(prefix="warmapply_disp_"),
                               "history.json")  # empty → nothing pre-seen
    fresh, report = source_dispatch.dispatch(
        order, roles=ROLES, blacklist=[], registry=registry, history_path=tmp_history)

    print("\nPer-source report (every source in order is visited):")
    for r in report:
        extra = r.get("note") or r.get("error") or ""
        print(f"  - {r['source']:<7} {r['status']:<8} count={r['count']}  {extra}")

    print("\nFresh de-duped jobs:")
    print(json.dumps(fresh, indent=2, ensure_ascii=False))
    return fresh, report


def main() -> int:
    print("=" * 74)
    print("WarmApply · RemoteOK + dispatch — DRY RUN (OFFLINE; requests tripwired)")
    print("=" * 74 + "\n")

    jobs = part_a()
    fresh, report = part_b()

    # ---- Assertions --------------------------------------------------------
    print("\n" + "-" * 74)
    print("Assertions:")
    failures = []

    # A1: role filter kept only the 2 design roles (111, 222); dropped 333, 444.
    ok_filter = [j["job_id"] for j in jobs] == ["remoteok:111", "remoteok:222"]
    failures += [] if ok_filter else [f"role filter wrong: {[j['job_id'] for j in jobs]}"]
    print(f"  [{'OK' if ok_filter else 'XX'}] role filter kept design roles only "
          f"({[j['job_id'] for j in jobs]})")

    # A2: canonical shape (exact key set), source + job_id prefix, no internal _tags.
    shape_ok = all(set(j.keys()) == CANONICAL_KEYS for j in jobs)
    prefix_ok = all(j["job_id"].startswith("remoteok:") and j["source"] == "remoteok"
                    for j in jobs)
    no_tags = all("_tags" not in j for j in jobs)
    ok_shape = shape_ok and prefix_ok and no_tags
    failures += [] if ok_shape else ["canonical shape/source/prefix wrong"]
    print(f"  [{'OK' if ok_shape else 'XX'}] canonical shape exact + source=remoteok "
          f"+ no internal keys")

    # A3: HTML stripped in snippet, tags appended.
    snip = jobs[0]["description_snippet"]
    ok_snip = "<" not in snip and "design system" in snip and "tags:" in snip
    failures += [] if ok_snip else [f"snippet not clean: {snip!r}"]
    print(f"  [{'OK' if ok_snip else 'XX'}] snippet HTML-stripped + tags appended")

    # B1: every source in the order appears in the report (all queried).
    reported = [r["source"] for r in report]
    ok_all = reported == ["alpha", "ghost", "boom", "beta"]
    failures += [] if ok_all else [f"not all sources visited: {reported}"]
    print(f"  [{'OK' if ok_all else 'XX'}] all sources visited in order ({reported})")

    # B2: ghost skipped, boom errored, run survived both.
    status = {r["source"]: r["status"] for r in report}
    ok_robust = status.get("ghost") == "skipped" and status.get("boom") == "error"
    failures += [] if ok_robust else [f"robustness wrong: {status}"]
    print(f"  [{'OK' if ok_robust else 'XX'}] not-implemented skipped + erroring source "
          f"survived (ghost={status.get('ghost')}, boom={status.get('boom')})")

    # B3: duplicate resolved to the FIRST source in order (alpha), beta:9 dropped.
    ids = [j["job_id"] for j in fresh]
    dup_survivor = next((j for j in fresh if j["company"].lower() == "acme"), None)
    ok_dup = (dup_survivor is not None and dup_survivor["job_id"] == "alpha:1"
              and "beta:9" not in ids)
    failures += [] if ok_dup else [f"first-in-order did not win dup: ids={ids}"]
    print(f"  [{'OK' if ok_dup else 'XX'}] first-in-order wins dup "
          f"(survivor={dup_survivor['job_id'] if dup_survivor else None}, beta:9 dropped)")

    # B4: both real sources still contributed their unique jobs (all sources run).
    ok_contrib = "alpha:2" in ids and "beta:2" in ids and len(fresh) == 3
    failures += [] if ok_contrib else [f"unique jobs missing: ids={ids}"]
    print(f"  [{'OK' if ok_contrib else 'XX'}] both sources contributed uniques "
          f"(alpha:2 + beta:2 present, {len(fresh)} total)")

    # C: zero network.
    ok_offline = len(_tripwire.calls) == 0
    failures += [] if ok_offline else [f"network touched: {_tripwire.calls}"]
    print(f"  [{'OK' if ok_offline else 'XX'}] NO network (requests.get invoked "
          f"{len(_tripwire.calls)} times)")

    print("\n" + "=" * 74)
    if failures:
        print("RESULT: FAIL ❌")
        for f in failures:
            print(f"  - {f}")
        print("=" * 74)
        return 1
    print("RESULT: PASS ✅ — normalize + role filter correct, all sources run, "
          "first-in-order wins, offline.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
