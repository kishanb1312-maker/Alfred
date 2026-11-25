#!/usr/bin/env python3
"""Alfred · run_report — one Markdown report + one HTML dashboard per run.

Reads only local files (no network):
    data/finder_report.json      jobs per source
    data/verified_jobs.json      / data/verify_dropped.json
    data/evaluation_output.json  career-ops scores
    data/review_queue.json       jobs that reached your review list
    data/job_decisions.json      approve / skip
    data/apply_results.json      what happened on each application (review_store)
    data/scheduled_emails.json   emails Aside scheduled in Gmail
    data/email_sent.json         emails sent through Gmail SMTP
    data/applications.md         the career-ops tracker (every row)

Writes:
    output/reports/run-report-YYYY-MM-DD.md
    output/reports/dashboard-YYYY-MM-DD.html   (self-contained, opens offline)
    output/reports/dashboard.html              (latest copy)

Usage: run_report.py [--date YYYY-MM-DD] [--open]
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from datetime import date
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402
import review_store as rs  # noqa: E402


def _read(name: str, default: Any) -> Any:
    try:
        with open(os.path.join(paths.data_dir(), name), "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def parse_tracker(text: str) -> List[Dict[str, str]]:
    """PURE: rows of the first markdown table in applications.md as dicts."""
    rows, header = [], None
    for line in (text or "").splitlines():
        if not line.strip().startswith("|"):
            if header and rows:
                break
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        rows.append({header[i]: (cells[i] if i < len(cells) else "") for i in range(len(header))})
    return rows


def _link_target(cell: str) -> str:
    m = re.search(r"\]\(([^)]+)\)", cell or "")
    return m.group(1) if m else (cell or "")


def collect() -> Dict[str, Any]:
    finder = _read("finder_report.json", {})
    sources = (finder.get("sources") or finder.get("per_source")) if isinstance(finder, dict) else finder
    if isinstance(sources, dict):  # {"linkedin_feed": {...} | 12}
        sources = [{"source": k, **(v if isinstance(v, dict) else {"count": v})} for k, v in sources.items()]
    if not isinstance(sources, list):
        sources = []
    verified = _read("verified_jobs.json", [])
    dropped = _read("verify_dropped.json", [])
    evaluated = _read("evaluation_output.json", [])
    reviewed = [j for j in rs.all_review_jobs() if j]
    decisions = _read("job_decisions.json", {})
    results = rs.apply_results()
    scheduled = rs.scheduled_emails()
    sent = _read("email_sent.json", {})
    try:
        with open(paths.tracker_path(), "r", encoding="utf-8") as fh:
            tracker = parse_tracker(fh.read())
    except OSError:
        tracker = []

    jobs = []
    for j in reviewed:
        jid = j["job_id"]
        res = results.get(jid) or {}
        em = scheduled.get(jid) or {}
        sm = sent.get(jid) or {}
        jobs.append({
            "job_id": jid, "company": j.get("company"), "title": j.get("title"),
            "location": j.get("location"), "bucket": rs.location_bucket(j),
            "score": j.get("score"), "recommendation": j.get("recommendation"),
            "decision": (decisions.get(jid) or {}).get("decision") or "waiting",
            "apply_status": res.get("status") or ("queued" if jid in rs.approved_queue() else "—"),
            "host": res.get("host"), "applied_at": res.get("ts") if res.get("status") == "submitted" else None,
            "confirmation": res.get("confirmation"), "final_url": res.get("final_url") or j.get("employer_url") or j.get("url"),
            "unanswered": res.get("unanswered") or [], "notes": res.get("notes"),
            "email": (f"scheduled {em.get('scheduled_for')} → {em.get('to')}" if em.get("status") == "scheduled"
                      else f"sent → {sm.get('to')}" if sm.get("status") == "SENT"
                      else (em.get("status") or ("draft" if rs.load_draft(jid) else "—"))),
            "cv_pdf": j.get("cv_pdf"), "report": j.get("report"), "fact_check": j.get("fact_check"),
        })

    def count(pred) -> int:
        return sum(1 for x in jobs if pred(x))
    totals = {
        "found": (finder.get("final_count") if isinstance(finder, dict) and finder.get("final_count") is not None
                  else sum(int(s.get("count") or s.get("kept") or 0) for s in sources if isinstance(s, dict))),
        "verified": len(verified) if isinstance(verified, list) else 0,
        "dropped": len(dropped) if isinstance(dropped, list) else 0,
        "evaluated": len(evaluated) if isinstance(evaluated, list) else 0,
        "on_review": len(jobs),
        "approved": count(lambda x: x["decision"] == "approved"),
        "applied": count(lambda x: x["apply_status"] == "submitted"),
        "needs_you": count(lambda x: x["apply_status"] in ("filled", "blocked", "failed")),
        "emails_scheduled": sum(1 for e in scheduled.values() if e.get("status") == "scheduled"),
        "emails_sent": sum(1 for e in sent.values() if isinstance(e, dict) and e.get("status") == "SENT"),
        "tracker_rows": len(tracker),
    }
    return {"date": date.today().isoformat(), "totals": totals, "jobs": jobs, "sources": sources,
            "dropped": dropped if isinstance(dropped, list) else [], "tracker": tracker,
            "dry_run": _dry_run()}


def _dry_run() -> Optional[bool]:
    try:
        import yaml
        with open(paths.search_config(), "r", encoding="utf-8") as fh:
            return bool((yaml.safe_load(fh) or {}).get("dry_run", True))
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

def _md_cell(v: Any) -> str:
    return str(v if v not in (None, "") else "—").replace("|", "/").replace("\n", " ")


def render_md(d: Dict[str, Any]) -> str:
    t = d["totals"]
    mode = "DRY RUN — nothing submitted or sent" if d["dry_run"] else "LIVE"
    out = [f"# Alfred run report — {d['date']}", "", f"**Mode:** {mode}", "",
           "| Found | Still open | Dropped | Evaluated | On review | Approved | **Applied** | Needs you | Emails scheduled | Emails sent |",
           "|---|---|---|---|---|---|---|---|---|---|",
           f"| {t['found']} | {t['verified']} | {t['dropped']} | {t['evaluated']} | {t['on_review']} | "
           f"{t['approved']} | **{t['applied']}** | {t['needs_you']} | {t['emails_scheduled']} | {t['emails_sent']} |", ""]
    applied = [j for j in d["jobs"] if j["apply_status"] == "submitted"]
    out += ["## Applied", ""]
    if applied:
        out += ["| Company | Role | Location | Score | Via | When | Confirmation | Email | CV |", "|---|---|---|---|---|---|---|---|---|"]
        for j in applied:
            out.append("| " + " | ".join(_md_cell(x) for x in (
                j["company"], j["title"], j["location"], j["score"], j["host"], j["applied_at"],
                j["confirmation"], j["email"], os.path.basename(j["cv_pdf"] or "") or None)) + " |")
    else:
        out.append("Nothing submitted in this run.")
    need = [j for j in d["jobs"] if j["apply_status"] in ("filled", "blocked", "failed")]
    out += ["", "## Needs you", ""]
    if need:
        for j in need:
            miss = "; ".join(j["unanswered"]) if j["unanswered"] else (j["notes"] or "")
            out.append(f"- **{j['company']} — {j['title']}** ({j['apply_status']}): {miss} → {j['final_url']}")
    else:
        out.append("Nothing waiting on you.")
    waiting = [j for j in d["jobs"] if j["decision"] == "waiting"]
    out += ["", "## Waiting for your approval", ""]
    out += [f"- {j['score']} · {j['company']} — {j['title']} ({j['bucket']}) · `{j['job_id']}`" for j in waiting] or ["None."]
    out += ["", "## Every job on the review list", "",
            "| Company | Role | Location | Priority | Score | Decision | Application | Email | Fact check | Report |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for j in d["jobs"]:
        out.append("| " + " | ".join(_md_cell(x) for x in (
            j["company"], j["title"], j["location"], j["bucket"], j["score"], j["decision"],
            j["apply_status"], j["email"], j["fact_check"], j["report"])) + " |")
    if d["sources"]:
        out += ["", "## Sources", "", "| Source | Status | Jobs | Note |", "|---|---|---|---|"]
        for s in d["sources"]:
            out.append("| " + " | ".join(_md_cell(s.get(k)) for k in ("source", "status", "count", "note")) + " |")
    if d["dropped"]:
        out += ["", "## Dropped as closed or stale", ""]
        out += [f"- {j.get('company')} — {j.get('title')}: {(j.get('verification') or {}).get('reason')}"
                for j in d["dropped"][:50]]
    out += ["", f"Tracker: `data/applications.md` ({t['tracker_rows']} rows) · reports in `reports/`", ""]
    return "\n".join(out)


# ---------------------------------------------------------------------------
# HTML dashboard (single file, no external requests)
# ---------------------------------------------------------------------------

_CSS = """
:root{--bg:#f7f7f5;--card:#fff;--ink:#1d1d1b;--mute:#6b6b66;--line:#e4e3de;--accent:#2f6fed;
--ok:#1f8a4c;--warn:#b26a00;--bad:#c0392b;--chip:#eef1f7}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--card:#1e1e1c;--ink:#ecebe6;--mute:#a3a29c;
--line:#33332f;--accent:#7aa2ff;--ok:#4cc38a;--warn:#e0a54a;--bad:#ff7a6b;--chip:#272a33}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
main{max-width:1200px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:28px 0 10px}
.mode{color:var(--mute);margin-bottom:18px}.mode b{color:var(--warn)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}
.tile .n{font-size:24px;font-weight:650}.tile .l{color:var(--mute);font-size:12px}
.tile.hi .n{color:var(--ok)}.tile.need .n{color:var(--warn)}
.bar{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}
input,select{background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:6px 10px;font:inherit}
.wrap{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:10px}
table{border-collapse:collapse;width:100%;min-width:900px}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:12px;color:var(--mute);cursor:pointer;white-space:nowrap;position:sticky;top:0;background:var(--card)}
tr:last-child td{border-bottom:0}
.chip{display:inline-block;padding:1px 8px;border-radius:999px;background:var(--chip);font-size:12px;white-space:nowrap}
.submitted{color:var(--ok)}.filled,.blocked,.failed{color:var(--warn)}.skipped{color:var(--mute)}
a{color:var(--accent)}.mute{color:var(--mute)}
"""

_JS = """
const D=JSON.parse(document.getElementById('data').textContent);
const esc=s=>String(s??'—').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const cols=[['company','Company'],['title','Role'],['location','Location'],['bucket','Priority'],
['score','Score'],['decision','Decision'],['apply_status','Application'],['host','Via'],
['applied_at','Applied at'],['email','Email'],['fact_check','Fact check']];
let sortK='bucket',dir=1;
function row(j){return '<tr>'+cols.map(([k])=>{let v=j[k];
 if(k==='apply_status')return `<td><span class="chip ${esc(v)}">${esc(v)}</span></td>`;
 if(k==='title'&&j.final_url)return `<td><a href="${esc(j.final_url)}" target="_blank" rel="noopener">${esc(v)}</a></td>`;
 return `<td>${esc(v)}</td>`}).join('')+'</tr>'}
function draw(){const q=document.getElementById('q').value.toLowerCase(),f=document.getElementById('f').value;
 let rows=D.jobs.filter(j=>(!f||j.apply_status===f||j.decision===f||j.bucket===f)&&
   (!q||JSON.stringify(j).toLowerCase().includes(q)));
 rows.sort((a,b)=>String(a[sortK]??'').localeCompare(String(b[sortK]??''),undefined,{numeric:true})*dir);
 document.getElementById('h').innerHTML=cols.map(([k,l])=>`<th data-k="${k}">${l}${k===sortK?(dir>0?' ▲':' ▼'):''}</th>`).join('');
 document.getElementById('b').innerHTML=rows.map(row).join('')||'<tr><td colspan="11" class="mute">No jobs match.</td></tr>';
 document.querySelectorAll('th').forEach(th=>th.onclick=()=>{const k=th.dataset.k;dir=k===sortK?-dir:1;sortK=k;draw()})}
document.getElementById('q').oninput=draw;document.getElementById('f').onchange=draw;draw();
"""


def render_html(d: Dict[str, Any]) -> str:
    t = d["totals"]
    tiles = [("Found", t["found"], ""), ("Still open", t["verified"], ""), ("Evaluated", t["evaluated"], ""),
             ("On review", t["on_review"], ""), ("Approved", t["approved"], ""), ("Applied", t["applied"], "hi"),
             ("Needs you", t["needs_you"], "need"), ("Emails scheduled", t["emails_scheduled"], ""),
             ("Emails sent", t["emails_sent"], ""), ("Tracker rows", t["tracker_rows"], "")]
    tile_html = "".join(f'<div class="tile {c}"><div class="n">{n}</div><div class="l">{html.escape(l)}</div></div>'
                        for l, n, c in tiles)
    mode = "<b>DRY RUN</b> — nothing submitted or sent" if d["dry_run"] else "LIVE run"
    tracker_rows = "".join(
        "<tr>" + "".join(f"<td>{html.escape(r.get(k, '') or '—')}</td>"
                         for k in ("#", "date", "company", "role", "score", "status", "notes")) + "</tr>"
        for r in d["tracker"])
    data = json.dumps({"jobs": d["jobs"]}).replace("</", "<\\/")
    opts = "".join(f'<option value="{v}">{v}</option>' for v in
                   ("submitted", "filled", "blocked", "failed", "queued", "waiting", "approved", "skipped",
                    "remote_abroad", "india", "onsite_abroad"))
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Alfred dashboard {d['date']}</title>
<style>{_CSS}</style></head><body><main>
<h1>Alfred dashboard</h1><div class="mode">{d['date']} · {mode}</div>
<div class="tiles">{tile_html}</div>
<h2>Jobs on the review list</h2>
<div class="bar"><input id="q" placeholder="Search company, role, location…" size="32">
<select id="f"><option value="">All</option>{opts}</select></div>
<div class="wrap"><table><thead><tr id="h"></tr></thead><tbody id="b"></tbody></table></div>
<h2>Tracker (data/applications.md)</h2>
<div class="wrap"><table><thead><tr><th>#</th><th>Date</th><th>Company</th><th>Role</th><th>Score</th><th>Status</th><th>Notes</th></tr></thead>
<tbody>{tracker_rows or '<tr><td colspan="7" class="mute">Tracker is empty.</td></tr>'}</tbody></table></div>
<script type="application/json" id="data">{data}</script><script>{_JS}</script>
</main></body></html>"""


def write(d: Optional[Dict[str, Any]] = None, out_dir: Optional[str] = None) -> Dict[str, str]:
    d = d or collect()
    out_dir = out_dir or os.path.join(paths.output_dir(), "reports")
    os.makedirs(out_dir, exist_ok=True)
    md = os.path.join(out_dir, f"run-report-{d['date']}.md")
    page = os.path.join(out_dir, f"dashboard-{d['date']}.html")
    latest = os.path.join(out_dir, "dashboard.html")
    with open(md, "w", encoding="utf-8") as fh:
        fh.write(render_md(d))
    body = render_html(d)
    for p in (page, latest):
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(body)
    return {"md": md, "dashboard": page, "latest": latest}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--open", action="store_true")
    a = ap.parse_args(argv)
    d = collect()
    if a.date:
        d["date"] = a.date
    out = write(d)
    print(json.dumps({**out, "totals": d["totals"]}, indent=2))
    if a.open and sys.platform == "darwin":
        os.system(f'open "{out["dashboard"]}"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
