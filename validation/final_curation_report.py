#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

import pandas as pd


# ============================================================
# Trial definitions
# ============================================================

LEARNING_TRIALS = ["T01"]
EXECUTION_TRIALS = ["T02", "T03"]


# ============================================================
# Consistency / range review thresholds
# ============================================================

# These are conservative review thresholds for early-stage
# PUPPET validation.
#
# Later, once more participants are available, repeated-trial
# consistency metrics / clustering can be used alongside these.
RANGE_REVIEW_THRESHOLDS = {
    "range_completion_time": 15.0,
    "range_joint_path_length": 1.5,
    "range_joint_jerk": 50000.0,
    "range_base_path_length": 1.0,
    "range_object_path_length": 1.0,
    "range_gripper_chatter": 3.0,
}


# ============================================================
# Utility functions
# ============================================================

def load_json(path):
    with Path(path).open("r") as f:
        return json.load(f)


def save_json(data, path):
    with Path(path).open("w") as f:
        json.dump(
            data,
            f,
            indent=2,
        )


def safe_read_csv(path):
    path = Path(path)

    if not path.exists():
        return pd.DataFrame()

    return pd.read_csv(path)


def bool_is_true(value):
    """
    Safely interpret common boolean representations.

    Returns:
        True
        False
        None for missing / NaN
    """

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    if isinstance(value, bool):
        return value

    if isinstance(value, str):

        parsed = value.strip().lower()

        if parsed in [
            "true",
            "yes",
            "1",
        ]:
            return True

        if parsed in [
            "false",
            "no",
            "0",
        ]:
            return False

    return bool(value)


# ============================================================
# Load trial quality reports
# ============================================================

def load_trial_quality_reports(data_dir):
    data_dir = Path(data_dir)
    rows = []

    for trial_dir in sorted(
        data_dir.iterdir()
    ):

        if not trial_dir.is_dir():
            continue

        report_path = (
            trial_dir
            / "quality_report.json"
        )

        if not report_path.exists():
            continue

        report = load_json(
            report_path
        )

        metrics = report.get(
            "metrics",
            {},
        )

        row = {
            "trial_dir": str(
                trial_dir
            ),

            "participant_id": report.get(
                "participant_id"
            ),

            "condition": report.get(
                "condition"
            ),

            "trial_id": report.get(
                "trial_id"
            ),

            "task_success": report.get(
                "task_success"
            ),

            "technician_intervention": report.get(
                "technician_intervention"
            ),

            "notes": report.get(
                "notes"
            ),
        }

        for key, value in metrics.items():
            row[key] = value

        rows.append(
            row
        )

    return pd.DataFrame(
        rows
    )


# ============================================================
# Trial-level curation
# ============================================================

def decide_trial_curation(row):
    """
    Trial-level curation policy.

    Raw task completion:
        task_success=False
            -> reject

    Validation:
        validation status=fail
            -> reject

    Intervention:
        T01
            learning trial
            intervention is allowed and does not affect
            curation by itself

        T02/T03
            execution trials
            any technician intervention -> reject

    Other technical validation concerns:
        -> review
    """

    reasons = []

    validation_status = str(
        row.get(
            "status",
            "",
        )
    ).strip().lower()

    trial_id = str(
        row.get(
            "trial_id",
            "",
        )
    ).strip().upper()

    task_success = bool_is_true(
        row.get(
            "task_success"
        )
    )

    technician_intervention = bool_is_true(
        row.get(
            "technician_intervention"
        )
    )

    # --------------------------------------------------------
    # Validation failure
    # --------------------------------------------------------

    if validation_status == "fail":

        return (
            "reject",
            "Trial validation failed."
        )

    # --------------------------------------------------------
    # Raw task failure
    # --------------------------------------------------------

    if task_success is False:

        return (
            "reject",
            "Trial was not successful."
        )

    # --------------------------------------------------------
    # Intervention policy
    # --------------------------------------------------------

    if technician_intervention is True:

        # T01 = learning trial
        if trial_id in LEARNING_TRIALS:

            # Intervention remains recorded but does not
            # independently change curation.
            pass

        # T02 / T03 = execution trials
        elif trial_id in EXECUTION_TRIALS:

            intervention_count = row.get(
                "intervention_count",
                row.get(
                    "num_interventions",
                    1,
                ),
            )

            intervention_severity = str(
                row.get(
                    "intervention_severity",
                    "minor",
                )
            ).strip().lower()

            try:
                intervention_count = int(
                    float(intervention_count)
                )
            except Exception:
                intervention_count = 1

            if intervention_severity == "major":

                reasons.append(
                    f"Major technician/researcher intervention "
                    f"occurred during execution trial {trial_id}."
                )

            elif (
                intervention_severity == "minor"
                and intervention_count > 2
            ):

                reasons.append(
                    f"More than two minor technician/researcher "
                    f"interventions occurred during execution trial "
                    f"{trial_id}."
                )

            # 1-2 minor interventions remain valid and are
            # retained as recorded analysis variables.

        else:

            reasons.append(
                f"Technician intervention occurred for unknown "
                f"trial_id '{trial_id}'."
            )

    # --------------------------------------------------------
    # Validation review
    # --------------------------------------------------------

    if validation_status == "review":

        reasons.append(
            "Trial validation requires review."
        )

    # --------------------------------------------------------
    # EE missing-data check
    # --------------------------------------------------------

    ee_missing_ratio = row.get(
        "ee_missing_ratio"
    )

    if (
        pd.notna(
            ee_missing_ratio
        )
        and float(
            ee_missing_ratio
        )
        > 0.9
    ):

        reasons.append(
            "End-effector Cartesian pose is mostly missing."
        )

    # --------------------------------------------------------
    # Object-path sanity check
    # --------------------------------------------------------

    object_path = row.get(
        "object_path_length"
    )

    if (
        pd.notna(
            object_path
        )
        and float(
            object_path
        )
        < 0.02
        and task_success is True
    ):

        reasons.append(
            "Object path length is near zero despite "
            "task_success=true."
        )

    # --------------------------------------------------------
    # Joint jerk sanity check
    # --------------------------------------------------------

    joint_jerk = row.get(
        "joint_jerk"
    )

    if (
        pd.notna(
            joint_jerk
        )
        and float(
            joint_jerk
        )
        > 50000
    ):

        reasons.append(
            "Joint jerk is very high; motion may be "
            "unstable or noisy."
        )

    # --------------------------------------------------------
    # Minimum telemetry size
    # --------------------------------------------------------

    num_rows = row.get(
        "num_rows"
    )

    if (
        pd.notna(
            num_rows
        )
        and float(
            num_rows
        )
        < 50
    ):

        return (
            "reject",
            "Too few telemetry rows."
        )

    # --------------------------------------------------------
    # Final trial curation decision
    # --------------------------------------------------------

    if reasons:

        return (
            "review",
            " | ".join(
                reasons
            ),
        )

    return (
        "keep",
        "",
    )


# ============================================================
# Condition-level range review
# ============================================================

def get_range_review_reasons(row):
    reasons = []

    for (
        col,
        threshold,
    ) in RANGE_REVIEW_THRESHOLDS.items():

        if col not in row:
            continue

        value = row.get(
            col
        )

        if pd.isna(
            value
        ):
            continue

        try:

            value = float(
                value
            )

        except Exception:

            continue

        if value > threshold:

            reasons.append(
                f"{col} is high "
                f"({value:.3f} > {threshold:.3f})"
            )

    return reasons


# ============================================================
# Condition-level curation
# ============================================================

def decide_condition_curation(row):
    """
    Condition-level curation policy.

    A condition is rejected if its validation summary is FAIL.

    Intervention policy:
        T01 interventions are learning-phase events and do
        not invalidate the condition.

        Any T02/T03 intervention should already produce a
        condition_status='fail' through summarize_conditions.py.

    execution_success_rate and execution_intervention_rate
    are retained as explicit analysis variables.
    """

    reasons = []

    status = str(
        row.get(
            "condition_status",
            "",
        )
    ).strip().lower()

    # --------------------------------------------------------
    # Condition validation failure
    # --------------------------------------------------------

    if status == "fail":

        return (
            "reject",
            "Condition validation failed."
        )

    # --------------------------------------------------------
    # Raw task completion
    # --------------------------------------------------------

    success_rate = row.get(
        "success_rate"
    )

    if (
        pd.notna(
            success_rate
        )
        and float(
            success_rate
        )
        < 1.0
    ):

        reasons.append(
            "Not all trials were successfully completed."
        )

    # --------------------------------------------------------
    # Execution success
    # --------------------------------------------------------
    #
    # This applies only to T02/T03.
    #
    # A rate < 1 means at least one execution trial either:
    #   - did not complete successfully
    #   - required technician intervention
    #
    # Normally summarize_conditions.py should already mark
    # the condition FAIL when intervention occurred.
    # This check is retained defensively.
    # --------------------------------------------------------

    execution_success_rate = row.get(
        "execution_success_rate"
    )

    if (
        pd.notna(
            execution_success_rate
        )
        and float(
            execution_success_rate
        )
        < 1.0
    ):

        reasons.append(
            "Not all execution trials were independently successful."
        )

    # --------------------------------------------------------
    # Execution intervention rate
    # --------------------------------------------------------

    execution_intervention_rate = row.get(
        "execution_intervention_rate"
    )

    if (
        pd.notna(
            execution_intervention_rate
        )
        and float(
            execution_intervention_rate
        )
        > 0
    ):

        # This should normally have caused condition_status=fail.
        # If it did not, do not silently KEEP the condition.
        return (
            "reject",
            "At least one execution trial required "
            "technician/researcher intervention."
        )

    # IMPORTANT:
    #
    # We intentionally DO NOT use overall intervention_rate
    # to decide curation because it includes T01.
    #
    # T01 is the learning trial and its interventions are
    # allowed.

    # --------------------------------------------------------
    # Existing condition review
    # --------------------------------------------------------

    if status == "review":

        reasons.append(
            "At least one trial in this condition "
            "requires review."
        )

    # --------------------------------------------------------
    # EE missing-data check
    # --------------------------------------------------------

    mean_ee_missing = row.get(
        "mean_ee_missing_ratio"
    )

    if (
        pd.notna(
            mean_ee_missing
        )
        and float(
            mean_ee_missing
        )
        > 0.9
    ):

        reasons.append(
            "End-effector pose mostly missing across condition."
        )

    # --------------------------------------------------------
    # Repeated-demonstration range checks
    # --------------------------------------------------------

    range_reasons = (
        get_range_review_reasons(
            row
        )
    )

    for reason in range_reasons:

        reasons.append(
            "High repeated-demonstration variability: "
            + reason
        )

    # --------------------------------------------------------
    # Optional consistency label
    # --------------------------------------------------------

    consistency_label = row.get(
        "consistency_label"
    )

    if (
        isinstance(
            consistency_label,
            str,
        )
        and consistency_label
        == "non_consistent"
    ):

        reasons.append(
            "K-means consistency label is non_consistent."
        )

    # --------------------------------------------------------
    # Final condition decision
    # --------------------------------------------------------

    if reasons:

        return (
            "review",
            " | ".join(
                reasons
            ),
        )

    return (
        "keep",
        "",
    )


# ============================================================
# Participant-level curation
# ============================================================

def decide_participant_curation(row):
    reasons = []

    status = row.get(
        "participant_status"
    )

    if status == "incomplete":

        return (
            "reject",
            "Participant dataset is incomplete."
        )

    if status == "review":

        reasons.append(
            "One or more participant conditions "
            "require review."
        )

    if reasons:

        return (
            "review",
            " | ".join(
                reasons
            ),
        )

    return (
        "keep",
        "",
    )


# ============================================================
# Build trial curation
# ============================================================

def build_trial_curation(data_dir):

    validation_df = safe_read_csv(
        Path(
            data_dir
        )
        / "trial_validation_summary.csv"
    )

    quality_df = (
        load_trial_quality_reports(
            data_dir
        )
    )

    if validation_df.empty:

        return pd.DataFrame()

    if quality_df.empty:

        merged = (
            validation_df.copy()
        )

    else:

        merge_cols = [
            "trial_dir",
            "participant_id",
            "condition",
            "trial_id",
            "task_success",
            "technician_intervention",
        ]

        existing_merge_cols = [
            col
            for col in merge_cols
            if (
                col in validation_df.columns
                and col in quality_df.columns
            )
        ]

        merged = validation_df.merge(
            quality_df,
            on=existing_merge_cols,
            how="left",
        )

    decisions = merged.apply(
        decide_trial_curation,
        axis=1,
    )

    merged[
        "trial_curation_decision"
    ] = [
        decision[0]
        for decision in decisions
    ]

    merged[
        "trial_curation_reason"
    ] = [
        decision[1]
        for decision in decisions
    ]

    return merged


# ============================================================
# Build condition curation
# ============================================================

def build_condition_curation(data_dir):

    condition_df = safe_read_csv(
        Path(
            data_dir
        )
        / "condition_validation_summary.csv"
    )

    range_df = safe_read_csv(
        Path(
            data_dir
        )
        / "dataset_range_report.csv"
    )

    consistency_df = safe_read_csv(
        Path(
            data_dir
        )
        / "dataset_consistency_report.csv"
    )

    if condition_df.empty:

        return pd.DataFrame()

    merged = (
        condition_df.copy()
    )

    # --------------------------------------------------------
    # Merge repeated-trial range metrics
    # --------------------------------------------------------

    if not range_df.empty:

        range_cols = [
            col
            for col in range_df.columns
            if (
                col.startswith(
                    "range_"
                )
                or col.startswith(
                    "mean_"
                )
                or col.startswith(
                    "min_"
                )
                or col.startswith(
                    "max_"
                )
                or col
                in [
                    "participant_id",
                    "condition",
                    "num_trials",
                ]
            )
        ]

        range_df_small = (
            range_df[
                range_cols
            ].copy()
        )

        merged = merged.merge(
            range_df_small,
            on=[
                "participant_id",
                "condition",
            ],
            how="left",
            suffixes=(
                "",
                "_range",
            ),
        )

    # --------------------------------------------------------
    # Merge optional consistency analysis
    # --------------------------------------------------------

    if not consistency_df.empty:

        consistency_cols = [
            col
            for col in consistency_df.columns
            if col
            in [
                "participant_id",
                "condition",
                "cluster",
                "consistency_label",
                "curation_decision",
            ]
        ]

        consistency_df_small = (
            consistency_df[
                consistency_cols
            ].copy()
        )

        merged = merged.merge(
            consistency_df_small,
            on=[
                "participant_id",
                "condition",
            ],
            how="left",
            suffixes=(
                "",
                "_consistency",
            ),
        )

    decisions = merged.apply(
        decide_condition_curation,
        axis=1,
    )

    merged[
        "condition_curation_decision"
    ] = [
        decision[0]
        for decision in decisions
    ]

    merged[
        "condition_curation_reason"
    ] = [
        decision[1]
        for decision in decisions
    ]

    return merged


# ============================================================
# Build participant curation
# ============================================================

def build_participant_curation(data_dir):

    participant_df = safe_read_csv(
        Path(
            data_dir
        )
        / "participant_validation_summary.csv"
    )

    condition_curation_df = safe_read_csv(
        Path(
            data_dir
        )
        / "final_condition_curation_report.csv"
    )

    if participant_df.empty:

        return pd.DataFrame()

    merged = (
        participant_df.copy()
    )

    # --------------------------------------------------------
    # Add condition-curation counts when available
    # --------------------------------------------------------

    if not condition_curation_df.empty:

        grouped = (
            condition_curation_df.groupby(
                "participant_id"
            )
        )

        extra_rows = []

        for (
            participant_id,
            group,
        ) in grouped:

            extra_rows.append(
                {
                    "participant_id": participant_id,

                    "num_condition_keep": int(
                        (
                            group[
                                "condition_curation_decision"
                            ]
                            == "keep"
                        ).sum()
                    ),

                    "num_condition_review": int(
                        (
                            group[
                                "condition_curation_decision"
                            ]
                            == "review"
                        ).sum()
                    ),

                    "num_condition_reject": int(
                        (
                            group[
                                "condition_curation_decision"
                            ]
                            == "reject"
                        ).sum()
                    ),
                }
            )

        extra_df = pd.DataFrame(
            extra_rows
        )

        merged = merged.merge(
            extra_df,
            on="participant_id",
            how="left",
        )

    decisions = merged.apply(
        decide_participant_curation,
        axis=1,
    )

    merged[
        "participant_curation_decision"
    ] = [
        decision[0]
        for decision in decisions
    ]

    merged[
        "participant_curation_reason"
    ] = [
        decision[1]
        for decision in decisions
    ]

    return merged


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "data_dir",
        help=(
            "Data directory, usually: data"
        ),
    )

    args = parser.parse_args()

    data_dir = Path(
        args.data_dir
    )

    # --------------------------------------------------------
    # Trial curation
    # --------------------------------------------------------

    trial_curation = (
        build_trial_curation(
            data_dir
        )
    )

    # --------------------------------------------------------
    # Condition curation
    # --------------------------------------------------------

    condition_curation = (
        build_condition_curation(
            data_dir
        )
    )

    # --------------------------------------------------------
    # Save trial reports
    # --------------------------------------------------------

    if not trial_curation.empty:

        trial_csv = (
            data_dir
            / "final_trial_curation_report.csv"
        )

        trial_json = (
            data_dir
            / "final_trial_curation_report.json"
        )

        trial_curation.to_csv(
            trial_csv,
            index=False,
        )

        save_json(
            trial_curation.to_dict(
                orient="records"
            ),
            trial_json,
        )

        print(
            f"Saved trial curation report CSV: "
            f"{trial_csv}"
        )

        print(
            f"Saved trial curation report JSON: "
            f"{trial_json}"
        )

    # --------------------------------------------------------
    # Save condition reports
    # --------------------------------------------------------

    if not condition_curation.empty:

        condition_csv = (
            data_dir
            / "final_condition_curation_report.csv"
        )

        condition_json = (
            data_dir
            / "final_condition_curation_report.json"
        )

        condition_curation.to_csv(
            condition_csv,
            index=False,
        )

        save_json(
            condition_curation.to_dict(
                orient="records"
            ),
            condition_json,
        )

        print(
            f"Saved condition curation report CSV: "
            f"{condition_csv}"
        )

        print(
            f"Saved condition curation report JSON: "
            f"{condition_json}"
        )

    # --------------------------------------------------------
    # Participant curation
    # --------------------------------------------------------

    participant_curation = (
        build_participant_curation(
            data_dir
        )
    )

    if not participant_curation.empty:

        participant_csv = (
            data_dir
            / "final_participant_curation_report.csv"
        )

        participant_json = (
            data_dir
            / "final_participant_curation_report.json"
        )

        participant_curation.to_csv(
            participant_csv,
            index=False,
        )

        save_json(
            participant_curation.to_dict(
                orient="records"
            ),
            participant_json,
        )

        print(
            f"Saved participant curation report CSV: "
            f"{participant_csv}"
        )

        print(
            f"Saved participant curation report JSON: "
            f"{participant_json}"
        )

    # ========================================================
    # Terminal summary
    # ========================================================

    print("")
    print(
        "Final curation summary:"
    )

    # --------------------------------------------------------
    # Participant level
    # --------------------------------------------------------

    if not participant_curation.empty:

        display_cols = [
            "participant_id",
            "participant_status",
            "participant_curation_decision",
            "participant_curation_reason",
        ]

        existing_cols = [
            col
            for col in display_cols
            if col
            in participant_curation.columns
        ]

        print("")
        print(
            "Participant level:"
        )

        print(
            participant_curation[
                existing_cols
            ].to_string(
                index=False
            )
        )

    # --------------------------------------------------------
    # Condition level
    # --------------------------------------------------------

    if not condition_curation.empty:

        display_cols = [
            "participant_id",
            "condition",
            "condition_status",
            "success_rate",
            "execution_success_rate",
            "intervention_rate",
            "learning_intervention_rate",
            "execution_intervention_rate",
            "condition_curation_decision",
            "condition_curation_reason",
        ]

        existing_cols = [
            col
            for col in display_cols
            if col
            in condition_curation.columns
        ]

        print("")
        print(
            "Condition level:"
        )

        print(
            condition_curation[
                existing_cols
            ].to_string(
                index=False
            )
        )

    # --------------------------------------------------------
    # Trial level
    # --------------------------------------------------------

    if not trial_curation.empty:

        display_cols = [
            "trial_dir",
            "trial_id",
            "status",
            "task_success",
            "technician_intervention",
            "trial_curation_decision",
            "trial_curation_reason",
        ]

        existing_cols = [
            col
            for col in display_cols
            if col
            in trial_curation.columns
        ]

        print("")
        print(
            "Trial level:"
        )

        print(
            trial_curation[
                existing_cols
            ].to_string(
                index=False
            )
        )


if __name__ == "__main__":
    main()