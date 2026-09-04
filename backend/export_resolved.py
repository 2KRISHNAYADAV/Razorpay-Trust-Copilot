"""
export_resolved.py — export analyst-resolved cases to data/retrain_queue.csv.

Usage (from repo root):
    python -m backend.export_resolved               # append mode (default)
    python -m backend.export_resolved --overwrite   # replace existing file

Output columns match data/flagged_cases.csv exactly so the file can be
concatenated with the original training data for retraining:

    type data\\flagged_cases.csv data\\retrain_queue.csv > data\\combined.csv

Column layout
-------------
case_id, merchant_name, mcc_category, archetype,
merchant_tenure_days, avg_daily_txn_30d, volume_spike_ratio,
refund_rate_30d, chargeback_rate_90d, kyc_completeness_score,
bank_account_changed_flag, days_since_bank_change,
customer_complaint_count_30d, device_ip_diversity_score,
night_txn_ratio, is_festive_period, prior_flags_count,
prior_flags_confirmed_fraud, avg_ticket_size, ticket_size_change_ratio,
label_is_fraud

Notes
-----
- `archetype` is not stored in scored_cases.json; it is written as the empty
  string so the row is still importable.  Fill it in manually if you need it
  for stratified retraining.
- `label_is_fraud` is derived from ground_truth_label ("fraud" → 1, else → 0).
- The script writes a header only when creating a new file or in --overwrite
  mode; in append mode it skips the header so the file stays well-formed.
- Re-exporting the same case_id twice will produce a duplicate row (append
  mode).  De-duplicate with pandas before retraining if needed.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Column definitions — must mirror flagged_cases.csv exactly
# ---------------------------------------------------------------------------

# Columns drawn from the case dict (present in scored_cases.json)
_FROM_CASE: list[str] = [
    "case_id",
    "merchant_name",
    "mcc_category",
    # archetype is absent from scored_cases.json; handled separately below
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

# Final ordered column list matching flagged_cases.csv
CSV_COLUMNS: list[str] = [
    "case_id", "merchant_name", "mcc_category", "archetype",
    "merchant_tenure_days", "avg_daily_txn_30d", "volume_spike_ratio",
    "refund_rate_30d", "chargeback_rate_90d", "kyc_completeness_score",
    "bank_account_changed_flag", "days_since_bank_change",
    "customer_complaint_count_30d", "device_ip_diversity_score",
    "night_txn_ratio", "is_festive_period", "prior_flags_count",
    "prior_flags_confirmed_fraud", "avg_ticket_size", "ticket_size_change_ratio",
    "label_is_fraud",
]


# ---------------------------------------------------------------------------
# Mapping helper
# ---------------------------------------------------------------------------

def _case_to_row(case: dict) -> dict:
    """
    Convert a resolved CaseRecord dict to a flat row matching CSV_COLUMNS.

    Fields not present in the case dict (archetype, label_is_fraud) are
    derived or defaulted.
    """
    row: dict = {}

    for col in _FROM_CASE:
        row[col] = case.get(col, "")

    # archetype was not preserved through scoring; leave blank
    row["archetype"] = case.get("archetype", "")

    # ground_truth_label was updated by the analyst via /resolve
    row["label_is_fraud"] = 1 if case.get("ground_truth_label") == "fraud" else 0

    return {col: row[col] for col in CSV_COLUMNS}


# ---------------------------------------------------------------------------
# Main export logic
# ---------------------------------------------------------------------------

def export(output_path: Path, overwrite: bool = False) -> int:
    """
    Pull resolved cases from the in-memory store and write to *output_path*.

    Returns the number of rows written.
    """
    # Import here so the module can also be imported without side-effects
    from backend.store import get_resolved  # noqa: PLC0415

    resolved = get_resolved()
    if not resolved:
        print("No resolved cases to export.", file=sys.stderr)
        return 0

    file_exists = output_path.exists() and output_path.stat().st_size > 0
    write_header = overwrite or not file_exists
    mode = "w" if overwrite else "a"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open(mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if write_header:
            writer.writeheader()
        for case in resolved:
            writer.writerow(_case_to_row(case))

    print(
        f"Exported {len(resolved)} resolved case(s) to {output_path} "
        f"({'overwritten' if overwrite else 'appended'})."
    )
    return len(resolved)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export analyst-resolved cases to data/retrain_queue.csv"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data" / "retrain_queue.csv",
        help="Destination CSV file (default: data/retrain_queue.csv)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the output file instead of appending to it",
    )
    args = parser.parse_args()

    n = export(args.output, overwrite=args.overwrite)
    sys.exit(0 if n >= 0 else 1)


if __name__ == "__main__":
    main()
