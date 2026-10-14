#!/usr/bin/env python3

import argparse
from pathlib import Path

import pandas as pd


def safe_read_csv(path):
    path = Path(path)

    if not path.exists():
        return pd.DataFrame()

    return pd.read_csv(path)


def merge_reason(existing_reason, new_reason):
    if pd.isna(existing_reason) or str(existing_reason).strip() == "":
        return new_reason

    if new_reason in str(existing_reason):
        return str(existing_reason)

    return str(existing_reason) + " | " + new_reason


def update_condition_decision(row):
    session_status = row.get("session_status")
    current_decision = row.get("condition_curation_decision")
    current_reason = row.get("condition_curation_reason")

    if session_status == "fail":
        row["condition_curation_decision"] = "reject"
        row["condition_curation_reason"] = merge_reason(
            current_reason,
            "Session validation failed."
        )
        return row

    if session_status == "review":
        if current_decision != "reject":
            row["condition_curation_decision"] = "review"

        row["condition_curation_reason"] = merge_reason(
            current_reason,
            "Session validation requires review."
        )

    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir", help="Data directory, usually: data")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)

    session_path = data_dir / "session_validation_summary.csv"
    condition_path = data_dir / "final_condition_curation_report.csv"

    session_df = safe_read_csv(session_path)
    condition_df = safe_read_csv(condition_path)

    if session_df.empty:
        raise FileNotFoundError(
            "Missing or empty session_validation_summary.csv. "
            "Run validate_all_sessions.py first."
        )

    if condition_df.empty:
        raise FileNotFoundError(
            "Missing or empty final_condition_curation_report.csv. "
            "Run final_curation_report.py first."
        )

    keep_session_cols = [
        "participant_id",
        "condition",
        "session_status",
        "bag_exists",
        "bag_duration_seconds",
        "total_messages",
        "num_required_topics_present",
        "num_required_topics",
        "missing_required_topics",
        "events_status",
        "num_event_trials",
        "video_status",
        "missing_required_videos",
        "missing_optional_videos",
        "issues",
        "review_reasons",
    ]

    keep_session_cols = [
        col for col in keep_session_cols
        if col in session_df.columns
    ]

    session_small = session_df[keep_session_cols].copy()

    # Rename session issue columns so they do not overwrite condition issue columns.
    rename_map = {
        "issues": "session_issues",
        "review_reasons": "session_review_reasons",
    }

    session_small = session_small.rename(columns=rename_map)

    merged = condition_df.merge(
        session_small,
        on=["participant_id", "condition"],
        how="left"
    )

    merged = merged.apply(update_condition_decision, axis=1)

    output_csv = data_dir / "final_condition_curation_report.csv"
    output_json = data_dir / "final_condition_curation_report.json"

    merged.to_csv(output_csv, index=False)
    merged.to_json(output_json, orient="records", indent=2)

    print(f"Updated condition curation report with session validation:")
    print(f"  {output_csv}")
    print(f"  {output_json}")

    print("")
    print("Updated condition summary:")

    display_cols = [
        "participant_id",
        "condition",
        "session_status",
        "condition_status",
        "condition_curation_decision",
        "condition_curation_reason",
    ]

    existing_cols = [col for col in display_cols if col in merged.columns]

    print(merged[existing_cols].to_string(index=False))


if __name__ == "__main__":
    main()
