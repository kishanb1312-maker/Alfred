#!/usr/bin/env python3
"""Alfred · careerops_bridge — the one door between Alfred and career-ops.

Alfred keeps its own sources, contact finder, email sending and Aside-driven
applying. For everything career-ops does better it calls career-ops's own Node
scripts instead of re-implementing them:

    scan            node scan.mjs --json              zero-token ATS scan (150+ providers)
    liveness        node check-liveness.mjs <urls>    is the posting still open?
    confirm         node confirm-at-employer.mjs      aggregator listing -> employer ATS
    reposts         node detect-reposts.mjs           ghost / re-listed roles
    verify_facts    node verify-cv-facts.mjs --json   blocks invented CV claims
    merge_tracker   node merge-tracker.mjs            tracker additions -> applications.md
    set_status      node set-status.mjs               canonical tracker status update
    followups       node followup-cadence.mjs         who is due a follow-up
    doctor          node doctor.mjs --json            career-ops setup check

Every call runs with CAREER_OPS_ROOT = Alfred's home, so career-ops reads and
writes the SAME folder Alfred does (cv.md, config/profile.yml, portals.yml,
data/applications.md, reports/, output/).

The code is pinned (PIN below) and lives in DATA_HOME/vendor/career-ops,
installed by `alfred careerops-install`. A missing Node or a missing install is
reported honestly and every caller degrades: nothing here ever raises into a run.

Network boundary: only the Node scripts touch the network, and only through
`_run`, so the offline tests replace `_run` and nothing real ever executes.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Dict, Iterable, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402

REPO_URL = "https://github.com/career-ops-hq/career-ops.git"
# career-ops v1.40.0 (main, 2026-11-22). Bump deliberately: a newer commit can
# change the JSON these scripts print, so re-run scripts/run_tests.py after.
PIN = "9c9431130e979202dae5acf4458cfc6fb0db8a6f"
NODE_MIN = (22, 13)

# Hosts that re-list other companies' jobs. A listing from one of these is
# unconfirmed until it is found on the employer's own careers page / ATS.
AGGREGATOR_HOSTS = (
    "linkedin.com", "indeed.com", "wellfound.com", "angel.co", "glassdoor.",
    "naukri.com", "instahyre.com", "cutshort.io", "internshala.com", "foundit.in",
    "monster.com", "ziprecruiter.com", "weworkremotely.com", "remoteok.com",
    "jobspresso.co", "hirist.", "iimjobs.com",
)


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

def root() -> str:
    return paths.careerops_dir()


def installed() -> bool:
    r = root()
    return (os.path.isfile(os.path.join(r, "AGENTS.md"))
            and os.path.isdir(os.path.join(r, "modes"))
            and os.path.isdir(os.path.join(r, "node_modules")))


def node_version() -> Optional[tuple]:
    node = shutil.which("node")
    if not node:
        return None
    try:
        out = subprocess.run([node, "--version"], capture_output=True, text=True,
                             timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.match(r"v(\d+)\.(\d+)", out)
    return (int(m.group(1)), int(m.group(2))) if m else None


def node_ok() -> bool:
    v = node_version()
    return v is not None and v >= NODE_MIN


def env() -> Dict[str, str]:
    e = dict(os.environ)
    e["CAREER_OPS_ROOT"] = paths.careerops_data_root()
    e["CAREER_OPS_NO_ASKS"] = "1"      # no community prompts inside Alfred runs
    e.pop("CAREER_OPS_TRACKER", None)  # one tracker: DATA_HOME/data/applications.md
    return e


def status() -> Dict[str, Any]:
    v = node_version()
    return {
        "root": root(),
        "installed": installed(),
        "node": ".".join(map(str, v)) if v else None,
        "node_ok": node_ok(),
        "pin": PIN,
        "data_root": paths.careerops_data_root(),
    }


def unavailable_reason() -> Optional[str]:
    if not node_ok():
        v = node_version()
        return (f"Node {'.'.join(map(str, NODE_MIN))}+ needed (found "
                f"{'.'.join(map(str, v)) if v else 'none'})")
    if not installed():
        return f"career-ops not installed at {root()} — run: alfred careerops-install"
    return None


# ---------------------------------------------------------------------------
# The single subprocess chokepoint (tests replace this)
# ---------------------------------------------------------------------------

def _run(script: str, args: Iterable[str] = (), timeout: int = 900,
         stdin: Optional[str] = None) -> Dict[str, Any]:
    reason = unavailable_reason()
    if reason:
        return {"ok": False, "rc": None, "stdout": "", "stderr": reason, "skipped": True}
    cmd = [shutil.which("node") or "node", script, *[str(a) for a in args]]
    try:
        proc = subprocess.run(cmd, cwd=root(), env=env(), input=stdin,
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "rc": None, "stdout": "", "stderr": f"timeout after {timeout}s"}
    except OSError as exc:
        return {"ok": False, "rc": None, "stdout": "", "stderr": str(exc)}
    return {"ok": proc.returncode == 0, "rc": proc.returncode,
            "stdout": proc.stdout, "stderr": proc.stderr}


def _last_json(text: str) -> Optional[Any]:
    """The last line of stdout that parses as JSON (scripts print logs first)."""
    whole = (text or "").strip()
    if whole.startswith(("{", "[")):
        try:
            return json.loads(whole)
        except ValueError:
            pass
    for line in reversed(whole.splitlines()):
        line = line.strip()
        if line.startswith(("{", "[")):
            try:
                return json.loads(line)
            except ValueError:
                continue
    return None


# ---------------------------------------------------------------------------
# Install (clone pinned commit + npm ci + Playwright Chromium for PDFs/liveness)
# ---------------------------------------------------------------------------

def install(pin: str = PIN) -> Dict[str, Any]:
    """Clone or update career-ops to `pin`, then install its Node deps.

    Downloads code from GitHub and packages from npm: only run it when the user
    asked for setup (`alfred careerops-install`).
    """
    if not node_ok():
        return {"ok": False, "step": "node", "error": unavailable_reason()}
    git = shutil.which("git")
    if not git:
        return {"ok": False, "step": "git", "error": "git not found"}
    r = root()
    steps: List[str] = []
    if not os.path.isdir(os.path.join(r, ".git")):
        os.makedirs(os.path.dirname(r), exist_ok=True)
        rc = subprocess.call([git, "clone", "-q", "--filter=blob:none", REPO_URL, r])
        if rc != 0:
            return {"ok": False, "step": "clone", "error": f"git clone exit {rc}"}
        steps.append("cloned")
    else:
        subprocess.call([git, "-C", r, "fetch", "-q", "origin"])
        steps.append("fetched")
    rc = subprocess.call([git, "-C", r, "checkout", "-q", pin])
    if rc != 0:
        return {"ok": False, "step": "checkout", "error": f"could not check out {pin}"}
    steps.append(f"pinned {pin[:7]}")
    npm = shutil.which("npm") or "npm"
    # career-ops ships no package-lock.json, so `npm ci` refuses; install from package.json.
    verb = "ci" if os.path.isfile(os.path.join(r, "package-lock.json")) else "install"
    rc = subprocess.call([npm, verb, "--no-audit", "--no-fund", "--loglevel=error"], cwd=r)
    if rc != 0:
        return {"ok": False, "step": f"npm {verb}", "error": f"npm {verb} exit {rc}", "steps": steps}
    steps.append(f"npm {verb}")
    npx = shutil.which("npx") or "npx"
    rc = subprocess.call([npx, "playwright", "install", "chromium"], cwd=r)
    steps.append("chromium" if rc == 0 else "chromium FAILED (PDFs + liveness need it)")
    return {"ok": rc == 0, "steps": steps, "root": r}


def doctor() -> Dict[str, Any]:
    res = _run("doctor.mjs", ["--json"], timeout=120)
    data = _last_json(res["stdout"])
    if isinstance(data, dict):
        return data
    return {"error": res["stderr"] or "doctor.mjs printed no JSON", "skipped": res.get("skipped")}


def init_templates() -> Dict[str, Any]:
    """Copy career-ops personalization templates into the data root (never overwrites)."""
    res = _run("doctor.mjs", ["--json", "--init-templates"], timeout=120)
    return _last_json(res["stdout"]) or {"error": res["stderr"]}


HOUSE_START = "<!-- ALFRED HOUSE RULES START"
HOUSE_END = "<!-- ALFRED HOUSE RULES END -->"


def house_rules_text() -> str:
    with open(os.path.join(paths.CODE_ROOT, "config", "careerops_custom.alfred.md"),
              "r", encoding="utf-8") as fh:
        return fh.read().strip() + "\n"


def merge_house_rules(existing: str, rules: str) -> str:
    """PURE: put Alfred's block into modes/_custom.md, replacing an older copy and
    keeping every line the user wrote outside the markers."""
    if HOUSE_START in existing and HOUSE_END in existing:
        before = existing[:existing.index(HOUSE_START)]
        after = existing[existing.index(HOUSE_END) + len(HOUSE_END):]
        return before.rstrip() + ("\n\n" if before.strip() else "") + rules + after.lstrip("\n")
    return (existing.rstrip() + "\n\n" if existing.strip() else "") + rules


def install_house_rules() -> str:
    """Write Alfred's procedural rules into DATA_HOME/modes/_custom.md (user layer,
    read by every career-ops mode). Returns the path."""
    target = os.path.join(paths.careerops_data_root(), "modes", "_custom.md")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    try:
        with open(target, "r", encoding="utf-8") as fh:
            existing = fh.read()
    except OSError:
        existing = ""
    merged = merge_house_rules(existing, house_rules_text())
    if merged != existing:
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(merged)
    return target


def onboard_write(answers: Dict[str, Any], force: bool = False,
                  only: Optional[str] = None) -> Dict[str, Any]:
    """Write config/profile.yml + portals.yml through career-ops's own writer."""
    args = ["--answers", "-"]
    if force:
        args.append("--force")
    if only:
        args += ["--only", only]
    res = _run("onboard-write.mjs", args, timeout=120, stdin=json.dumps(answers))
    return _last_json(res["stdout"]) or {"error": res["stderr"] or res["stdout"]}


# ---------------------------------------------------------------------------
# Scan — zero-token discovery across career-ops providers
# ---------------------------------------------------------------------------

def read_scan_history(path: Optional[str] = None) -> List[Dict[str, str]]:
    path = path or paths.scan_history_path()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return []
    if not lines:
        return []
    header = lines[0].split("\t") if lines[0].startswith("url\t") else [
        "url", "first_seen", "portal", "title", "company", "status", "location"]
    body = lines[1:] if lines[0].startswith("url\t") else lines
    rows = []
    for line in body:
        cells = line.split("\t")
        rows.append({k: (cells[i] if i < len(cells) else "") for i, k in enumerate(header)})
    return rows


def normalize_scan_row(row: Dict[str, str], found_at: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """One scan-history row -> Alfred's canonical job shape. None if unusable."""
    url = (row.get("url") or "").strip()
    title = (row.get("title") or "").strip()
    company = (row.get("company") or "").strip()
    if not url or not title or not company:
        return None
    portal = (row.get("portal") or "careerops").strip() or "careerops"
    key = row.get("listing_key") or row.get("requisition_id") or url
    return {
        "job_id": f"careerops:{portal}:{key}",
        "source": "careerops_scan",
        "provider": portal,
        "title": title,
        "company": company,
        "company_domain": None,
        "location": (row.get("location") or "").strip() or None,
        "url": url,
        "posted_date": (row.get("posted_at") or "").strip() or None,
        "easy_apply": False,
        "description_snippet": None,
        "trust_flags": [f for f in (row.get("trust_flags") or "").split(",") if f],
        "found_at": found_at,
    }


def scan(since_days: Optional[int] = None, dry_run: bool = False,
         extra_args: Iterable[str] = ()) -> Dict[str, Any]:
    """Run scan.mjs and return {jobs, receipt, error}.

    scan.mjs reads its own filters from portals.yml (title/location/age) and
    appends what it finds to data/pipeline.md + data/scan-history.tsv. Alfred
    then reads back the rows the receipt names as added.
    """
    args = ["--json", "--quiet"]
    if since_days:
        args += ["--since", str(int(since_days))]
    if dry_run:
        args.append("--dry-run")
    args += list(extra_args)
    res = _run("scan.mjs", args, timeout=1800)
    receipt = _last_json(res["stdout"])
    if not isinstance(receipt, dict):
        return {"jobs": [], "receipt": None,
                "error": (res["stderr"] or "scan.mjs printed no receipt").strip()[-500:],
                "skipped": bool(res.get("skipped"))}
    added = set(receipt.get("added_urls") or [])
    jobs: List[Dict[str, Any]] = []
    if added:
        for row in read_scan_history():
            if row.get("url") in added and row.get("status", "added") == "added":
                job = normalize_scan_row(row, found_at=receipt.get("date"))
                if job:
                    jobs.append(job)
                    added.discard(row.get("url"))
    return {"jobs": jobs, "receipt": receipt, "error": None,
            "missing_rows": sorted(added)}


# ---------------------------------------------------------------------------
# Is the job real? liveness + employer confirmation + reposts
# ---------------------------------------------------------------------------

_LIVE_LINE = re.compile(r"^\S+\s+(active|expired|uncertain)\s+(?:\(api\)\s+)?(?:.*?\s)?(https?://\S+)\s*$")


def parse_liveness(stdout: str) -> Dict[str, Dict[str, Any]]:
    """check-liveness.mjs text output -> {url: {verdict, reason, via_api}}."""
    out: Dict[str, Dict[str, Any]] = {}
    last: Optional[str] = None
    for raw in (stdout or "").splitlines():
        m = _LIVE_LINE.match(raw.strip())
        if m:
            verdict, url = m.group(1), m.group(2)
            out[url] = {"verdict": verdict, "reason": None, "via_api": "(api)" in raw}
            last = url
        elif last and raw.startswith("           ") and raw.strip():
            out[last]["reason"] = raw.strip()
    return out


def is_aggregator(url: Optional[str]) -> bool:
    host = (url or "").lower()
    return any(h in host for h in AGGREGATOR_HOSTS)


def liveness(urls: List[str], record: bool = True) -> Dict[str, Any]:
    """Check employer/ATS URLs. Aggregator URLs are refused here: an aggregator
    page shows a title + Apply long after the role closed, so it proves nothing."""
    direct = [u for u in urls if u and not is_aggregator(u)]
    result: Dict[str, Any] = {"verdicts": {}, "skipped_aggregators": [u for u in urls if is_aggregator(u)]}
    if not direct:
        return result
    fd, tmp = tempfile.mkstemp(prefix="alfred-urls-", suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("\n".join(direct) + "\n")
    args = ["--file", tmp] + ([] if record else ["--no-record"])
    try:
        res = _run("check-liveness.mjs", args, timeout=1800)
    finally:
        os.unlink(tmp)
    result["verdicts"] = parse_liveness(res["stdout"])
    if not res["ok"] and not result["verdicts"]:
        result["error"] = (res["stderr"] or "check-liveness.mjs failed").strip()[-500:]
    for u in direct:
        result["verdicts"].setdefault(u, {"verdict": "uncertain", "reason": "not reported"})
    return result


def confirm_at_employer(url: str, company: str, title: str,
                        origin: Optional[str] = None) -> Dict[str, Any]:
    """Find an aggregator listing on the employer's own ATS. Read-only.

    Posting strings go through a JSON file, never a shell argument.
    """
    payload = {"url": url, "company": company, "title": title}
    if origin:
        payload["origin"] = origin
    fd, tmp = tempfile.mkstemp(prefix="alfred-posting-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(payload, fh)
    try:
        res = _run("confirm-at-employer.mjs", ["--input", tmp, "--json"], timeout=300)
    finally:
        os.unlink(tmp)
    data = _last_json(res["stdout"])
    if isinstance(data, dict):
        return data
    return {"verdict": "error", "error": (res["stderr"] or "no JSON").strip()[-300:],
            "skipped": bool(res.get("skipped"))}


def reposts(window_days: int = 90) -> Dict[str, Any]:
    res = _run("detect-reposts.mjs", ["--window", str(window_days)], timeout=300)
    data = _last_json(res["stdout"])
    return data if isinstance(data, dict) else {"clusters": [], "error": res["stderr"]}


def repost_urls(report: Dict[str, Any]) -> Dict[str, str]:
    """{url: 'company · title (n listings)'} for every URL in a repost cluster."""
    flagged: Dict[str, str] = {}
    for c in report.get("clusters") or []:
        label = f"{c.get('company', '?')} · {c.get('role') or '?'}"
        urls = [a.get("url") for a in (c.get("appearances") or [])
                if isinstance(a, dict) and a.get("url")]
        span = c.get("daysSpan")
        for u in urls:
            flagged[u] = (f"{label}: listed {c.get('repostCount', len(urls))} times"
                          + (f" over {span} days" if span is not None else ""))
    return flagged


# ---------------------------------------------------------------------------
# Truthfulness gate + tracker
# ---------------------------------------------------------------------------

def verify_facts(generated: str, sources: Optional[List[str]] = None) -> Dict[str, Any]:
    """Run the CV fact gate. verdict: pass | warn | block | error."""
    # career-ops scripts run with cwd=vendor/career-ops, so a path relative to the
    # caller's cwd (e.g. "output/x.html" from the Alfred home) must be made absolute.
    args = [os.path.abspath(generated), "--json"]
    for s in sources or []:
        args += ["--source", os.path.abspath(s)]
    res = _run("verify-cv-facts.mjs", args, timeout=300)
    data = _last_json(res["stdout"])
    if isinstance(data, dict) and data.get("verdict"):
        return data
    return {"verdict": "error", "errors": [(res["stderr"] or "no JSON").strip()[-300:]],
            "skipped": bool(res.get("skipped"))}


def merge_tracker() -> Dict[str, Any]:
    res = _run("merge-tracker.mjs", [], timeout=300)
    return {"ok": res["ok"], "output": (res["stdout"] + res["stderr"]).strip()[-2000:]}


VALID_STATES = ("Evaluated", "Applied", "Responded", "Assessment", "Interview",
                "Offer", "Hired", "Rejected", "Discarded", "SKIP", "Speculative")


def set_status(selector: str, state: str, note: Optional[str] = None,
               by_report: bool = True) -> Dict[str, Any]:
    if state not in VALID_STATES:
        return {"ok": False, "error": f"not a canonical state: {state}"}
    args = (["--report", str(selector)] if by_report else [str(selector)]) + [state]
    if note:
        args += ["--note", note]
    res = _run("set-status.mjs", args, timeout=120)
    return {"ok": res["ok"], "output": (res["stdout"] + res["stderr"]).strip()[-1000:]}


def followups() -> Dict[str, Any]:
    res = _run("followup-cadence.mjs", ["--json"], timeout=120)
    data = _last_json(res["stdout"])
    return data if isinstance(data, dict) else {"error": res["stderr"]}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli(argv: List[str]) -> int:
    cmd = argv[0] if argv else "status"
    if cmd == "status":
        print(json.dumps(status(), indent=2))
        return 0
    if cmd == "install":
        res = install()
        print(json.dumps(res, indent=2))
        return 0 if res.get("ok") else 1
    if cmd == "doctor":
        print(json.dumps(doctor(), indent=2))
        return 0
    if cmd == "house-rules":
        print(install_house_rules())
        return 0
    if cmd == "scan":
        since = int(argv[1]) if len(argv) > 1 else None
        res = scan(since_days=since)
        print(json.dumps({"count": len(res["jobs"]), "error": res["error"],
                          "receipt": res["receipt"], "jobs": res["jobs"]}, indent=2))
        return 0 if res["error"] is None else 1
    if cmd == "liveness":
        print(json.dumps(liveness(argv[1:]), indent=2))
        return 0
    if cmd == "reposts":
        print(json.dumps(reposts(), indent=2))
        return 0
    if cmd == "verify" and len(argv) > 1:
        res = verify_facts(argv[1], argv[2:])
        print(json.dumps(res, indent=2))
        return 1 if res.get("verdict") in ("block", "error") else 0
    if cmd == "merge":
        print(merge_tracker()["output"])
        return 0
    if cmd == "followups":
        print(json.dumps(followups(), indent=2))
        return 0
    print("usage: careerops_bridge.py status|install|doctor|house-rules|scan [days]|liveness <url..>|"
          "reposts|verify <cv> [sources..]|merge|followups")
    return 2


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
