#!/usr/bin/env python3

import argparse
from pathlib import Path

import pandas as pd


def safe_read_csv(path):
    path = Path(path)
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def clean_value(value):
    if pd.isna(value):
        return "N/A"

    text = str(value)

    # Avoid breaking markdown tables if reasons contain pipes.
    text = text.replace("|", ";")

    return text


def status_icon(status):
    status = str(status).lower()

    if status in ["pass", "keep", "complete"]:
        return "✅"

    if status in ["review"]:
        return "⚠️"

    if status in ["fail", "reject", "incomplete"]:
        return "❌"

    return "•"


def write_table(md, df, columns):
    existing = [col for col in columns if col in df.columns]

    if df.empty or not existing:
        md.append("_No data available._")
        md.append("")
        return

    md.append("| " + " | ".join(existing) + " |")
    md.append("| " + " | ".join(["---"] * len(existing)) + " |")

    for _, row in df.iterrows():
        values = [clean_value(row.get(col)) for col in existing]
        md.append("| " + " | ".join(values) + " |")

    md.append("")


def generate_report(data_dir, participant_id):
    data_dir = Path(data_dir)

    session_df = safe_read_csv(data_dir / "session_validation_summary.csv")
    trial_df = safe_read_csv(data_dir / "final_trial_curation_report.csv")
    condition_df = safe_read_csv(data_dir / "final_condition_curation_report.csv")
    participant_df = safe_read_csv(data_dir / "final_participant_curation_report.csv")
    range_df = safe_read_csv(data_dir / "dataset_range_report.csv")
    consistency_df = safe_read_csv(data_dir / "dataset_consistency_report.csv")

    # Filter all reports to this participant.
    if not session_df.empty and "participant_id" in session_df.columns:
        session_df = session_df[session_df["participant_id"] == participant_id]

    if not trial_df.empty and "participant_id" in trial_df.columns:
        trial_df = trial_df[trial_df["participant_id"] == participant_id]

    if not condition_df.empty and "participant_id" in condition_df.columns:
        condition_df = condition_df[condition_df["participant_id"] == participant_id]

    if not participant_df.empty and "participant_id" in participant_df.columns:
        participant_df = participant_df[participant_df["participant_id"] == participant_id]

    if not range_df.empty and "participant_id" in range_df.columns:
        range_df = range_df[range_df["participant_id"] == participant_id]

    if not consistency_df.empty and "participant_id" in consistency_df.columns:
        consistency_df = consistency_df[consistency_df["participant_id"] == participant_id]

    md = []

    md.append(f"# PUPPET Master Validation Report: {participant_id}")
    md.append("")
    md.append(
        "This report summarizes the quality-aware validation and curation status "
        "of one participant dataset across the VR, 2D, and REAL experimental conditions."
    )
    md.append("")

    # ---------------------------------------------------------------------
    # 1. Participant-level decision
    # ---------------------------------------------------------------------
    md.append("## 1. Participant-Level Decision")
    md.append("")

    if participant_df.empty:
        md.append("_No participant-level curation report found._")
        md.append("")
    else:
        row = participant_df.iloc[0]

        status = clean_value(row.get("participant_status"))
        decision = clean_value(row.get("participant_curation_decision"))
        reason = clean_value(row.get("participant_curation_reason"))

        md.append(f"**Participant status:** {status_icon(status)} `{status}`")
        md.append("")
        md.append(f"**Participant curation decision:** {status_icon(decision)} `{decision}`")
        md.append("")
        md.append(f"**Reason:** {reason}")
        md.append("")

    # ---------------------------------------------------------------------
    # 2. Session-level summary
    # ---------------------------------------------------------------------
    md.append("## 2. Session-Level Summary")
    md.append("")
    md.append(
        "Session-level validation checks the raw condition recording before trial-level analysis. "
        "It verifies whether the ROS bag, events file, required topics, and condition-specific videos exist."
    )
    md.append("")

    if session_df.empty:
        md.append("_No session-level validation summary found. Run `validate_all_sessions.py` first._")
        md.append("")
    else:
        display_session = session_df.copy()

        for col in ["session_status", "events_status", "video_status"]:
            if col in display_session.columns:
                display_session[col] = display_session[col].apply(
                    lambda x: f"{status_icon(x)} {x}"
                )

        write_table(
            md,
            display_session,
            [
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
                "event_trials_found",
                "video_status",
                "missing_required_videos",
                "missing_optional_videos",
                "issues",
                "review_reasons",
            ],
        )

    # ---------------------------------------------------------------------
    # 3. Condition-level summary
    # ---------------------------------------------------------------------
    md.append("## 3. Condition-Level Summary")
    md.append("")
    md.append(
        "Condition-level validation combines the three repeated demonstrations "
        "within each condition."
    )
    md.append("")

    if condition_df.empty:
        md.append("_No condition-level curation report found._")
        md.append("")
    else:
        display_condition = condition_df.copy()

        for col in ["condition_status", "condition_curation_decision", "session_status"]:
            if col in display_condition.columns:
                display_condition[col] = display_condition[col].apply(
                    lambda x: f"{status_icon(x)} {x}"
                )

        write_table(
            md,
            display_condition,
            [
                "condition",
                "session_status",
                "condition_status",
                "condition_curation_decision",
                "success_rate",
                "intervention_rate",
                "mean_num_rows",
                "mean_duration_seconds",
                "mean_ee_missing_ratio",
                "missing_required_topics",
                "condition_curation_reason",
                "session_review_reasons",
            ],
        )

    # ---------------------------------------------------------------------
    # 4. Trial-level summary
    # ---------------------------------------------------------------------
    md.append("## 4. Trial-Level Summary")
    md.append("")
    md.append(
        "Trial-level validation checks each individual demonstration segment "
        "for metadata, telemetry completeness, manual labels, and suspicious telemetry patterns."
    )
    md.append("")

    if trial_df.empty:
        md.append("_No trial-level curation report found._")
        md.append("")
    else:
        display_trial = trial_df.copy()

        for col in ["status", "trial_curation_decision"]:
            if col in display_trial.columns:
                display_trial[col] = display_trial[col].apply(
                    lambda x: f"{status_icon(x)} {x}"
                )

        write_table(
            md,
            display_trial,
            [
                "condition",
                "trial_id",
                "status",
                "trial_curation_decision",
                "task_success",
                "technician_intervention",
                "num_rows",
                "duration_seconds",
                "ee_missing_ratio",
                "trial_curation_reason",
            ],
        )

    # ---------------------------------------------------------------------
    # 5. Quality metrics
    # ---------------------------------------------------------------------
    md.append("## 5. Demonstration Quality Metrics")
    md.append("")
    md.append(
        "These metrics describe task execution quality and robot-motion quality "
        "for each segmented demonstration."
    )
    md.append("")

    if trial_df.empty:
        md.append("_No trial quality metrics found._")
        md.append("")
    else:
        write_table(
            md,
            trial_df,
            [
                "condition",
                "trial_id",
                "completion_time",
                "joint_path_length",
                "joint_jerk",
                "joint_effort",
                "gripper_chatter",
                "base_path_length",
                "object_path_length",
                "cartesian_path_length",
                "cartesian_jerk",
            ],
        )

    # ---------------------------------------------------------------------
    # 6. Consistency ranges
    # ---------------------------------------------------------------------
    md.append("## 6. Condition Consistency / Repeated-Demonstration Variability")
    md.append("")
    md.append(
        "This section summarizes variability across the three repeated demonstrations "
        "within each participant-condition set."
    )
    md.append("")

    if range_df.empty:
        md.append("_No dataset_range_report.csv found. Run `analyze_dataset_consistency.py` first._")
        md.append("")
    else:
        write_table(
            md,
            range_df,
            [
                "participant_id",
                "condition",
                "num_trials",
                "range_completion_time",
                "range_joint_path_length",
                "range_joint_jerk",
                "range_joint_effort",
                "range_gripper_chatter",
                "range_base_path_length",
                "range_object_path_length",
            ],
        )

    # ---------------------------------------------------------------------
    # 7. Consistency clustering
    # ---------------------------------------------------------------------
    md.append("## 7. Consistency Cluster Result")
    md.append("")

    if consistency_df.empty:
        md.append(
            "_No dataset_consistency_report.csv found yet. This is expected until "
            "there are enough participant-condition sets for clustering._"
        )
        md.append("")
    else:
        write_table(
            md,
            consistency_df,
            [
                "participant_id",
                "condition",
                "cluster",
                "consistency_label",
                "curation_decision",
            ],
        )

    # ---------------------------------------------------------------------
    # 8. Interpretation
    # ---------------------------------------------------------------------
    md.append("## 8. Interpretation")
    md.append("")

    if participant_df.empty:
        md.append(
            "The participant-level dataset could not be interpreted because the "
            "participant curation report is missing."
        )
    else:
        row = participant_df.iloc[0]
        decision = str(row.get("participant_curation_decision"))

        if decision == "reject":
            md.append(
                "This participant dataset is not yet usable as a complete cross-condition dataset. "
                "This usually means one or more required conditions are missing, failed validation, "
                "or still contain placeholder files."
            )
        elif decision == "review":
            md.append(
                "This participant dataset is partially usable but requires manual review before "
                "being included in final analysis. Review flags may come from missing optional streams, "
                "missing end-effector pose, suspicious telemetry, video audit issues, or high "
                "repeated-demonstration variability."
            )
        elif decision == "keep":
            md.append(
                "This participant dataset passed the current validation and curation checks and "
                "can be considered usable for downstream condition comparison."
            )
        else:
            md.append(
                "The participant curation decision is unclear and should be inspected manually."
            )

    md.append("")

    # ---------------------------------------------------------------------
    # 9. Notes
    # ---------------------------------------------------------------------
    md.append("## 9. Notes")
    md.append("")
    md.append("- `reject` does not always mean the data is permanently unusable. It can mean the condition has not been recorded yet.")
    md.append("- `review` means the data exists but requires human inspection before being used.")
    md.append("- `keep` means the data passed the current validation checks.")
    md.append("- End-effector pose requires `/tf_static` to be recorded correctly in future bags.")
    md.append("")

    return "\n".join(md)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data", help="Data directory")
    parser.add_argument("--participant", required=True, help="Participant ID, e.g. P001")
    args = parser.parse_args()

    report_text = generate_report(args.data, args.participant)

    output_path = Path(args.data) / f"{args.participant}_master_validation_report.md"

    with output_path.open("w") as f:
        f.write(report_text)

    print(f"Saved master report: {output_path}")
    print("")
    print("Open it with:")
    print(f"gedit {output_path}")
    print("")
    print("Or view in terminal:")
    print(f"cat {output_path}")


if __name__ == "__main__":
    main()
