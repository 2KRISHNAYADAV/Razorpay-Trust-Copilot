"""
scoring.py — model inference and SHAP explanation, loaded once at import time.

The XGBoost model was trained on 16 numeric features (mcc_category is excluded
from the model; it is metadata only). The SHAP TreeExplainer is built directly
from the loaded model.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import shap
import xgboost as xgb

# ---------------------------------------------------------------------------
# Paths (relative to the repo root, not this file)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent
_MODEL_PATH = _REPO_ROOT / "model" / "risk_model.json"

# ---------------------------------------------------------------------------
# Feature order — must match exactly what the model was trained on
# (notebook cell 9 / FEATURES list)
# ---------------------------------------------------------------------------

FEATURES: list[str] = [
    "merchant_tenure_days",
    "avg_daily_txn_30d",
    "volume_spike_ratio",
    "refund_rate_30d",
    "chargeback_rate_90d",
    "kyc_completeness_score",
    "bank_account_changed_flag",
    "days_since_bank_change",
    "customer_complaint_count_30d",
    "device_ip_diversity_score",
    "night_txn_ratio",
    "is_festive_period",
    "prior_flags_count",
    "prior_flags_confirmed_fraud",
    "avg_ticket_size",
    "ticket_size_change_ratio",
]

# ---------------------------------------------------------------------------
# Friendly labels — exact copy from notebook cell 21
# ---------------------------------------------------------------------------

FRIENDLY_NAMES: dict[str, str] = {
    "merchant_tenure_days": "account age",
    "avg_daily_txn_30d": "baseline transaction volume",
    "volume_spike_ratio": "sudden change in transaction volume",
    "refund_rate_30d": "refund rate",
    "chargeback_rate_90d": "chargeback rate",
    "kyc_completeness_score": "KYC document completeness",
    "bank_account_changed_flag": "recent payout account change",
    "days_since_bank_change": "time since payout account change",
    "customer_complaint_count_30d": "customer complaint volume",
    "device_ip_diversity_score": "device/IP diversity across transactions",
    "night_txn_ratio": "share of transactions at unusual hours",
    "is_festive_period": "seasonal sale period",
    "prior_flags_count": "number of past risk flags",
    "prior_flags_confirmed_fraud": "past flags confirmed as fraud",
    "avg_ticket_size": "average transaction size",
    "ticket_size_change_ratio": "change in typical transaction size",
}

# ---------------------------------------------------------------------------
# Load model + explainer once at import time
#
# XGBoost 3.x raises TypeError when calling .load_model() on a bare
# XGBClassifier() because _estimator_type is not set yet.  Loading via
# xgb.Booster avoids the sklearn wrapper entirely and works identically
# with shap.TreeExplainer.
# ---------------------------------------------------------------------------

_booster = xgb.Booster()
_booster.load_model(str(_MODEL_PATH))

_explainer = shap.TreeExplainer(_booster)

# ---------------------------------------------------------------------------
# Decision tier thresholds
# ---------------------------------------------------------------------------

def _decision_tier(risk_score: float) -> str:
    if risk_score < 0.20:
        return "auto_clear"
    if risk_score < 0.70:
        return "agent_review"
    return "escalate"


# ---------------------------------------------------------------------------
# score_case
# ---------------------------------------------------------------------------

def score_case(features: dict) -> dict:
    """
    Run the model and SHAP on a single feature dict.

    `features` must contain all keys in FEATURES (plus optionally mcc_category
    and other metadata fields, which are silently ignored here).

    Returns a dict that matches CaseRecord from schemas.py — but *without*
    case_id, merchant_name, mcc_category, and plain_language_explanation.
    The caller is responsible for adding those fields.
    """
    # Build a one-row DataFrame in the exact feature order the model expects
    row = pd.DataFrame([{f: features[f] for f in FEATURES}])

    # Predict probability of fraud (class 1).
    # Booster.predict() on a binary classifier returns the sigmoid output
    # directly (equivalent to predict_proba[:, 1]).
    dmat = xgb.DMatrix(row)
    risk_score: float = round(float(_booster.predict(dmat)[0]), 4)
    tier: str = _decision_tier(risk_score)

    # SHAP values — shape (1, n_features) for tree explainer on binary classifier
    shap_values = _explainer.shap_values(row)
    # Some XGBoost versions return a list [neg, pos]; take pos class
    if isinstance(shap_values, list):
        contribs = shap_values[1][0]
    else:
        contribs = shap_values[0]

    # Top 3 features by absolute SHAP impact
    order = np.argsort(-np.abs(contribs))[:3]
    top_reasons = [
        {
            "feature": FEATURES[f_idx],
            "friendly_label": FRIENDLY_NAMES[FEATURES[f_idx]],
            "value": round(float(row.iloc[0][FEATURES[f_idx]]), 6),
            "impact": round(float(contribs[f_idx]), 4),
            "direction": "raises risk" if contribs[f_idx] > 0 else "lowers risk",
        }
        for f_idx in order
    ]

    return {
        "risk_score": risk_score,
        "decision_tier": tier,
        "top_reasons": top_reasons,
        # ground_truth_label is unknown at live-score time; caller can set it
        "ground_truth_label": "legitimate",
    }


# ---------------------------------------------------------------------------
# Quick smoke-test (run as __main__)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json

    df = pd.read_csv(_REPO_ROOT / "data" / "flagged_cases.csv")
    sample = df.iloc[0]

    print(f"Running score_case on: {sample['case_id']} ({sample['merchant_name']})")
    print(f"Ground truth label   : {'fraud' if sample['label_is_fraud'] == 1 else 'legitimate'}\n")

    result = score_case(sample.to_dict())

    # Augment with metadata so it looks like a full CaseRecord
    result["case_id"] = sample["case_id"]
    result["merchant_name"] = sample["merchant_name"]
    result["mcc_category"] = sample["mcc_category"]

    print(json.dumps(result, indent=2))
