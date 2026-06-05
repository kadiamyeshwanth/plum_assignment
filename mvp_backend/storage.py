"""
In-memory claims store for the Plum OPD Adjudication MVP.
In production this would be replaced by a PostgreSQL / Supabase database.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime


# Simple in-memory store: { claim_id: record }
_store: Dict[str, Dict[str, Any]] = {}


def save_claim(claim_input: Dict[str, Any], result: Dict[str, Any]) -> str:
    """Persist a claim and its adjudication result. Returns the claim_id."""
    claim_id = result.get("claim_id", claim_input.get("case_id", "CLM_UNKNOWN"))
    _store[claim_id] = {
        "claim_id": claim_id,
        "input": claim_input,
        "result": result,
        "submitted_at": datetime.now().isoformat(),
    }
    return claim_id


def get_claim(claim_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a stored claim by ID. Returns None if not found."""
    return _store.get(claim_id)


def list_claims(limit: int = 50) -> List[Dict[str, Any]]:
    """Return the most recent `limit` claims as a list."""
    all_claims = list(_store.values())
    # Sort newest first
    all_claims.sort(key=lambda c: c.get("submitted_at", ""), reverse=True)
    return all_claims[:limit]


def clear_all() -> None:
    """Clear all stored claims (useful for testing)."""
    _store.clear()


def claims_count() -> int:
    return len(_store)
