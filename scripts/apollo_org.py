"""Alfred - Apollo organization enrichment (company facts only).

NOTE: this Apollo key is on a Free plan. `mixed_people/search` and
`people/match` return HTTP 403 API_INACCESSIBLE, so Apollo CANNOT be used for
email discovery in this deployment. Only `organizations/enrich` works.

Usage:  ./.venv/bin/python scripts/apollo_org.py <domain> [<domain> ...]
Prints one JSON object per domain with the grounded fields we use.
"""
from __future__ import annotations
import json, os, sys, urllib.request, urllib.parse, pathlib

def _load_env() -> None:
    env = pathlib.Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

FIELDS = ["name","website_url","estimated_num_employees","industry","keywords",
          "short_description","founded_year","total_funding_printed",
          "latest_funding_stage","city","state","country","linkedin_url",
          "technology_names","annual_revenue_printed"]

def enrich(domain: str) -> dict:
    _load_env()
    key = os.environ.get("APOLLO_API_KEY", "")
    if not key:
        return {"domain": domain, "error": "APOLLO_API_KEY missing"}
    url = "https://api.apollo.io/api/v1/organizations/enrich?" + urllib.parse.urlencode({"domain": domain})
    req = urllib.request.Request(url, data=b"", method="POST",
                                 headers={"Content-Type": "application/json", "x-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
    except Exception as e:
        return {"domain": domain, "error": f"{type(e).__name__}: {e}"}
    org = data.get("organization")
    if not org:
        return {"domain": domain, "found": False}
    out = {"domain": domain, "found": True}
    for f in FIELDS:
        v = org.get(f)
        if isinstance(v, list):
            v = v[:15]
        out[f] = v
    return out

if __name__ == "__main__":
    for d in sys.argv[1:]:
        print(json.dumps(enrich(d), ensure_ascii=False))
