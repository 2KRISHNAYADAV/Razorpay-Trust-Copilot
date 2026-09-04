"""
main.py — FastAPI application for the merchant risk copilot.

Endpoints (all spec'd in README.md):
  GET  /health
  GET  /cases?tier=<optional>&sort=<optional>
  GET  /cases/resolved
  GET  /cases/{case_id}
  POST /score
  POST /cases/{case_id}/resolve

CORS is enabled for all origins (hackathon, not production).
"""

from __future__ import annotations

import sys
from pathlib import Path

# When `uvicorn main:app` is run from inside backend/, the backend/ directory
# is on sys.path but the repo root is not.  Add the repo root so that
# scoring.py / store.py can resolve paths like "model/risk_model.json" and
# "data/scored_cases.json" via _REPO_ROOT = Path(__file__).parent.parent.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_BACKEND_DIR = Path(__file__).resolve().parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

import agent
import store
import auth
from fastapi import Depends, Request, Response
from schemas import CaseRecord, ResolveRequest, ScoreRequest, RequestCodeBody, VerifyCodeBody
from scoring import score_case

# ---------------------------------------------------------------------------
# App + CORS
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Merchant Risk Copilot",
    description="Explainable, tiered merchant fraud-risk scoring API.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# POST /auth/case/request-code
# ---------------------------------------------------------------------------
@app.post("/auth/case/request-code", tags=["auth"])
def request_verification_code(body: RequestCodeBody) -> dict:
    # Do not check if case_id actually exists to prevent enumeration!
    # Just pretend it's all good, unless there's a rate limit block.
    auth.request_verification_code(body.case_id)
    return {"message": "Verification challenge created."}

# ---------------------------------------------------------------------------
# POST /auth/case/verify
# ---------------------------------------------------------------------------
@app.post("/auth/case/verify", tags=["auth"])
def verify_code(body: VerifyCodeBody, response: Response) -> dict:
    # Verifies the code, throws 401/429 if bad
    session_token = auth.verify_code(body.case_id, body.code)
    
    response.set_cookie(
        key=auth.SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        secure=False,    # Disabled for localhost/http testing
        samesite="lax",  # Requirement: SameSite
        max_age=auth.SESSION_DURATION_SEC
    )
    return {"authenticated": True, "session_expires_in": auth.SESSION_DURATION_SEC}

# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------
@app.post("/auth/logout", tags=["auth"])
def logout(request: Request, response: Response) -> dict:
    token = request.cookies.get(auth.SESSION_COOKIE_NAME)
    if token:
        auth.invalidate_session(token)
    response.delete_cookie(auth.SESSION_COOKIE_NAME)
    return {"message": "Logged out successfully."}

# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

@app.get("/health", tags=["meta"])
def health() -> dict:
    """Liveness check — returns 200 when the service is up."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# GET /cases?tier=&sort=
# ---------------------------------------------------------------------------

@app.get("/cases", response_model=list[CaseRecord], tags=["cases"])
def list_cases(
    tier: str | None = Query(
        default=None,
        description="Filter by decision_tier: auto_clear | agent_review | escalate",
    ),
    sort: str = Query(
        default="risk_score",
        description="Top-level field to sort by (descending). Default: risk_score",
    ),
) -> list[dict]:
    """
    Return all pre-scored cases, optionally filtered by tier, sorted descending.
    This is the ops-console table endpoint.
    """
    return store.get_all(tier=tier, sort_by=sort)


# ---------------------------------------------------------------------------
# GET /cases/resolved   — must be declared BEFORE /cases/{case_id}
# ---------------------------------------------------------------------------

@app.get("/cases/resolved", response_model=list[CaseRecord], tags=["cases"])
def list_resolved() -> list[dict]:
    """Return every case resolved by an analyst since server startup."""
    return store.get_resolved()


# ---------------------------------------------------------------------------
# GET /cases/{case_id}
# ---------------------------------------------------------------------------

@app.get("/cases/{case_id}", response_model=CaseRecord, tags=["cases"])
def get_case(case_id: str) -> dict:
    """
    Return one case's full record including plain_language_explanation.
    """

    case = store.get_by_id(case_id)
    if case is None:
        raise HTTPException(status_code=401, detail="Unable to verify the information provided.")

    # Attach the explanation (mutate a copy so the store isn't polluted)
    result = dict(case)
    result["plain_language_explanation"] = agent.draft_explanation(case)
    return result


# ---------------------------------------------------------------------------
# POST /score
# ---------------------------------------------------------------------------

@app.post("/score", response_model=CaseRecord, tags=["scoring"])
def score(request: ScoreRequest) -> dict:
    """
    Live-score a merchant using the loaded XGBoost model + SHAP explainer.
    Body is the 16 raw numeric features (plus mcc_category).
    Returns a record in the same shape as a scored_cases.json entry.
    """
    features = request.model_dump()
    result = score_case(features)

    # Add caller-supplied metadata fields that score_case leaves for the caller
    result["case_id"] = "LIVE"
    result["merchant_name"] = "Live Score Request"
    result["mcc_category"] = features.get("mcc_category", "unknown")

    # Generate plain-language explanation for the live result
    result["plain_language_explanation"] = agent.draft_explanation(result)

    return result


# ---------------------------------------------------------------------------
# POST /cases/{case_id}/resolve
# ---------------------------------------------------------------------------

@app.post("/cases/{case_id}/resolve", response_model=CaseRecord, tags=["cases"])
def resolve_case(case_id: str, body: ResolveRequest) -> dict:
    """
    Record an analyst's verdict for a case.
    Updates ground_truth_label in-memory and returns the updated record.
    """
    updated = store.update_resolution(
        case_id=case_id,
        resolved_as=body.resolved_as,
        notes=body.notes,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id!r} not found.")

    result = dict(updated)
    result["plain_language_explanation"] = agent.draft_explanation(updated)
    return result


# ---------------------------------------------------------------------------
# POST /cases/{case_id}/assistant
# ---------------------------------------------------------------------------

import time
from schemas import AssistantRequest, AssistantResponse

RATE_LIMITS = {}

@app.post("/cases/{case_id}/assistant", response_model=AssistantResponse, tags=["cases"])
def ask_assistant(case_id: str, request: AssistantRequest) -> dict:
    """Ask the Trust Assistant a question about a specific case."""
    
    now = time.time()
    
    if case_id not in RATE_LIMITS:
        RATE_LIMITS[case_id] = {"count": 0, "history": []}
        
    stats = RATE_LIMITS[case_id]
    if stats["count"] >= 20:
        raise HTTPException(status_code=429, detail="Maximum 20 questions per case reached.")
        
    # Clean up history older than 60 seconds
    stats["history"] = [t for t in stats["history"] if now - t < 60]
    
    if len(stats["history"]) >= 5:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait a minute.")
        
    case = store.get_by_id(case_id)
    if case is None:
        raise HTTPException(status_code=401, detail="Unable to verify the information provided.")
        
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Empty message.")
        
    stats["count"] += 1
    stats["history"].append(now)
    
    ans_data = agent.handle_merchant_query(case, request.message[:500].strip())
    ans_data["case_id"] = case_id
    return ans_data



# ---------------------------------------------------------------------------
# Static frontend — mounted LAST so all API routes take priority
# ---------------------------------------------------------------------------

from fastapi.staticfiles import StaticFiles  # noqa: E402

_FRONTEND_DIR = _REPO_ROOT / "frontend"
if _FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")
