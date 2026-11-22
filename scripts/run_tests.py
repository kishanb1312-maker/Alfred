#!/usr/bin/env python3
"""Alfred · run_tests — every offline suite in one command.

    ./.venv/bin/python scripts/run_tests.py            all suites
    ./.venv/bin/python scripts/run_tests.py bridge     only suites whose name contains "bridge"

Runs each scripts/dry_run_*.py in its own process (no network, no real sends, no real
history writes), then — when career-ops is installed — its own self-tests for the two
gates Alfred depends on most: the CV fact gate and the repost detector. Prints one line
per suite and exits non-zero if any failed.
"""

from __future__ import annotations

import glob
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _python_suites(pattern: str):
    for path in sorted(glob.glob(os.path.join(HERE, "dry_run_*.py"))):
        name = os.path.basename(path)[len("dry_run_"):-3]
        if pattern in name:
            yield name, [sys.executable, path], None


def _careerops_suites(pattern: str):
    import careerops_bridge as cob
    if cob.unavailable_reason():
        print(f"  •  career-ops self-tests skipped: {cob.unavailable_reason()}")
        return
    for script in ("verify-cv-facts.mjs", "detect-reposts.mjs"):
        name = "careerops:" + script.replace(".mjs", "")
        if pattern in name:
            yield name, ["node", script, "--self-test"], cob.root()


def main(argv) -> int:
    pattern = argv[0] if argv else ""
    results = []
    suites = list(_python_suites(pattern))
    suites += list(_careerops_suites(pattern))
    print(f"Alfred · tests ({len(suites)} suites)")
    print("-" * 60)
    for name, cmd, cwd in suites:
        t0 = time.time()
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=600)
        ok = proc.returncode == 0
        results.append((name, ok))
        print(f"  {'✅' if ok else '❌'} {name:<34} {time.time() - t0:5.1f}s")
        if not ok:
            tail = (proc.stdout + proc.stderr).strip().splitlines()[-12:]
            for line in tail:
                print(f"       {line}")
    failed = [n for n, ok in results if not ok]
    print("-" * 60)
    print(f"RESULT: {'PASS ✅' if not failed else 'FAIL ❌'}  "
          f"{len(results) - len(failed)}/{len(results)} passed"
          + (f"  — failed: {', '.join(failed)}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
