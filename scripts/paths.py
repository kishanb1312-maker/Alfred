"""WarmApply · paths — the single source of truth for every filesystem path.

Why this module exists
----------------------
WarmApply ships two ways:

  1. **Clone-and-run** (legacy): the whole repo is checked out and both the code and
     the user's data live under the repo root.
  2. **Claude Code plugin** (new): the *code* lives in a managed, read-only plugin dir
     (exposed as ``$CLAUDE_PLUGIN_ROOT``) and the *user's data* lives in the home dir
     (``~/.warmapply`` or ``$WARMAPPLY_HOME``).

Every other script imports from here instead of deriving its own ``_REPO_ROOT`` so both
layouts work with no per-script conditionals.

Two roots
---------
- ``DATA_HOME``  — where the *user's* mutable data lives (configs, resume, output, flags).
      resolution:  $WARMAPPLY_HOME  →  ~/.warmapply (if it exists)  →  repo root
- ``CODE_ROOT``  — where the *bundled, read-only* code + example files live.
      resolution:  $CLAUDE_PLUGIN_ROOT  →  repo root

Under ``DATA_HOME`` the layout is identical in both modes::

    <DATA_HOME>/
      config/   search.yaml, profile.yaml
      data/     <resume>.docx, paused.flag, applied_history.json, approved_queue.json, ...
      output/   tailored per-job artifacts

``.env`` is loaded from ``env_file()`` on import (tiny parser, no hard dependency);
real environment variables always win over values in the file.
"""

from __future__ import annotations

import glob as _glob
import os
from typing import List

# ---------------------------------------------------------------------------
# Roots
# ---------------------------------------------------------------------------

# The repo root = parent of this scripts/ dir. Used as the fallback for BOTH roots
# so a bare clone keeps working exactly as before.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resolve_data_home() -> str:
    """Where the user's mutable data lives.

    $WARMAPPLY_HOME (explicit override, expanded) → ~/.warmapply if it exists →
    else the repo root (backward-compatible clone-and-run).

    NOTE: WARMAPPLY_HOME must be a REAL exported environment variable. It cannot be
    set from a line inside .env, because .env itself is located *inside* DATA_HOME —
    it is not loaded until after this resolution runs, so it can't influence it.
    """
    override = os.environ.get("WARMAPPLY_HOME", "").strip()
    if override:
        return os.path.abspath(os.path.expanduser(override))

    default_home = os.path.join(os.path.expanduser("~"), ".warmapply")
    if os.path.isdir(default_home):
        return default_home

    return _REPO_ROOT


def _resolve_code_root() -> str:
    """Where the bundled, read-only code + example files live.

    $CLAUDE_PLUGIN_ROOT (set by Claude Code inside the plugin) → else the repo root.
    """
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "").strip()
    if plugin_root:
        return os.path.abspath(os.path.expanduser(plugin_root))
    return _REPO_ROOT


DATA_HOME = _resolve_data_home()
CODE_ROOT = _resolve_code_root()


# ---------------------------------------------------------------------------
# Directory helpers (under DATA_HOME)
# ---------------------------------------------------------------------------

def config_dir() -> str:
    return os.path.join(DATA_HOME, "config")


def data_dir() -> str:
    return os.path.join(DATA_HOME, "data")


def output_dir() -> str:
    return os.path.join(DATA_HOME, "output")


# ---------------------------------------------------------------------------
# Config files (under DATA_HOME/config)
# ---------------------------------------------------------------------------

def search_config() -> str:
    return os.path.join(config_dir(), "search.yaml")


def profile_config() -> str:
    return os.path.join(config_dir(), "profile.yaml")


# ---------------------------------------------------------------------------
# Data files & flags (under DATA_HOME/data)
# ---------------------------------------------------------------------------

def resume_glob() -> str:
    return os.path.join(data_dir(), "*.docx")

def resume_matches() -> List[str]:
    return sorted(_glob.glob(resume_glob()))


def pause_flag() -> str:
    return os.path.join(data_dir(), "paused.flag")


def email_paused_flag() -> str:
    return os.path.join(data_dir(), "email_paused.flag")


def applied_history_path() -> str:
    return os.path.join(data_dir(), "applied_history.json")


def approved_queue_path() -> str:
    return os.path.join(data_dir(), "approved_queue.json")


def daily_counts_path() -> str:
    return os.path.join(data_dir(), "daily_counts.json")


def telegram_state_path() -> str:
    # Persists the getUpdates offset (and any future bot state). Name kept exactly
    # as the pre-plugin code used it so existing state is never orphaned.
    return os.path.join(data_dir(), "telegram_state.json")


# ---------------------------------------------------------------------------
# Bundled example files (under CODE_ROOT — read-only, ships with the code)
# ---------------------------------------------------------------------------

def env_file() -> str:
    """The user's real .env (mutable, under DATA_HOME)."""
    return os.path.join(DATA_HOME, ".env")


def env_example() -> str:
    return os.path.join(CODE_ROOT, ".env.example")


def search_example() -> str:
    return os.path.join(CODE_ROOT, "config", "search.example.yaml")


def profile_example() -> str:
    return os.path.join(CODE_ROOT, "config", "profile.example.yaml")


# ---------------------------------------------------------------------------
# .env loading — tiny parser, no hard dependency; real env vars win.
# ---------------------------------------------------------------------------

def load_env(path: str | None = None, *, override: bool = False) -> None:
    """Load KEY=value lines from the .env file into os.environ.

    - No dependency on python-dotenv (keeps requirements minimal / offline-safe).
    - By default an existing real environment variable is NOT overwritten, so an
      explicitly-exported value always wins over the file.
    - Silently no-ops if the file is missing.
    """
    path = path or env_file()
    if not os.path.isfile(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[len("export "):].lstrip()
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                if not key:
                    continue
                value = value.strip()
                # strip matching surrounding quotes
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                    value = value[1:-1]
                if override or key not in os.environ:
                    os.environ[key] = value
    except OSError:
        # Non-fatal: a missing/unreadable .env just means env vars come from the shell.
        return


# Load on import so any script that imports paths.py gets .env populated.
load_env()
