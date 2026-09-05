"""Alfred source adapters.

Each adapter module exposes `fetch(roles, locations=None, timeout=...) -> list`
returning canonical Alfred job dicts (read-only). REGISTRY maps the source
name used in `search_order` to its adapter module. Sources listed in config but
absent from REGISTRY are treated as "not implemented yet" and skipped.
"""

from __future__ import annotations

from . import remoteok
from . import weworkremotely
from . import jobspresso
from . import wellfound
from . import indeed
from . import greenhouse_lever
from . import linkedin_feed

# name (as used in config search_order) → adapter module.
# Python (API/RSS) sources expose fetch(...); BROWSER sources (BROWSER=True) expose
# only a pure normalize(...) and are driven by the job-finder subagent, not dispatch.
REGISTRY = {
    "remoteok": remoteok,
    "we_work_remotely": weworkremotely,
    "jobspresso": jobspresso,
    "wellfound": wellfound,
    "indeed": indeed,
    "greenhouse_lever": greenhouse_lever,
    "linkedin_feed": linkedin_feed,
}
