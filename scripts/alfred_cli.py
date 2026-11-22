#!/usr/bin/env python3
"""Alfred · alfred — the host-agnostic setup/maintenance CLI (§5).

A single entrypoint for the plugin's first-run setup and health checks. It is the
ONLY place secrets ever enter Alfred, and they enter via getpass (no echo) —
never typed into chat, never printed, never written by the assistant.

Subcommands:
    alfred bootstrap                 create the venv + install deps + init (cross-platform, no shell)
    alfred env                       print the venv's python path for THIS OS (copy-pasteable)
    alfred init                      create ~/.alfred/{config,data,output}/ + copy templates
    alfred set-secret <KEY>          getpass (hidden) → write KEY=value into ~/.alfred/.env
    alfred doctor                    full health checklist (superset of orchestrate --preflight)
    alfred parse-resume <path.docx>  copy resume into data/ + print extracted vs still-needed fields
    alfred cv-from-docx <path.docx>  first cv.md (career-ops's CV source) from the resume
    alfred careerops-install         clone the pinned career-ops engine + npm deps + Chromium
    alfred careerops-status          is career-ops installed, which Node, which pin
    alfred careerops-onboard <answers.json>   write config/profile.yml + portals.yml
    alfred review | approve <id> [--email] | skip <id> | queue | pause | resume
                                     the manual approval gate (see review_store.py)

Cross-platform note: this CLI runs the same on Windows, macOS, and Linux — every
path is built with os.path and the home dir resolves via os.path.expanduser("~")
(=%USERPROFILE% on Windows). `bootstrap` exists so first-run setup needs no Bash:
it drives `python -m venv` + pip via subprocess in pure Python.

Path model (see paths.py §4): CODE lives in the plugin dir ($CLAUDE_PLUGIN_ROOT),
USER DATA lives in the home dir. Every write here targets `home_target()` — the real
$ALFRED_HOME or ~/.alfred — never the legacy repo-root fallback, because these
commands create/manage that home dir (on first `init` it does not exist yet).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from typing import Any, Callable, Dict, List, Optional

# scripts/ on sys.path (sys.path[0] when run directly; already present when imported).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402  single source of truth for CODE_ROOT + example templates


# ---------------------------------------------------------------------------
# Key sets (from .env.example / SPEC §8a)
# ---------------------------------------------------------------------------

# Gmail is the only required secret: it sends the cold emails you approve.
REQUIRED_SECRETS = ["GMAIL_ADDRESS", "GMAIL_APP_PASSWORD"]
OPTIONAL_SECRETS = ["HUNTER_API_KEY", "APOLLO_API_KEY"]
KNOWN_KEYS = REQUIRED_SECRETS + OPTIONAL_SECRETS


# ---------------------------------------------------------------------------
# Home-dir resolution — the CLI's write target (NOT paths.DATA_HOME; see docstring)
# ---------------------------------------------------------------------------

def home_target() -> str:
    """Resolved the same way as paths._resolve_data_home() (minus the repo-root
    fallback) so reads and writes always agree — including for a pre-rename install
    that still lives in $WARMAPPLY_HOME / ~/.warmapply."""
    for var in ("ALFRED_HOME", "WARMAPPLY_HOME"):
        override = os.environ.get(var, "").strip()
        if override:
            return os.path.abspath(os.path.expanduser(override))

    fresh = os.path.join(os.path.expanduser("~"), ".alfred")
    legacy = os.path.join(os.path.expanduser("~"), ".warmapply")
    if not os.path.isdir(fresh) and os.path.isdir(legacy):
        return legacy
    return fresh


def home_paths(home: Optional[str] = None) -> Dict[str, str]:
    home = home or home_target()
    return {
        "home": home,
        "config": os.path.join(home, "config"),
        "data": os.path.join(home, "data"),
        "output": os.path.join(home, "output"),
        "env": os.path.join(home, ".env"),
        "search": os.path.join(home, "config", "search.yaml"),
        "profile": os.path.join(home, "config", "profile.yaml"),
    }


# ---------------------------------------------------------------------------
# .env upsert — PURE text transform (unit-testable, never touches getpass/stdin)
# ---------------------------------------------------------------------------

def upsert_env_line(text: str, key: str, value: str) -> str:
    """Return `text` with `KEY=value` set: replace the first existing KEY line
    (commented or not, with/without `export`) else append. Order & comments kept."""
    pat = re.compile(rf"^\s*(?:export\s+)?#?\s*{re.escape(key)}\s*=")
    out: List[str] = []
    replaced = False
    for line in text.splitlines():
        if not replaced and pat.match(line):
            out.append(f"{key}={value}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.append(f"{key}={value}")
    return "\n".join(out) + "\n"


def write_secret(env_path: str, key: str, value: str) -> None:
    """Atomically upsert KEY into the env file with 0600 perms. Value never logged."""
    os.makedirs(os.path.dirname(env_path), exist_ok=True)
    text = ""
    if os.path.isfile(env_path):
        with open(env_path, "r", encoding="utf-8") as fh:
            text = fh.read()
    new_text = upsert_env_line(text, key, value)
    tmp = env_path + ".tmp"
    # Create the temp file 0600 from the START (not chmod-after-write) so a secret
    # is never briefly world-readable. O_CREAT applies the mode only on creation, so
    # drop any stale tmp first to guarantee our perms win.
    if os.path.exists(tmp):
        os.unlink(tmp)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(new_text)
    os.replace(tmp, env_path)


def _read_env_values(env_path: str) -> Dict[str, str]:
    """Parse KEY=value pairs from the env file (for doctor's filled/blank check)."""
    values: Dict[str, str] = {}
    if not os.path.isfile(env_path):
        return values
    with open(env_path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[len("export "):].lstrip()
            k, _, v = line.partition("=")
            values[k.strip()] = v.strip().strip("'\"")
    return values


# ---------------------------------------------------------------------------
# venv location — identical logic on every OS, only the leaf dir differs
# ---------------------------------------------------------------------------

def venv_dir(home: Optional[str] = None) -> str:
    return os.path.join(home or home_target(), ".venv")


def venv_python(home: Optional[str] = None) -> str:
    """Path to the venv's python interpreter for the CURRENT OS.

    Windows puts it at .venv\\Scripts\\python.exe; POSIX at .venv/bin/python.
    """
    vdir = venv_dir(home)
    if os.name == "nt":
        return os.path.join(vdir, "Scripts", "python.exe")
    return os.path.join(vdir, "bin", "python")


# ---------------------------------------------------------------------------
# env — print the venv python path (so the wizard can hand over one command)
# ---------------------------------------------------------------------------

def cmd_env(args: argparse.Namespace) -> int:
    vpy = venv_python()
    exists = os.path.isfile(vpy)
    print(vpy if exists else f"{vpy}  (not created yet — run: alfred bootstrap)")
    return 0 if exists else 1


# ---------------------------------------------------------------------------
# bootstrap — venv + deps + init, in pure Python (no Bash / PowerShell needed)
# ---------------------------------------------------------------------------

def cmd_bootstrap(args: argparse.Namespace) -> int:
    """Create the venv, install requirements into it, and run init.

    Runs the same on Windows, macOS, and Linux — it shells out only to Python
    itself (venv + pip) via subprocess, so no OS-specific shell syntax is needed.
    """
    import subprocess

    hp = home_paths()
    os.makedirs(hp["home"], exist_ok=True)
    vdir = venv_dir(hp["home"])
    vpy = venv_python(hp["home"])

    # 1) venv (idempotent — python -m venv is a no-op refresh if it already exists)
    if os.path.isfile(vpy):
        print(f"  •  venv exists : {vdir}")
    else:
        print(f"  ⏳ creating venv: {vdir}")
        rc = subprocess.call([sys.executable, "-m", "venv", vdir])
        if rc != 0 or not os.path.isfile(vpy):
            print("❌ failed to create the virtual environment. Is Python 3.8+ installed "
                  "and on PATH? (Windows: install from python.org and tick "
                  "'Add python.exe to PATH'.)")
            return 1

    # 2) deps — install requirements.txt into the venv (not the system interpreter)
    req = os.path.join(paths.CODE_ROOT, "requirements.txt")
    if not os.path.isfile(req):
        print(f"⚠️  requirements.txt not found at {req} — skipping dependency install.")
    else:
        print(f"  ⏳ installing deps from {req}")
        rc = subprocess.call([vpy, "-m", "pip", "install", "-q",
                              "--disable-pip-version-check", "-r", req])
        if rc != 0:
            print("❌ dependency install failed. Re-run manually:\n"
                  f'   "{vpy}" -m pip install -r "{req}"')
            return 1

    # 3) init the data dir + templates
    print("  ⏳ initializing data dir")
    cmd_init(args)

    print("-" * 60)
    print("✅ bootstrap complete. From here, run the CLI with the VENV python:")
    print(f'   "{vpy}" "{os.path.join(paths.CODE_ROOT, "scripts", "alfred_cli.py")}" doctor')
    return 0


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------

def cmd_init(args: argparse.Namespace) -> int:
    hp = home_paths()
    created: List[str] = []
    skipped: List[str] = []

    for d in (hp["home"], hp["config"], hp["data"], hp["output"]):
        if os.path.isdir(d):
            skipped.append(d)
        else:
            os.makedirs(d, exist_ok=True)
            created.append(d)

    # Copy bundled templates (never overwrite a file the user already has → idempotent).
    for src, dst in ((paths.search_example(), hp["search"]),
                     (paths.profile_example(), hp["profile"]),
                     (paths.env_example(), hp["env"])):
        if os.path.exists(dst):
            skipped.append(dst)
            continue
        if not os.path.exists(src):
            print(f"  ⚠️  template not found (skipped): {src}")
            continue
        shutil.copyfile(src, dst)
        if dst == hp["env"]:
            os.chmod(dst, 0o600)  # .env holds secrets → lock it down from creation
        created.append(dst)

    print(f"Alfred · init  →  {hp['home']}")
    print("-" * 60)
    for c in created:
        print(f"  ✅ created : {c}")
    for s in skipped:
        print(f"  •  exists  : {s}")
    print("-" * 60)
    print("Next:")
    print("  1. alfred set-secret GMAIL_ADDRESS   (then GMAIL_APP_PASSWORD)")
    print("  2. alfred careerops-install          (the career-ops engine; needs Node 22.13+)")
    print("  3. alfred cv-from-docx <resume.docx> (then /alfred:alfred-setup finishes the profile)")
    print("  4. alfred doctor")
    return 0


# ---------------------------------------------------------------------------
# set-secret  (the ONLY way secrets enter — getpass, no echo)
# ---------------------------------------------------------------------------

def cmd_set_secret(args: argparse.Namespace) -> int:
    import getpass

    key = args.key.strip()
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
        print(f"❌ invalid key '{key}' — expected UPPER_SNAKE_CASE (e.g. GMAIL_ADDRESS)")
        return 2
    if key not in KNOWN_KEYS:
        print(f"⚠️  '{key}' is not a recognized Alfred key — setting it anyway.")

    hp = home_paths()
    if not os.path.isdir(hp["home"]):
        print(f"⚠️  {hp['home']} does not exist yet — creating it "
              "(run `alfred init` for the full skeleton).")
        os.makedirs(hp["home"], exist_ok=True)

    try:
        value = getpass.getpass(f"Enter value for {key} (input hidden, not echoed): ")
    except (EOFError, KeyboardInterrupt):
        print("\n(aborted — nothing written)")
        return 1

    if value == "":
        print("(empty value — nothing written)")
        return 1

    write_secret(hp["env"], key, value)
    del value  # do not keep the secret in memory longer than needed
    print(f"✅ {key} saved to {hp['env']}  (value hidden; file perms 600).")
    return 0


# ---------------------------------------------------------------------------
# doctor  (superset of orchestrate --preflight)
# ---------------------------------------------------------------------------

_DEP_MODULES = [("yaml", "PyYAML"), ("docx", "python-docx"), ("requests", "requests"),
                ("dns.resolver", "dnspython"), ("email_validator", "email-validator")]


def _mark(status: str) -> str:
    # "info" is a stated fact, not something to act on — it renders as a neutral bullet
    # and is excluded from the advisories list, unlike "warn".
    return {"ok": "✅", "warn": "⚠️ ", "fail": "❌", "info": "•"}.get(status, "•")


def cmd_doctor(args: argparse.Namespace) -> int:
    import orchestrate  # reuse the exact preflight checks (configs/resume/dry_run/pause)

    hp = home_paths()
    if not os.path.isdir(hp["home"]):
        print(f"❌ Alfred is not initialized — run `alfred init` "
              f"(expected {hp['home']}).")
        return 1
    paths.load_env(hp["env"])

    checks: List[tuple] = []  # (status, label, detail)

    # 1) Python deps importable (required)
    missing = [pkg for mod, pkg in _DEP_MODULES if not _importable(mod)]
    checks.append(("fail" if missing else "ok", "Python deps",
                   (", ".join(missing) + " missing — pip install -r requirements.txt")
                   if missing else "all importable"))

    # 2) Configs valid + resume present + dry_run/pause — delegate to preflight
    report = orchestrate.preflight(
        search_path=hp["search"], profile_path=hp["profile"],
        resume_glob=os.path.join(hp["data"], "*.docx"),
        pause_flag=os.path.join(hp["data"], "paused.flag"),
        cv_path=os.path.join(hp["home"], "cv.md"),
    )
    c = report["checks"]
    checks.append(("ok" if c["search_config"]["exists"] else "fail",
                   "search config", hp["search"]))
    checks.append(("ok" if c["profile_config"]["exists"] else "fail",
                   "profile config", hp["profile"]))
    checks.append(("ok" if c["cv"]["exists"] else "fail", "cv.md",
                   c["cv"]["path"] if c["cv"]["exists"]
                   else c["cv"]["path"] + " missing — alfred cv-from-docx <resume.docx>"))
    checks.append(("ok" if c["resume"]["exists"] else "info", "master resume (.docx)",
                   (c["resume"]["found"][0] if c["resume"]["found"]
                    else "none in data/ (only needed to create cv.md)")))

    # 3) Required secrets filled (required)
    env_vals = _read_env_values(hp["env"])
    empty_required = [k for k in REQUIRED_SECRETS if not env_vals.get(k, "").strip()]
    checks.append(("fail" if empty_required else "ok", "required secrets",
                   ("blank: " + ", ".join(empty_required) + "  (alfred set-secret <KEY>)")
                   if empty_required else "all set (GMAIL_*)"))

    # 4) Optional secrets (advisory)
    empty_optional = [k for k in OPTIONAL_SECRETS if not env_vals.get(k, "").strip()]
    checks.append(("warn" if empty_optional else "ok", "optional secrets",
                   ("blank (fine to leave): " + ", ".join(empty_optional))
                   if empty_optional else "all set"))

    # 5) career-ops engine: Node + pinned install + its own setup check.
    import careerops_bridge as cob
    st = cob.status()
    checks.append(("ok" if st["node_ok"] else "fail", "Node.js",
                   (st["node"] or "not found") + ("" if st["node_ok"] else
                    f" — need {'.'.join(map(str, cob.NODE_MIN))}+ (brew install node)")))
    checks.append(("ok" if st["installed"] else "fail", "career-ops",
                   (f"{st['root']} @ {cob.PIN[:7]}") if st["installed"]
                   else "not installed — alfred careerops-install"))
    if st["installed"] and st["node_ok"]:
        cdoc = cob.doctor()
        missing = cdoc.get("missing") or []
        unpers = [u.get("path") for u in (cdoc.get("unpersonalized") or []) if isinstance(u, dict)]
        if cdoc.get("dataRootError"):
            checks.append(("fail", "career-ops data", str(cdoc.get("warnings", ["data root refused"])[0])))
        elif missing:
            checks.append(("fail", "career-ops setup", "missing: " + ", ".join(missing)
                           + "  (/alfred:alfred-setup)"))
        else:
            checks.append(("warn" if unpers else "ok", "career-ops setup",
                           ("still template: " + ", ".join(unpers)) if unpers
                           else "cv.md, profile.yml, _profile.md, portals.yml present"))

    # 6) Aside — the only browser Alfred drives (LinkedIn, Indeed, Wellfound, applying).
    aside = shutil.which("aside") or (os.path.expanduser("~/.local/bin/aside")
                                      if os.path.isfile(os.path.expanduser("~/.local/bin/aside")) else None)
    checks.append(("ok" if aside else "warn", "Aside browser",
                   aside or "aside CLI not found — browser sources and portal applying will be "
                            "skipped (install: https://aside.com)"))

    # ---- render ----
    print("Alfred · doctor")
    print("-" * 60)
    for status, label, detail in checks:
        print(f"  {_mark(status)} {label:<18}: {detail}")

    dry = report["dry_run"]
    dry_show = "ON (no real sends/submits)" if dry else ("OFF (LIVE)" if dry is False else "unknown")
    print(f"  •  {'dry_run':<18}: {dry_show}")
    print(f"  {'⛔' if report['paused'] else '▶️ '} {'/pause':<18}: "
          f"{'SET — application-agent halted' if report['paused'] else 'not set'}")
    print("-" * 60)

    has_fail = any(s == "fail" for s, _, _ in checks) or report["paused"]
    if has_fail:
        print("RESULT: NOT READY — resolve the ❌ items above (⚠️ items are advisory).")
        return 1
    warns = [l for s, l, _ in checks if s == "warn"]
    if warns:
        print(f"RESULT: READY ✅  (advisories: {', '.join(warns)})")
    else:
        print("RESULT: READY ✅  — all green.")
    if dry:
        print("  (dry_run is ON — a full pass prepares everything but sends/submits nothing.)")
    return 0


def _importable(mod: str) -> bool:
    try:
        __import__(mod)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# parse-resume
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
_URL_RE = re.compile(r"https?://[^\s)>\]]+", re.IGNORECASE)

_SKILL_KEYWORDS = [
    "python", "java", "javascript", "typescript", "go", "golang", "rust", "ruby",
    "c++", "c#", "php", "scala", "kotlin", "swift", "bash", "shell",
    "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "ansible", "linux",
    "jenkins", "gitlab", "github actions", "ci/cd", "git",
    "sql", "postgresql", "postgres", "mysql", "mongodb", "redis", "kafka",
    "elasticsearch", "spark", "hadoop", "airflow",
    "react", "angular", "vue", "node", "node.js", "django", "flask", "fastapi",
    "spring", "rails", ".net", "graphql", "rest", "grpc",
    "prometheus", "grafana", "datadog", "sre", "devops",
]
_TITLE_KEYWORDS = [
    "software engineer", "senior software engineer", "backend engineer",
    "frontend engineer", "full stack engineer", "full-stack engineer",
    "site reliability engineer", "sre", "devops engineer", "platform engineer",
    "data engineer", "cloud engineer", "systems engineer", "systems administrator",
    "solutions architect", "software architect", "developer", "programmer",
    "engineering manager", "tech lead", "team lead",
]


def read_docx_text(path: str) -> str:
    import docx
    document = docx.Document(path)
    parts = [p.text for p in document.paragraphs]
    for table in document.tables:  # skills often live in tables
        for row in table.rows:
            for cell in row.cells:
                parts.append(cell.text)
    return "\n".join(parts)


def extract_from_resume(text: str) -> Dict[str, Any]:
    """Best-effort structured pull from raw resume text (no invention)."""
    emails = sorted(set(_EMAIL_RE.findall(text)))
    phones = sorted({re.sub(r"\s+", " ", p).strip() for p in _PHONE_RE.findall(text)})
    urls = _URL_RE.findall(text)
    linkedin = next((u for u in urls if "linkedin" in u.lower()), None)
    github = next((u for u in urls if "github" in u.lower()), None)
    portfolio = next((u for u in urls
                      if "linkedin" not in u.lower() and "github" not in u.lower()), None)

    low = text.lower()
    skills = sorted({s for s in _SKILL_KEYWORDS
                     if re.search(rf"(?<![\w+#]){re.escape(s)}(?![\w+#])", low)})
    titles = sorted({t for t in _TITLE_KEYWORDS if t in low})

    # Heuristic name: first short, digit-free, '@'-free line near the top.
    name = None
    for line in text.splitlines()[:8]:
        s = line.strip()
        if s and "@" not in s and not re.search(r"\d", s) and 1 < len(s.split()) <= 4:
            name = s
            break

    return {
        "name": name,
        "emails": emails,
        "phones": phones,
        "linkedin_url": linkedin,
        "github_url": github,
        "portfolio_url": portfolio,
        "skills": skills,
        "titles": titles,
    }


# Fields a resume genuinely cannot supply — these must come from the wizard (SPEC §10.13).
_STILL_NEEDED_ALWAYS = [
    "work_authorization", "notice_period", "availability",
    "salary_expectation", "willing_to_relocate", "remote_preference",
]


def cmd_parse_resume(args: argparse.Namespace) -> int:
    src = os.path.abspath(os.path.expanduser(args.path))
    if not os.path.isfile(src):
        print(f"❌ file not found: {src}")
        return 2
    if not src.lower().endswith(".docx"):
        print(f"❌ expected a .docx resume, got: {src}")
        return 2

    hp = home_paths()
    os.makedirs(hp["data"], exist_ok=True)
    dst = os.path.join(hp["data"], os.path.basename(src))
    if os.path.abspath(src) != os.path.abspath(dst):
        shutil.copy2(src, dst)

    try:
        text = read_docx_text(dst)
    except Exception as exc:
        print(f"❌ could not read resume: {exc}")
        return 1

    extracted = extract_from_resume(text)
    still_needed = list(_STILL_NEEDED_ALWAYS)
    if not extracted["phones"]:
        still_needed.append("personal.phone")
    if not extracted["linkedin_url"]:
        still_needed.append("personal.linkedin_url")

    result = {
        "resume_copied_to": dst,
        "extracted": extracted,
        "still_needed": still_needed,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


# ---------------------------------------------------------------------------
# career-ops + review passthroughs
# ---------------------------------------------------------------------------

def cmd_cv_from_docx(args: argparse.Namespace) -> int:
    import cv_from_docx
    return cv_from_docx.main([args.path, "--out", os.path.join(home_target(), "cv.md")]
                             + (["--force"] if args.force else []))


def cmd_careerops_install(args: argparse.Namespace) -> int:
    import careerops_bridge as cob
    print(f"Installing career-ops @ {cob.PIN[:7]} into {cob.root()} "
          "(downloads from GitHub + npm, ~200 MB with Chromium)…")
    res = cob.install()
    print(json.dumps(res, indent=2))
    if res.get("ok"):
        print(json.dumps(cob.init_templates(), indent=2))
        print(f"house rules → {cob.install_house_rules()}")
    return 0 if res.get("ok") else 1


def cmd_careerops_status(args: argparse.Namespace) -> int:
    import careerops_bridge as cob
    print(json.dumps(cob.status(), indent=2))
    return 0


def cmd_careerops_onboard(args: argparse.Namespace) -> int:
    import careerops_bridge as cob
    with open(args.answers, "r", encoding="utf-8") as fh:
        answers = json.load(fh)
    print(json.dumps(cob.onboard_write(answers, force=args.force, only=args.only), indent=2))
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    import review_store
    cmd = "list" if args.command == "review" else args.command
    argv = [cmd] + ([args.job_id] if getattr(args, "job_id", None) else [])
    if getattr(args, "email", False):
        argv.append("--email")
    return review_store._cli(argv)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alfred",
        description="Alfred setup & health CLI. Secrets enter ONLY via `set-secret` (getpass).")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("bootstrap",
                   help="create the venv + install deps + init (cross-platform, no shell)")
    sub.add_parser("env", help="print the venv's python path for this OS")

    sub.add_parser("init", help="create ~/.alfred/{config,data,output}/ + copy templates")

    p_secret = sub.add_parser("set-secret", help="getpass (hidden) → write KEY into .env")
    p_secret.add_argument("key", help="e.g. TELEGRAM_BOT_TOKEN, GMAIL_ADDRESS, GMAIL_APP_PASSWORD")

    sub.add_parser("doctor", help="full readiness checklist (superset of --preflight)")

    p_resume = sub.add_parser("parse-resume", help="copy resume into data/ + report fields")
    p_resume.add_argument("path", help="path to your master resume .docx")

    p_cv = sub.add_parser("cv-from-docx", help="first cv.md from the resume .docx")
    p_cv.add_argument("path")
    p_cv.add_argument("--force", action="store_true")

    sub.add_parser("careerops-install", help="clone pinned career-ops + npm ci + Chromium")
    sub.add_parser("careerops-status", help="career-ops install / Node / pin")
    p_onb = sub.add_parser("careerops-onboard", help="write config/profile.yml + portals.yml")
    p_onb.add_argument("answers", help="JSON file in onboard-write.mjs's answers shape")
    p_onb.add_argument("--force", action="store_true")
    p_onb.add_argument("--only", choices=["profile", "portals"])

    for name, hlp in (("review", "list jobs waiting for your Approve/Skip"),
                      ("queue", "approved jobs not yet applied"),
                      ("pause", "stop the application agent"),
                      ("resume", "lift /pause")):
        sub.add_parser(name, help=hlp)
    p_ap = sub.add_parser("approve", help="approve a job (add --email to clear its email too)")
    p_ap.add_argument("job_id")
    p_ap.add_argument("--email", action="store_true")
    p_sk = sub.add_parser("skip", help="skip a job")
    p_sk.add_argument("job_id")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    dispatch: Dict[str, Callable[[argparse.Namespace], int]] = {
        "bootstrap": cmd_bootstrap,
        "env": cmd_env,
        "init": cmd_init,
        "set-secret": cmd_set_secret,
        "doctor": cmd_doctor,
        "parse-resume": cmd_parse_resume,
        "cv-from-docx": cmd_cv_from_docx,
        "careerops-install": cmd_careerops_install,
        "careerops-status": cmd_careerops_status,
        "careerops-onboard": cmd_careerops_onboard,
        "review": cmd_review,
        "queue": cmd_review,
        "pause": cmd_review,
        "resume": cmd_review,
        "approve": cmd_review,
        "skip": cmd_review,
    }
    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return 2
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
