#!/usr/bin/env python3

import argparse
import json
import subprocess
from pathlib import Path

import pandas as pd


def load_json(path):
    with Path(path).open("r") as f:
        return json.load(f)


def save_json(data, path):
    with Path(path).open("w") as f:
        json.dump(data, f, indent=2)


def is_trial_folder(path):
    if not path.is_dir():
        return False

    return (path / "metadata.yaml").exists()


def run_trial_validator(trial_dir):
    cmd = ["python", "validate_trial.py", str(trial_dir)]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    return result.returncode, result.stdout, result.stderr


def summarize_validation_report(trial_dir):
    report_path = trial_dir / "validation_report.json"

    if not report_path.exists():
        return {
            "trial_dir": str(trial_dir),
            "status": "fail",
            "participant_id": None,
            "condition": None,
            "trial_id": None,
            "training_group": None,
            "task_success": None,
            "technician_intervention": None,
            "num_rows": None,
            "duration_seconds": None,
            "ee_missing_ratio": None,
            "num_issues": 1,
            "num_review_reasons": 0,
            "issues": "validation_report.json was not created",
            "review_reasons": "",
        }

    report = load_json(report_path)

    metadata = report.get("metadata_summary", {})
    telemetry = report.get("telemetry_summary", {})

    issues = report.get("issues", [])
    review_reasons = report.get("review_reasons", [])

    return {
        "trial_dir": str(trial_dir),
        "status": report.get("status"),
        "participant_id": metadata.get("participant_id"),
        "condition": metadata.get("condition"),
        "trial_id": metadata.get("trial_id"),
        "training_group": metadata.get("training_group"),
        "task_success": metadata.get("task_success"),
        "technician_intervention": metadata.get("technician_intervention"),
        "num_rows": telemetry.get("num_rows"),
        "duration_seconds": telemetry.get("duration_seconds"),
        "ee_missing_ratio": telemetry.get("ee_missing_ratio"),
        "num_issues": len(issues),
        "num_review_reasons": len(review_reasons),
        "issues": " | ".join(issues),
        "review_reasons": " | ".join(review_reasons),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "data_dir",
        help="Data folder, usually: data"
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)

    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    trial_dirs = [
        path for path in sorted(data_dir.iterdir())
        if is_trial_folder(path)
    ]

    if len(trial_dirs) == 0:
        raise ValueError("No trial folders with metadata.yaml were found.")

    print(f"Found {len(trial_dirs)} trial folders.")

    rows = []

    for trial_dir in trial_dirs:
        print(f"\nValidating {trial_dir}...")

        returncode, stdout, stderr = run_trial_validator(trial_dir)

        if stdout.strip():
            print(stdout.strip())

        if stderr.strip():
            print(stderr.strip())

        row = summarize_validation_report(trial_dir)
        rows.append(row)

    summary_df = pd.DataFrame(rows)

    output_csv = data_dir / "trial_validation_summary.csv"
    output_json = data_dir / "trial_validation_summary.json"

    summary_df.to_csv(output_csv, index=False)
    save_json(rows, output_json)

    print("")
    print(f"Saved validation summary CSV: {output_csv}")
    print(f"Saved validation summary JSON: {output_json}")

    print("")
    print("Status counts:")
    print(summary_df["status"].value_counts(dropna=False).to_string())

    print("")
    print("Summary:")
    display_cols = [
        "trial_dir",
        "status",
        "participant_id",
        "condition",
        "trial_id",
        "task_success",
        "technician_intervention",
        "num_rows",
        "duration_seconds",
        "ee_missing_ratio",
    ]

    existing_cols = [
        col for col in display_cols
        if col in summary_df.columns
    ]

    print(summary_df[existing_cols].to_string(index=False))


if __name__ == "__main__":
    main()
