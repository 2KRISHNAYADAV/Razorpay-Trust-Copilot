"""
store.py — in-memory case store, loaded once at import time.

Data source: data/scored_cases.json (2 000 pre-scored CaseRecord dicts).

Public API
----------
get_all(tier, sort_by)   -> list[dict]
get_by_id(case_id)       -> dict | None
update_resolution(...)   -> dict | None
get_resolved()           -> list[dict]
"""

from __future__ import annotations

import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DATA_PATH = _REPO_ROOT / "data" / "scored_cases.json"

# ---------------------------------------------------------------------------
# Load data once at import time
#
# Each element is a plain dict that matches CaseRecord from schemas.py.
# We store them in a list AND in an index dict for O(1) lookup by case_id.
# ---------------------------------------------------------------------------

with _DATA_PATH.open(encoding="utf-8") as _f:
    _cases: list[dict] = json.load(_f)

# Primary index: case_id -> dict (same object as in _cases)
_index: dict[str, dict] = {c["case_id"]: c for c in _cases}

# Secondary index: case_ids that have been resolved since startup
_resolved_ids: set[str] = set()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_all(
    tier: str | None = None,
    sort_by: str = "risk_score",
) -> list[dict]:
    """
    Return all cases, optionally filtered by decision_tier, sorted descending.

    Parameters
    ----------
    tier:    If given, only cases whose decision_tier equals this value are
             returned.  Pass None (default) to return every case.
    sort_by: Key to sort by (descending).  Must be a top-level key present in
             every case dict.  Defaults to "risk_score".
    """
    results = _cases if tier is None else [c for c in _cases if c["decision_tier"] == tier]
    return sorted(results, key=lambda c: c.get(sort_by, 0), reverse=True)


def get_by_id(case_id: str) -> dict | None:
    """Return the case dict for *case_id*, or None if not found."""
    return _index.get(case_id)


def update_resolution(case_id: str, resolved_as: str, notes: str) -> dict | None:
    """
    Update a case's ground_truth_label in-memory and store the analyst's notes.

    Returns the updated case dict, or None if case_id is not found.

    The update is **in-memory only** — it survives for the lifetime of the
    running process but is not persisted back to disk.
    """
    case = _index.get(case_id)
    if case is None:
        return None

    case["ground_truth_label"] = resolved_as
    case["notes"] = notes          # new field added only after resolution
    _resolved_ids.add(case_id)
    return case


def get_resolved() -> list[dict]:
    """Return every case that has been updated via update_resolution."""
    return [_index[cid] for cid in _resolved_ids if cid in _index]


# ---------------------------------------------------------------------------
# Quick smoke-test (run as __main__)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    agent_review = get_all(tier="agent_review")
    print(f"agent_review cases : {len(agent_review)}")

    auto_clear = get_all(tier="auto_clear")
    print(f"auto_clear cases   : {len(auto_clear)}")

    escalate = get_all(tier="escalate")
    print(f"escalate cases     : {len(escalate)}")

    print(f"total loaded       : {len(_cases)}")

    # Verify sort order (highest risk_score first)
    print(f"\nTop risk_score     : {agent_review[0]['risk_score']}")
    print(f"Bottom risk_score  : {agent_review[-1]['risk_score']}")

    # Exercise get_by_id
    first_id = agent_review[0]["case_id"]
    found = get_by_id(first_id)
    print(f"\nget_by_id({first_id!r}) -> {found['merchant_name']}")

    # Exercise update_resolution + get_resolved
    update_resolution(first_id, resolved_as="fraud", notes="Confirmed via manual review")
    resolved = get_resolved()
    print(f"\nResolved cases     : {len(resolved)}")
    print(f"  {resolved[0]['case_id']} -> ground_truth_label={resolved[0]['ground_truth_label']!r}")
    print(f"  notes={resolved[0]['notes']!r}")
