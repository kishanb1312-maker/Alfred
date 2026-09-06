#!/usr/bin/env python3
"""Alfred · notion_backfill — push the rows in data/notion_backfill.json into Notion.

Exists because stage 4 was skipped: the tracker had no Notion credential, so no row
was ever created for the jobs this run researched and tailored. Every row's property
payload was already built (via notion_schema.row_properties) and saved; this script
only talks to the API.

Reads NOTION_API_KEY + NOTION_DATABASE_ID from .env. Stdlib only.

    python scripts/notion_backfill.py --check    # auth + target + schema diff, no writes
    python scripts/notion_backfill.py --fix-schema
    python scripts/notion_backfill.py --push     # create the pages (skips existing Job IDs)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKFILL = os.path.join(ROOT, "data/notion_backfill.json")
API = "https://api.notion.com/v1"
VERSION = "2022-06-28"


def _env(key: str) -> str:
    path = os.path.join(ROOT, ".env")
    try:
        for line in open(path):
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


def _call(method: str, path: str, body=None):
    key = _env("NOTION_API_KEY")
    if not key:
        raise SystemExit(
            "NOTION_API_KEY is empty.\n"
            "  Set it (hidden prompt, never echoed):\n"
            "    ./.venv/bin/python scripts/alfred_cli.py set-secret NOTION_API_KEY"
        )
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        API + path, data=data, method=method,
        headers={"Authorization": f"Bearer {key}", "Notion-Version": VERSION,
                 "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:400]
        raise SystemExit(f"Notion API {e.code} on {method} {path}\n  {detail}")


def _load():
    with open(BACKFILL) as f:
        return json.load(f)


def _db_id() -> str:
    dbid = _env("NOTION_DATABASE_ID")
    if not dbid:
        raise SystemExit("NOTION_DATABASE_ID is empty in .env")
    return dbid


def check() -> int:
    me = _call("GET", "/users/me")
    print(f"auth OK  ->  {me.get('name') or me.get('id')} ({me.get('type')})")
    db = _call("GET", f"/databases/{_db_id()}")
    title = "".join(t.get("plain_text", "") for t in db.get("title", []))
    print(f"target   ->  {title or '(untitled)'}  [{db['id']}]")

    have = set(db.get("properties", {}))
    want = _load()["database_schema"]
    missing = [p for p in want if p not in have]
    print(f"schema   ->  {len(have)} existing properties, {len(missing)} missing")
    for p in missing:
        print(f"   missing: {p}  ({list(want[p])[0]})")
    if missing:
        print("\nRun with --fix-schema to add them, then --push.")
    else:
        print("\nSchema is ready. Run with --push.")
    return 0


def fix_schema() -> int:
    db = _call("GET", f"/databases/{_db_id()}")
    have = set(db.get("properties", {}))
    want = _load()["database_schema"]
    missing = {p: v for p, v in want.items() if p not in have}
    if not missing:
        print("nothing to add — schema already complete")
        return 0
    _call("PATCH", f"/databases/{_db_id()}", {"properties": missing})
    print(f"added {len(missing)} properties: {', '.join(missing)}")
    return 0


def _existing_job_ids() -> set:
    """Job IDs already in the database, so a re-run never duplicates a row."""
    seen, cursor = set(), None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        page = _call("POST", f"/databases/{_db_id()}/query", body)
        for row in page.get("results", []):
            prop = row.get("properties", {}).get("Job ID", {})
            for t in prop.get("rich_text", []) or []:
                if t.get("plain_text"):
                    seen.add(t["plain_text"])
        if not page.get("has_more"):
            return seen
        cursor = page.get("next_cursor")


def push() -> int:
    payload = _load()
    rows = [r for r in payload["rows"] if "properties" in r]
    already = _existing_job_ids()
    todo = [r for r in rows if r["job_id"] not in already]
    print(f"{len(rows)} rows in payload · {len(already)} already in Notion · {len(todo)} to create\n")
    created = failed = 0
    for r in todo:
        try:
            page = _call("POST", "/pages",
                         {"parent": {"database_id": _db_id()}, "properties": r["properties"]})
            created += 1
            print(f"  ok   {r['job_id']}  ->  {page.get('url')}")
        except SystemExit as e:
            failed += 1
            print(f"  FAIL {r['job_id']}: {e}")
    print(f"\ncreated {created}, failed {failed}, skipped {len(rows) - len(todo)}")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="auth + target + schema diff, no writes")
    g.add_argument("--fix-schema", action="store_true", help="add any missing properties")
    g.add_argument("--push", action="store_true", help="create the pages")
    a = ap.parse_args()
    if a.check:
        return check()
    if a.fix_schema:
        return fix_schema()
    return push()


if __name__ == "__main__":
    sys.exit(main())
