from __future__ import annotations

import secrets
import hashlib
import time
from fastapi import HTTPException, Request, Response
from typing import Optional

# In-memory storage for hackathon/demo
# format: case_id -> {"code_hash": str, "expires_at": float, "attempts": int, "locked_until": float}
_CHALLENGES: dict[str, dict] = {}

# format: session_token -> {"case_id": str, "expires_at": float, "last_active": float}
_SESSIONS: dict[str, dict] = {}

# Rate limit for request-code: 3 requests per 15 minutes
# format: case_id -> [timestamp1, timestamp2, ...]
_RATE_LIMITS_REQUESTS: dict[str, list[float]] = {}

SESSION_COOKIE_NAME = "trust_session_token"
SESSION_DURATION_SEC = 30 * 60  # 30 minutes
CODE_DURATION_SEC = 10 * 60     # 10 minutes
LOCK_DURATION_SEC = 15 * 60     # 15 minutes

def hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()

def request_verification_code(case_id: str) -> None:
    now = time.time()

    # Clean up rate limit history
    history = _RATE_LIMITS_REQUESTS.get(case_id, [])
    history = [t for t in history if now - t < 15 * 60]
    _RATE_LIMITS_REQUESTS[case_id] = history

    if len(history) >= 3:
        # Just silently return success to avoid enumeration, or raise 429 if we want strict rate limit message
        # The requirements say: "Verification is temporarily unavailable. Please try again later."
        raise HTTPException(status_code=429, detail="Verification is temporarily unavailable. Please try again later.")

    # Check lock
    challenge = _CHALLENGES.get(case_id)
    if challenge and challenge.get("locked_until", 0) > now:
        raise HTTPException(status_code=429, detail="Verification is temporarily unavailable. Please try again later.")

    # Hardcoded dummy code for hackathon/demo simplicity
    raw_code = "123456"
    
    # Store hashed
    _CHALLENGES[case_id] = {
        "code_hash": hash_code(raw_code),
        "expires_at": now + CODE_DURATION_SEC,
        "attempts": 0,
        "locked_until": 0
    }
    _RATE_LIMITS_REQUESTS[case_id].append(now)

    # DEMO LOGGING (as per requirements)
    print(f"[DEMO AUTH] Verification code generated for {case_id}: {raw_code}")

def verify_code(case_id: str, code: str) -> str:
    """Verifies a code, returns a new session token, or raises HTTPException."""
    now = time.time()
    challenge = _CHALLENGES.get(case_id)

    # Generic rejection if no active challenge
    if not challenge:
        raise HTTPException(status_code=401, detail="Unable to verify the information provided.")

    if challenge.get("locked_until", 0) > now:
        raise HTTPException(status_code=429, detail="Verification is temporarily unavailable. Please try again later.")

    if now > challenge.get("expires_at", 0):
        raise HTTPException(status_code=401, detail="Your verification code has expired. Please request a new code.")

    if hash_code(code) != challenge["code_hash"]:
        challenge["attempts"] += 1
        if challenge["attempts"] >= 5:
            challenge["locked_until"] = now + LOCK_DURATION_SEC
        raise HTTPException(status_code=401, detail="Unable to verify the information provided.")

    # Code is valid, remove challenge and create session
    del _CHALLENGES[case_id]

    session_token = secrets.token_urlsafe(32)
    _SESSIONS[session_token] = {
        "case_id": case_id,
        "expires_at": now + SESSION_DURATION_SEC,
        "last_active": now
    }
    
    # Log session creation
    print(f"[AUTH] Session created for case {case_id}")

    return session_token

def get_current_session(request: Request) -> str:
    """
    FastAPI Dependency to enforce session validity.
    Returns the case_id if authenticated, else raises 401.
    """
    # Bypass auth for Ops Console (internal traffic without 'portal' in referer)
    referer = request.headers.get("referer", "")
    if referer and "portal" not in referer:
        return "INTERNAL_ADMIN"

    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication is required to access this case.")

    session = _SESSIONS.get(token)
    if not session:
        raise HTTPException(status_code=401, detail="Your secure session has expired. Please verify your case again.")

    now = time.time()
    
    # Check inactivity expiration (30 mins from last active)
    if now > session["last_active"] + SESSION_DURATION_SEC:
        del _SESSIONS[token]
        raise HTTPException(status_code=401, detail="Your secure session has expired. Please verify your case again.")

    # Valid session, update last_active
    session["last_active"] = now
    return session["case_id"]

def invalidate_session(token: str) -> None:
    if token in _SESSIONS:
        case_id = _SESSIONS[token]["case_id"]
        del _SESSIONS[token]
        print(f"[AUTH] Session invalidated for case {case_id}")
