#!/usr/bin/env python3
"""Alfred · dry run — LinkedIn Easy Apply adapter (fully offline).

Exercises the pure normalizer with cards shaped the way the subagent scrapes them:
the several id forms LinkedIn exposes, search-vs-posting URLs, the Easy Apply badge,
and the role filter. Touches no network and no real history store.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from sources import linkedin_easy_apply as lea  # noqa: E402
from sources import REGISTRY  # noqa: E402

ok = True


def check(label, got, want):
    global ok
    good = got == want
    ok = ok and good
    print(f"  [{'OK' if good else 'FAIL'}] {label}"
          + ("" if good else f"\n        got={got!r}\n        want={want!r}"))


print("\n" + "=" * 74)
print("Alfred dry run — linkedin_easy_apply (pure normalizer, offline)")
print("=" * 74 + "\n")

print("Contract")
check("registered in REGISTRY", REGISTRY.get("linkedin_easy_apply") is lea, True)
check("BROWSER = True (dispatch skips it)", getattr(lea, "BROWSER", False), True)
check("no fetch() — the subagent browses", hasattr(lea, "fetch"), False)

print("\nPosting id — every form LinkedIn exposes")
check("canonical /jobs/view/<id>/",
      lea._job_id_from_url("https://www.linkedin.com/jobs/view/4012345678/"), "4012345678")
check("slug form /jobs/view/<slug>-<id>",
      lea._job_id_from_url("https://www.linkedin.com/jobs/view/ux-designer-at-acme-4012345678"),
      "4012345678")
check("split-pane ?currentJobId=",
      lea._job_id_from_url("https://www.linkedin.com/jobs/search/?keywords=ux&currentJobId=4012345678"),
      "4012345678")
check("bare search → no id", lea._job_id_from_url("https://www.linkedin.com/jobs/search/?keywords=ux"), "")

print("\nURL hygiene — never store a search URL")
check("posting URL kept",
      lea.clean_job_url("https://www.linkedin.com/jobs/view/4012345678/"),
      "https://www.linkedin.com/jobs/view/4012345678/")
check("search URL naming a job → rebuilt as the posting",
      lea.clean_job_url("https://www.linkedin.com/jobs/search/?keywords=ux&currentJobId=4012345678"),
      "https://www.linkedin.com/jobs/view/4012345678/")
check("bare search URL → null (never stored)",
      lea.clean_job_url("https://www.linkedin.com/jobs/search/?keywords=ux"), None)

print("\nEasy Apply flag — only when actually observed")
check("explicit boolean honoured", lea.is_easy_apply({"easy_apply": True}), True)
check("badge text detected", lea.is_easy_apply({"apply_label": "Easy Apply"}), True)
check("portal posting → False", lea.is_easy_apply({"apply_label": "Apply on company website"}), False)
check("nothing scraped → False (never guessed)", lea.is_easy_apply({}), False)

print("\nnormalize()")
job = lea.normalize({
    "url": "https://www.linkedin.com/jobs/view/4012345678/",
    "title": "Senior Product Designer",
    "company": "  Acme Corp ",
    "location": "Pune, India",
    "workplace_type": "Hybrid",
    "posted": "2 days ago",
    "snippet": "<p>Own the <b>design system</b> end to end.</p>",
    "apply_label": "Easy Apply",
})
check("stable job_id", job["job_id"], "linkedin_easy_apply:4012345678")
check("company trimmed", job["company"], "Acme Corp")
check("workplace folded into location", job["location"], "Pune, India (Hybrid)")
check("relative age → posted_date None (never fabricated)", job["posted_date"], None)
check("html stripped from snippet", job["description_snippet"], "Own the design system end to end.")
check("easy_apply true", job["easy_apply"], True)

blank = lea.normalize({"url": "https://www.linkedin.com/jobs/view/4012345679/", "title": "UX Designer"})
check("missing company → null (never invented)", blank["company"], None)

print("\nnormalize_cards() — role filter + Easy-Apply-only + junk drop")
cards = [
    {"id": "4000000001", "title": "Senior Product Designer", "company": "Acme",
     "url": "https://www.linkedin.com/jobs/view/4000000001/", "easy_apply": True},
    {"id": "4000000002", "title": "UI/UX Designer", "company": "Globex",
     "url": "https://www.linkedin.com/jobs/view/4000000002/", "easy_apply": True},
    {"id": "4000000003", "title": "Backend Engineer", "company": "Initech",
     "url": "https://www.linkedin.com/jobs/view/4000000003/", "easy_apply": True},
    {"id": "4000000004", "title": "Product Designer", "company": "Umbrella",
     "url": "https://www.linkedin.com/jobs/view/4000000004/",
     "apply_label": "Apply on company website"},
    {"title": "Product Designer", "company": "NoId Ltd",
     "url": "https://www.linkedin.com/jobs/search/?keywords=ux", "easy_apply": True},
]
roles = ["UI/UX Designer", "Product Designer"]
got = lea.normalize_cards(cards, roles)
check("kept the 2 Easy Apply role matches",
      [j["job_id"] for j in got],
      ["linkedin_easy_apply:4000000001", "linkedin_easy_apply:4000000002"])
check("off-role dropped", any("Backend" in (j["title"] or "") for j in got), False)
check("portal-only posting dropped", any(j["company"] == "Umbrella" for j in got), False)
check("unidentifiable card dropped", any(j["company"] == "NoId Ltd" for j in got), False)
check("_tags stripped from output", any("_tags" in j for j in got), False)

kept_all = lea.normalize_cards(cards, roles, easy_apply_only=False)
check("easy_apply_only=False keeps the portal posting", len(kept_all), 3)

print("\n" + "=" * 74)
print(f"RESULT: {'PASS ✅' if ok else 'FAIL ❌'} — normalize + id/URL hygiene + Easy Apply flag"
      " + role filter; dispatch defers to the subagent; fully offline.")
print("=" * 74 + "\n")
sys.exit(0 if ok else 1)
