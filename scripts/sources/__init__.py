"""WarmApply source adapters.

Each adapter module exposes `fetch(roles, locations=None, timeout=...) -> list`
returning canonical WarmApply job dicts (read-only). REGISTRY maps the source
name used in `search_order` to its adapter module. Sources listed in config but
absent from REGISTRY are treated as "not implemented yet" and skipped.
"""

from __future__ import annotations

from . import remoteok

# name (as used in config search_order) → adapter module with .fetch(...)
REGISTRY = {
    "remoteok": remoteok,
}
