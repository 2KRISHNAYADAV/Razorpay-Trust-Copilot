"""
Pydantic v2 schemas for the merchant risk copilot backend.

Field names and types are grounded in:
  - data/scored_cases.json  (one full record inspected)
  - data/flagged_cases.csv  (column names inspected)
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Reason  (one entry in top_reasons)
# ---------------------------------------------------------------------------

class Reason(BaseModel):
    feature: str = Field(..., description="Raw feature name, e.g. 'chargeback_rate_90d'")
    friendly_label: str = Field(..., description="Human-readable label, e.g. 'chargeback rate'")
    value: float = Field(..., description="Feature value for this case")
    impact: float = Field(..., description="SHAP value (signed log-odds impact)")
    direction: Literal["raises risk", "lowers risk"] = Field(
        ..., description="Whether this feature pushes the score up or down"
    )


# ---------------------------------------------------------------------------
# CaseRecord  (one full scored case — stored in memory and returned by API)
# ---------------------------------------------------------------------------

class CaseRecord(BaseModel):
    case_id: str
    merchant_name: str
    mcc_category: str
    risk_score: float = Field(..., ge=0.0, le=1.0)
    decision_tier: Literal["auto_clear", "agent_review", "escalate"]
    ground_truth_label: Literal["fraud", "legitimate"]
    top_reasons: list[Reason]
    plain_language_explanation: str | None = None


# ---------------------------------------------------------------------------
# ScoreRequest  (POST /score body)
#
# The 17 columns that remain after dropping:
#   case_id, merchant_name, archetype, label_is_fraud
#
# Types match the CSV values:
#   - mcc_category              -> str   (categorical)
#   - bank_account_changed_flag -> int   (0 / 1 binary flag)
#   - is_festive_period         -> int   (0 / 1 binary flag)
#   - all others                -> float
# ---------------------------------------------------------------------------

class ScoreRequest(BaseModel):
    mcc_category: str = Field(..., description="Merchant category code label, e.g. 'education'")
    merchant_tenure_days: float = Field(..., ge=0, description="Days since merchant onboarding")
    avg_daily_txn_30d: float = Field(..., ge=0, description="Average daily transaction count (30-day window)")
    volume_spike_ratio: float = Field(..., ge=0, description="Ratio of current volume to 90-day baseline")
    refund_rate_30d: float = Field(..., ge=0, le=1, description="Refund rate over the last 30 days")
    chargeback_rate_90d: float = Field(..., ge=0, le=1, description="Chargeback rate over the last 90 days")
    kyc_completeness_score: float = Field(..., ge=0, le=1, description="KYC document completeness (0-1)")
    bank_account_changed_flag: int = Field(..., ge=0, le=1, description="1 if bank account changed recently")
    days_since_bank_change: float = Field(..., ge=0, description="Days elapsed since last bank account change")
    customer_complaint_count_30d: float = Field(..., ge=0, description="Number of customer complaints (30-day window)")
    device_ip_diversity_score: float = Field(..., ge=0, le=1, description="Diversity of devices/IPs used (0-1)")
    night_txn_ratio: float = Field(..., ge=0, le=1, description="Fraction of transactions occurring at night")
    is_festive_period: int = Field(..., ge=0, le=1, description="1 if transactions fall in a festive period")
    prior_flags_count: float = Field(..., ge=0, description="Number of prior risk flags on this merchant")
    prior_flags_confirmed_fraud: float = Field(..., ge=0, description="Prior flags confirmed as fraud")
    avg_ticket_size: float = Field(..., ge=0, description="Average transaction ticket size (currency units)")
    ticket_size_change_ratio: float = Field(..., ge=0, description="Ratio of current avg ticket to historical baseline")


# ---------------------------------------------------------------------------
# ResolveRequest  (POST /cases/{case_id}/resolve body)
# ---------------------------------------------------------------------------

class ResolveRequest(BaseModel):
    resolved_as: Literal["fraud", "legitimate"] = Field(
        ..., description="Analyst's final verdict for this case"
    )
    notes: str = Field(default="", description="Optional free-text notes from the analyst")

# ---------------------------------------------------------------------------
# AssistantRequest & AssistantResponse  (POST /cases/{case_id}/assistant)
# ---------------------------------------------------------------------------

class AssistantRequest(BaseModel):
    message: str = Field(..., max_length=500, description="The merchant's query")

class AssistantResponse(BaseModel):
    intent: str
    answer: str
    sources: list[str]
    next_actions: list[str]

# ---------------------------------------------------------------------------
# Auth Schemas
# ---------------------------------------------------------------------------
import re
from pydantic import validator

class RequestCodeBody(BaseModel):
    case_id: str

    @validator('case_id')
    def validate_case_id(cls, v):
        v = v.strip()
        if len(v) > 50:
            raise ValueError("Case ID too long")
        return v

class VerifyCodeBody(BaseModel):
    case_id: str
    code: str

    @validator('case_id')
    def validate_case_id(cls, v):
        v = v.strip()
        if len(v) > 50:
            raise ValueError("Case ID too long")
        return v

    @validator('code')
    def validate_code(cls, v):
        v = v.strip()
        if not re.match(r"^\d{6}$", v):
            raise ValueError("Code must be exactly 6 digits")
        return v
