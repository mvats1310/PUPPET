#!/usr/bin/env python3

import json
import sys
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans


METRICS_FOR_CONSISTENCY = [
    "completion_time",
    "cartesian_path_length_clean",
    "cartesian_jerk",
    "joint_path_length",
    "joint_jerk",
    "joint_effort",
    "gripper_chatter",
    "base_path_length_clean",
    "object_path_length",
]


def load_quality_report(trial_dir):
    report_path = Path(trial_dir) / "quality_report.json"

    if not report_path.exists():
        return None

    with report_path.open("r") as f:
        return json.load(f)


def find_trial_reports(data_dir):
    data_dir = Path(data_dir)
    reports = []

    for trial_dir in sorted(data_dir.iterdir()):
        if not trial_dir.is_dir():
            continue

        report = load_quality_report(trial_dir)

        if report is None:
            continue

        report["_trial_dir"] = str(trial_dir)
        reports.append(report)

    return reports


def build_range_features(reports):
    grouped = defaultdict(list)

    for report in reports:
        participant_id = report.get("participant_id")
        condition = report.get("condition")

        if participant_id is None or condition is None:
            continue

        key = (participant_id, condition)
        grouped[key].append(report)

    rows = []

    for (participant_id, condition), group_reports in grouped.items():
        row = {
            "participant_id": participant_id,
            "condition": condition,
            "num_trials": len(group_reports),
        }

        task_success_values = [
            r.get("task_success") for r in group_reports
            if r.get("task_success") is not None
        ]

        intervention_values = [
            r.get("technician_intervention") for r in group_reports
            if r.get("technician_intervention") is not None
        ]

        row["num_successful_trials"] = sum(task_success_values)
        row["num_intervention_trials"] = sum(intervention_values)

        if len(task_success_values) > 0:
            row["success_rate"] = sum(task_success_values) / len(task_success_values)
        else:
            row["success_rate"] = None

        if len(intervention_values) > 0:
            row["intervention_rate"] = sum(intervention_values) / len(intervention_values)
        else:
            row["intervention_rate"] = None

        for metric in METRICS_FOR_CONSISTENCY:
            values = []

            for report in group_reports:
                metrics = report.get("metrics", {})
                value = metrics.get(metric)

                if value is None:
                    continue

                try:
                    value = float(value)
                except Exception:
                    continue

                if np.isnan(value) or np.isinf(value):
                    continue

                values.append(value)

            if len(values) >= 2:
                row[f"min_{metric}"] = float(np.min(values))
                row[f"max_{metric}"] = float(np.max(values))
                row[f"mean_{metric}"] = float(np.mean(values))
                row[f"range_{metric}"] = float(np.max(values) - np.min(values))
            elif len(values) == 1:
                row[f"min_{metric}"] = float(values[0])
                row[f"max_{metric}"] = float(values[0])
                row[f"mean_{metric}"] = float(values[0])
                row[f"range_{metric}"] = 0.0
            else:
                row[f"min_{metric}"] = None
                row[f"max_{metric}"] = None
                row[f"mean_{metric}"] = None
                row[f"range_{metric}"] = None

        rows.append(row)

    return pd.DataFrame(rows)


def choose_feature_columns(feature_df):
    candidate_cols = [
        col for col in feature_df.columns
        if col.startswith("range_")
    ]

    usable_cols = []

    for col in candidate_cols:
        values = pd.to_numeric(feature_df[col], errors="coerce")

        # Need at least two non-empty values and some variation for clustering.
        if values.notna().sum() >= 2 and values.nunique(dropna=True) > 1:
            usable_cols.append(col)

    return usable_cols


def run_consistency_clustering(feature_df, feature_cols):
    if len(feature_df) < 2:
        raise ValueError("Need at least two participant-condition sets for K-means clustering.")

    if len(feature_cols) == 0:
        raise ValueError("No usable range feature columns available for clustering.")

    clustering_df = feature_df.copy()

    X = clustering_df[feature_cols].apply(pd.to_numeric, errors="coerce")

    # Fill missing values with the column median.
    X = X.fillna(X.median(numeric_only=True))

    # If anything is still missing, fill with 0.
    X = X.fillna(0)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(
        n_clusters=2,
        random_state=42,
        n_init=20
    )

    cluster_labels = kmeans.fit_predict(X_scaled)
    clustering_df["cluster"] = cluster_labels

    # Decide which cluster is "consistent".
    # The consistent cluster should have lower average range values.
    cluster_range_means = {}

    for cluster_id in sorted(clustering_df["cluster"].unique()):
        cluster_rows = clustering_df[clustering_df["cluster"] == cluster_id]
        mean_range = cluster_rows[feature_cols].apply(
            pd.to_numeric, errors="coerce"
        ).mean(axis=1).mean()

        cluster_range_means[cluster_id] = mean_range

    consistent_cluster = min(cluster_range_means, key=cluster_range_means.get)

    clustering_df["consistency_label"] = clustering_df["cluster"].apply(
        lambda c: "consistent" if c == consistent_cluster else "non_consistent"
    )

    def decide_curation(row):
        if row.get("success_rate") is not None and row.get("success_rate") < 1.0:
            return "review"

        if row.get("intervention_rate") is not None and row.get("intervention_rate") > 0:
            return "review"

        if row.get("consistency_label") == "non_consistent":
            return "review"

        return "keep"

    clustering_df["curation_decision"] = clustering_df.apply(decide_curation, axis=1)

    return clustering_df


def save_json(data, output_path):
    output_path = Path(output_path)

    with output_path.open("w") as f:
        json.dump(data, f, indent=2)


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_dataset_consistency.py data")
        sys.exit(1)

    data_dir = Path(sys.argv[1])

    reports = find_trial_reports(data_dir)

    if len(reports) == 0:
        raise ValueError("No quality_report.json files found. Run analyze_trial.py first.")

    feature_df = build_range_features(reports)

    if len(feature_df) == 0:
        raise ValueError("No participant-condition sets could be built.")

    range_output_csv = data_dir / "dataset_range_report.csv"
    range_output_json = data_dir / "dataset_range_report.json"

    feature_df.to_csv(range_output_csv, index=False)
    save_json(feature_df.to_dict(orient="records"), range_output_json)

    print(f"Saved range report: {range_output_csv}")
    print(f"Saved range report JSON: {range_output_json}")

    feature_cols = choose_feature_columns(feature_df)

    print("")
    print("Participant-condition sets found:")
    for _, row in feature_df.iterrows():
        print(
            f"  {row['participant_id']} / {row['condition']} "
            f"with {row['num_trials']} trials"
        )

    print("")
    print("Usable clustering features:")
    if len(feature_cols) == 0:
        print("  None yet")
    else:
        for col in feature_cols:
            print(f"  {col}")

    if len(feature_df) < 2:
        print("")
        print("Only one participant-condition set was found.")
        print("K-means consistency clustering needs at least two sets.")
        print("For now, use dataset_range_report.csv to inspect within-set variability.")
        return

    if len(feature_cols) == 0:
        print("")
        print("No usable clustering features were found.")
        print("This can happen if all range values are missing or identical.")
        print("For now, use dataset_range_report.csv to inspect the raw ranges.")
        return

    result_df = run_consistency_clustering(feature_df, feature_cols)

    output_csv = data_dir / "dataset_consistency_report.csv"
    output_json = data_dir / "dataset_consistency_report.json"

    result_df.to_csv(output_csv, index=False)
    save_json(result_df.to_dict(orient="records"), output_json)

    print("")
    print(f"Saved consistency report: {output_csv}")
    print(f"Saved consistency report JSON: {output_json}")

    print("")
    print("Consistency summary:")
    summary_cols = [
        "participant_id",
        "condition",
        "num_trials",
        "success_rate",
        "intervention_rate",
        "consistency_label",
        "curation_decision",
    ]

    existing_summary_cols = [
        col for col in summary_cols
        if col in result_df.columns
    ]

    print(result_df[existing_summary_cols].to_string(index=False))


if __name__ == "__main__":
    main()
