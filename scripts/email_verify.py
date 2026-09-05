"""Alfred · email_verify — syntax + MX verification + pattern generation.

Used by the company-research agent's email waterfall. Every candidate address
MUST pass verification before it is accepted (guardrail: no unverified sends).

Dependencies (already in requirements.txt): email-validator, dnspython.

Network boundary:
  - verify_syntax()      → pure, offline (no DNS).
  - generate_patterns()  → pure, offline.
  - verify_mx()          → performs a DNS lookup (network).
  - verify(check_mx=...) → set check_mx=False for a fully offline check
                            (e.g. the dry-run). Then `mx` is None ("skipped").

Public API (per the company-research definition):
    - verify_syntax(email) -> bool
    - verify_mx(domain) -> bool
    - verify(email, check_mx=True) -> dict   # {syntax, mx, ok}
    - generate_patterns(first, last, domain) -> list[str]
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from email_validator import EmailNotValidError, validate_email

try:  # dnspython is only needed for the (network) MX check.
    import dns.resolver  # type: ignore
    _HAVE_DNS = True
except ImportError:  # pragma: no cover - dnspython listed in requirements.txt
    _HAVE_DNS = False


# ---------------------------------------------------------------------------
# Syntax (offline)
# ---------------------------------------------------------------------------

def verify_syntax(email: str) -> bool:
    """True if `email` is syntactically valid. No DNS/deliverability check."""
    if not email:
        return False
    try:
        validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


# ---------------------------------------------------------------------------
# MX (network)
# ---------------------------------------------------------------------------

def verify_mx(domain: str) -> bool:
    """True if `domain` has a usable mail exchanger. Performs a DNS lookup.

    Falls back to an A/AAAA record (RFC 5321 §5.1: a host with an address record
    but no MX may still receive mail). Any resolution failure → False.
    """
    if not domain:
        return False
    if not _HAVE_DNS:
        raise RuntimeError("dnspython not installed; cannot run verify_mx()")
    try:
        answers = dns.resolver.resolve(domain, "MX")
        return len(answers) > 0
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        # No MX — try an address record as a last resort.
        for rrtype in ("A", "AAAA"):
            try:
                if len(dns.resolver.resolve(domain, rrtype)) > 0:
                    return True
            except Exception:
                continue
        return False
    except Exception:
        # Timeout, no nameservers, etc. — treat as unverifiable.
        return False


# ---------------------------------------------------------------------------
# Combined
# ---------------------------------------------------------------------------

def verify(email: str, check_mx: bool = True) -> Dict[str, object]:
    """Verify `email`. Returns {syntax, mx, ok}.

    - `syntax`: bool from verify_syntax().
    - `mx`: bool if the MX check ran, else None (skipped — offline mode).
    - `ok`: True only if every check that ran passed. When check_mx is False,
      `ok` reflects syntax alone (the MX check was not performed).
    """
    syntax = verify_syntax(email)
    mx: Optional[bool]
    if check_mx and syntax:
        domain = email.rsplit("@", 1)[-1]
        mx = verify_mx(domain)
    else:
        mx = None  # skipped (offline) or moot (bad syntax)

    if check_mx:
        ok = bool(syntax and mx)
    else:
        ok = bool(syntax)
    return {"syntax": syntax, "mx": mx, "ok": ok}


# ---------------------------------------------------------------------------
# Pattern generation (offline)
# ---------------------------------------------------------------------------

def _clean(part: str) -> str:
    """Lowercase and strip anything that isn't a local-part-safe char."""
    return re.sub(r"[^a-z0-9]", "", (part or "").strip().lower())


def generate_patterns(first: str, last: str, domain: str) -> List[str]:
    """Common corporate email patterns for a person, most-likely first.

    Each candidate should still be passed through verify() before it is used.
    Returns a de-duplicated, order-preserving list.
    """
    f = _clean(first)
    l = _clean(last)
    d = (domain or "").strip().lower().lstrip("@")
    if not d or not (f or l):
        return []

    locals_: List[str] = []
    fi = f[:1]
    li = l[:1]

    if f and l:
        locals_ += [
            f"{f}.{l}",     # first.last
            f"{f}{l}",      # firstlast
            f"{fi}{l}",     # flast
            f"{fi}.{l}",    # f.last
            f"{f}_{l}",     # first_last
            f"{f}-{l}",     # first-last
            f"{f}{li}",     # firstl
            f"{l}.{f}",     # last.first
            f"{l}{f}",      # lastfirst
        ]
    if f:
        locals_.append(f)   # first
    if l:
        locals_.append(l)   # last

    seen = set()
    out: List[str] = []
    for local in locals_:
        addr = f"{local}@{d}"
        if addr not in seen:
            seen.add(addr)
            out.append(addr)
    return out


def best_pattern(first: str, last: str, domain: str) -> Optional[str]:
    """The SINGLE most-likely guessed address (`first.last@domain`), or None.

    Used as the last-resort fallback in the email waterfall: Alfred guesses ONE
    address only (never blasts multiple guesses). The caller MUST still MX-verify the
    domain before accepting it (see `best_guess`). Returns None if inputs are too thin.
    """
    patterns = generate_patterns(first, last, domain)
    return patterns[0] if patterns else None


def best_guess(first: str, last: str, domain: str,
               check_mx: bool = True) -> Dict[str, object]:
    """Produce the single best pattern-guess and gate it on the domain's MX.

    Returns {email, verified_mailbox, mx, source}. `verified_mailbox` is always
    False for a guess (no finder confirmed a real mailbox). `email` is None if the
    guess can't be formed or (when check_mx) the domain has no valid MX — we never
    keep a guess whose domain can't receive mail, and never fabricate a domain.
    Set check_mx=False for a fully offline call (then `mx` is None).
    """
    candidate = best_pattern(first, last, domain)
    if not candidate:
        return {"email": None, "verified_mailbox": False, "mx": None, "source": "none"}

    dom = candidate.rsplit("@", 1)[-1]
    mx_ok: Optional[bool] = verify_mx(dom) if check_mx else None
    if check_mx and not mx_ok:
        return {"email": None, "verified_mailbox": False, "mx": False, "source": "none"}
    return {"email": candidate, "verified_mailbox": False, "mx": mx_ok, "source": "pattern"}
