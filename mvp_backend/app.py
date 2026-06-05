"""
Plum OPD Adjudication API — FastAPI Application
"""
from fastapi import FastAPI, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from typing import Any, Dict, List, Optional
from datetime import datetime

from models import ClaimRequest, AdjudicationResult
from decision_engine import adjudicate
from extractor import extract_documents
from storage import save_claim, get_claim, list_claims, claims_count

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Plum OPD Adjudication API",
    description=(
        "AI-powered OPD insurance claim adjudication engine. "
        "Validates documents, checks policy rules, and makes approval/rejection decisions."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow the static frontend (and any local dev origin) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Restrict to your domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"])
def health_check():
    """Simple liveness probe."""
    return {
        "status": "ok",
        "service": "Plum OPD Adjudication API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "total_claims_processed": claims_count(),
    }


@app.post("/adjudicate", tags=["Claims"])
def adjudicate_claim(claim: ClaimRequest) -> Dict[str, Any]:
    """
    Submit an OPD claim for adjudication.

    The engine runs a 5-step evaluation:
    1. Document validation
    2. Waiting period checks
    3. Coverage verification
    4. Limit validation
    5. Fraud / medical necessity review

    Returns a structured decision with approval amount, reasons, and next steps.
    """
    payload = claim.dict()

    # Extract & validate documents (mock OCR/LLM layer)
    enriched_docs = extract_documents(payload)
    payload["documents"] = enriched_docs

    # Run adjudication
    result = adjudicate(payload)

    # Persist to store
    save_claim(claim.dict(), result)

    return result


@app.get("/claims", tags=["Claims"])
def list_all_claims(limit: int = Query(default=20, ge=1, le=100)) -> Dict[str, Any]:
    """
    Retrieve the most recent claims with their adjudication results.
    Useful for building a claims dashboard.
    """
    claims = list_claims(limit=limit)
    return {
        "total": claims_count(),
        "returned": len(claims),
        "claims": claims,
    }


@app.get("/claims/{claim_id}", tags=["Claims"])
def get_claim_by_id(
    claim_id: str = Path(..., description="The claim ID to retrieve (e.g. CLM_TEST)")
) -> Dict[str, Any]:
    """Retrieve a specific claim and its decision by claim ID."""
    record = get_claim(claim_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found.")
    return record


@app.get("/policy", tags=["Policy"])
def get_policy_summary() -> Dict[str, Any]:
    """Return a summary of the active policy terms (read-only)."""
    import json, os
    policy_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "policy_terms.json")
    )
    with open(policy_path, "r", encoding="utf-8") as f:
        policy = json.load(f)
    # Return a simplified view
    coverage = policy.get("coverage_details", {})
    return {
        "policy_id": policy.get("policy_id"),
        "policy_name": policy.get("policy_name"),
        "annual_limit": coverage.get("annual_limit"),
        "per_claim_limit": coverage.get("per_claim_limit"),
        "covered_categories": [k for k, v in coverage.items() if isinstance(v, dict) and v.get("covered", True)],
        "exclusions": policy.get("exclusions", []),
        "network_hospitals": policy.get("network_hospitals", []),
        "submission_deadline_days": policy.get("claim_requirements", {}).get("submission_timeline_days"),
        "minimum_claim_amount": policy.get("claim_requirements", {}).get("minimum_claim_amount"),
    }
