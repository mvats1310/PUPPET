#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from collections import defaultdict

import pandas as pd


REQUIRED_CONDITIONS = ["VR", "2D", "REAL"]


def load_json(path):
    with Path(path).open("r") as f:
        return json.load(f)


def save_json(data, path):
    with Path(path).open("w") as f:
        json.dump(data, f, indent=2)


def load_condition_summary(data_dir):
    path = Path(data_dir) / "condition_validation_summary.csv"

    if not path.exists():
        raise FileNotFoundError(
            "Missing condition_validation_summary.csv. "
            "Run summarize_conditions.py first."
        )

    return pd.read_csv(path)


def decide_participant_status(condition_rows):
    statuses = list(condition_rows["condition_status"])

    if any(status == "fail" for status in statuses):
        return "incomplete"

    if any(status == "review" for status in statuses):
        return "review"

    return "complete"


def build_participant_summary(condition_df):
    grouped = defaultdict(list)

    for _, row in condition_df.iterrows():
        participant_id = row["participant_id"]
        grouped[participant_id].append(row)

    output_rows = []

    for participant_id, rows in grouped.items():
        participant_df = pd.DataFrame(rows)

        found_conditions = set(participant_df["condition"].astype(str).tolist())

        missing_conditions = [
            condition for condition in REQUIRED_CONDITIONS
            if condition not in found_conditions
        ]

        issues = []
        review_reasons = []

        if missing_conditions:
            issues.append(
                "Missing required conditions: " + ", ".join(missing_conditions)
            )

        for _, condition_row in participant_df.iterrows():
            condition = condition_row["condition"]
            status = condition_row["condition_status"]

            if status == "fail":
                issues.append(f"{condition}: condition failed validation")

            if status == "review":
                review_reasons.append(f"{condition}: condition requires review")

            condition_issues = condition_row.get("issues")
            condition_reviews = condition_row.get("review_reasons")

            if isinstance(condition_issues, str) and condition_issues.strip():
                issues.append(f"{condition}: {condition_issues}")

            if isinstance(condition_reviews, str) and condition_reviews.strip():
                review_reasons.append(f"{condition}: {condition_reviews}")

        if missing_conditions:
            participant_status = "incomplete"
        else:
            participant_status = decide_participant_status(participant_df)

        row = {
            "participant_id": participant_id,
            "participant_status": participant_status,
            "required_conditions": ",".join(REQUIRED_CONDITIONS),
            "found_conditions": ",".join(sorted(found_conditions)),
            "missing_conditions": ",".join(missing_conditions),
            "num_conditions_found": len(found_conditions),
            "num_conditions_required": len(REQUIRED_CONDITIONS),
            "num_condition_fail": int((participant_df["condition_status"] == "fail").sum()),
            "num_condition_review": int((participant_df["condition_status"] == "review").sum()),
            "num_condition_pass": int((participant_df["condition_status"] == "pass").sum()),
            "mean_success_rate": pd.to_numeric(
                participant_df["success_rate"],
                errors="coerce"
            ).mean(),
            "mean_intervention_rate": pd.to_numeric(
                participant_df["intervention_rate"],
                errors="coerce"
            ).mean(),
            "issues": " | ".join(issues),
            "review_reasons": " | ".join(review_reasons),
        }

        output_rows.append(row)

    return pd.DataFrame(output_rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir", help="Data directory, usually: data")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)

    condition_df = load_condition_summary(data_dir)

    participant_df = build_participant_summary(condition_df)

    output_csv = data_dir / "participant_validation_summary.csv"
    output_json = data_dir / "participant_validation_summary.json"

    participant_df.to_csv(output_csv, index=False)
    save_json(participant_df.to_dict(orient="records"), output_json)

    print(f"Saved participant validation summary CSV: {output_csv}")
    print(f"Saved participant validation summary JSON: {output_json}")

    print("")
    print("Participant summary:")

    display_cols = [
        "participant_id",
        "participant_status",
        "found_conditions",
        "missing_conditions",
        "num_condition_pass",
        "num_condition_review",
        "num_condition_fail",
        "mean_success_rate",
        "mean_intervention_rate",
    ]

    existing_cols = [
        col for col in display_cols
        if col in participant_df.columns
    ]

    print(participant_df[existing_cols].to_string(index=False))


if __name__ == "__main__":
    main()
