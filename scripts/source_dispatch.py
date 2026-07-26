"""WarmApply · source_dispatch — run ALL implemented sources, every run.

The Job Finder's deterministic core. Given a `search_order`, it queries EVERY
implemented source in that order (no early stop, NO find-cap), concatenates the
results, then de-dupes so that — on a duplicate — the source appearing FIRST in
`search_order` wins. Blacklisted companies and already-seen jobs are dropped via
scripts/applied_history.py.

Daily caps limit APPLYING (application-agent / daily_caps.py), NOT finding — so
nothing here caps how many jobs are returned.

Behavior:
  - a source name not in the registry  → skipped with a note (no error),
  - a source that raises while fetching → contributes [] and the run continues,
  - de-dupe is order-preserving         → first source in search_order wins a dup.

Pure orchestration + a call into each adapter's fetch(). No network of its own.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import applied_history  # noqa: E402
from sources import REGISTRY  # noqa: E402


def _order_from_config(config: Dict[str, Any]) -> List[str]:
    """search_order takes precedence; fall back to the flat `sources:` list."""
    order = config.get("search_order")
    if isinstance(order, list) and order:
        return [str(s) for s in order]
    sources = config.get("sources")
    if isinstance(sources, list) and sources:
        return [str(s) for s in sources]
    return []


def dispatch(search_order: List[str],
             roles: Optional[List[str]] = None,
             locations: Optional[List[str]] = None,
             blacklist: Optional[List[str]] = None,
             *,
             registry: Optional[Dict[str, Any]] = None,
             history_path: Optional[str] = None,
             timeout: int = 15) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Query every implemented source in order; return (fresh_jobs, report).

    `registry` maps source name → an object with `fetch(roles, locations, timeout)`.
    Defaults to the real REGISTRY; tests inject fakes. `report` records, per source,
    whether it ran / was skipped / errored, and how many it contributed.
    """
    reg = REGISTRY if registry is None else registry
    collected: List[Dict[str, Any]] = []
    report: List[Dict[str, Any]] = []

    for name in search_order:
        adapter = reg.get(name)
        if adapter is None:
            report.append({"source": name, "status": "skipped",
                           "note": "not implemented yet", "count": 0})
            continue
        try:
            fetch: Callable = adapter.fetch if hasattr(adapter, "fetch") else adapter
            jobs = fetch(roles=roles, locations=locations, timeout=timeout) or []
        except Exception as exc:  # one bad source must not break the run
            report.append({"source": name, "status": "error",
                           "error": f"{type(exc).__name__}: {exc}", "count": 0})
            continue
        report.append({"source": name, "status": "ok", "count": len(jobs)})
        collected.extend(jobs)

    # Order-preserving de-dupe (job_id or company+normalized-title) + blacklist +
    # cross-run history. First occurrence — i.e. first source in order — wins.
    kwargs = {"path": history_path} if history_path is not None else {}
    fresh = applied_history.dedupe(collected, blacklist, **kwargs)
    return fresh, report


def search_all(config: Dict[str, Any],
               *,
               registry: Optional[Dict[str, Any]] = None,
               history_path: Optional[str] = None,
               timeout: int = 15) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Convenience wrapper: derive order/roles/locations/blacklist from a config."""
    return dispatch(
        _order_from_config(config),
        roles=config.get("roles"),
        locations=config.get("locations"),
        blacklist=config.get("blacklist_companies"),
        registry=registry,
        history_path=history_path,
        timeout=timeout,
    )
