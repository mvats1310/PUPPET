#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from collections import defaultdict

import pandas as pd


REQUIRED_TRIALS = ["T01", "T02", "T03"]
LEARNING_TRIALS = ["T01"]
EXECUTION_TRIALS = ["T02", "T03"]


def load_json(path):
    with Path(path).open("r") as f:
        return json.load(f)


def save_json(data, path):
    with Path(path).open("w") as f:
        json.dump(data, f, indent=2)


def to_bool(value):
    """
    Safely convert common boolean representations.
    """

    if isinstance(value, bool):
        return value

    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip().lower()

        if value in ["true", "yes", "1"]:
            return True

        if value in ["false", "no", "0"]:
            return False

    return bool(value)


def find_trial_validation_reports(data_dir):
    data_dir = Path(data_dir)
    reports = []

    for trial_dir in sorted(data_dir.iterdir()):

        if not trial_dir.is_dir():
            continue

        report_path = (
            trial_dir
            / "validation_report.json"
        )

        if not report_path.exists():
            continue

        report = load_json(
            report_path
        )

        report["_trial_dir"] = str(
            trial_dir
        )

        reports.append(
            report
        )

    return reports


def condition_status_from_trials(
    trial_reports,
):
    """
    Condition status follows the worst trial-level
    validation status.

    fail   > review > pass
    """

    statuses = [
        r.get("status")
        for r in trial_reports
    ]

    if any(
        status == "fail"
        for status in statuses
    ):
        return "fail"

    if any(
        status == "review"
        for status in statuses
    ):
        return "review"

    return "pass"


def build_condition_summary(
    reports,
):
    grouped = defaultdict(
        list
    )

    # ========================================================
    # Group trial reports by participant + condition
    # ========================================================

    for report in reports:

        metadata = report.get(
            "metadata_summary",
            {},
        )

        participant_id = metadata.get(
            "participant_id"
        )

        condition = metadata.get(
            "condition"
        )

        if (
            participant_id is None
            or condition is None
        ):
            continue

        grouped[
            (
                participant_id,
                condition,
            )
        ].append(
            report
        )

    rows = []

    # ========================================================
    # Build one summary row per participant-condition
    # ========================================================

    for (
        participant_id,
        condition,
    ), condition_reports in grouped.items():

        # ----------------------------------------------------
        # Trial availability
        # ----------------------------------------------------

        trial_ids = [
            str(
                r.get(
                    "metadata_summary",
                    {},
                ).get(
                    "trial_id",
                    "",
                )
            ).strip().upper()
            for r in condition_reports
        ]

        found_trials = set(
            trial_ids
        )

        missing_trials = [
            trial
            for trial in REQUIRED_TRIALS
            if trial not in found_trials
        ]

        # ----------------------------------------------------
        # Start with trial-level validation statuses
        # ----------------------------------------------------

        status = (
            condition_status_from_trials(
                condition_reports
            )
        )

        issues = []
        review_reasons = []

        # ----------------------------------------------------
        # Required trials
        # ----------------------------------------------------

        if len(
            missing_trials
        ) > 0:

            status = "fail"

            issues.append(
                "Missing required trials: "
                + ", ".join(
                    missing_trials
                )
            )

        # ----------------------------------------------------
        # Propagate trial-level findings
        # ----------------------------------------------------

        for report in condition_reports:

            metadata_summary = report.get(
                "metadata_summary",
                {},
            )

            trial_id = str(
                metadata_summary.get(
                    "trial_id",
                    "",
                )
            ).strip().upper()

            trial_status = report.get(
                "status"
            )

            for issue in report.get(
                "issues",
                [],
            ):

                issues.append(
                    f"{trial_id}: {issue}"
                )

            for reason in report.get(
                "review_reasons",
                [],
            ):

                review_reasons.append(
                    f"{trial_id}: {reason}"
                )

            if trial_status == "fail":

                issues.append(
                    f"{trial_id}: trial validation failed"
                )

            if trial_status == "review":

                review_reasons.append(
                    f"{trial_id}: trial requires review"
                )

        # ====================================================
        # Raw task-success metrics
        # ====================================================

        task_success_values = []

        for report in condition_reports:

            value = (
                report.get(
                    "metadata_summary",
                    {},
                ).get(
                    "task_success"
                )
            )

            parsed = to_bool(
                value
            )

            if parsed is not None:

                task_success_values.append(
                    parsed
                )

        if len(
            task_success_values
        ) > 0:

            success_rate = (
                sum(
                    task_success_values
                )
                / len(
                    task_success_values
                )
            )

        else:

            success_rate = None

        # ====================================================
        # Intervention metrics
        # ====================================================
        #
        # Overall intervention rate remains useful as a
        # descriptive metric.
        #
        # However:
        #
        # T01 = learning trial
        #   intervention is allowed and does not invalidate
        #   the condition by itself.
        #
        # T02/T03 = execution trials
        #   any intervention means execution failure.
        #
        # ====================================================

        intervention_values = []

        learning_intervention_values = []
        execution_intervention_values = []

        execution_success_values = []

        execution_intervention_trials = []

        for report in condition_reports:

            metadata_summary = report.get(
                "metadata_summary",
                {},
            )

            trial_id = str(
                metadata_summary.get(
                    "trial_id",
                    "",
                )
            ).strip().upper()

            intervention = to_bool(
                metadata_summary.get(
                    "technician_intervention"
                )
            )

            task_success = to_bool(
                metadata_summary.get(
                    "task_success"
                )
            )

            # -----------------------------------------------
            # Overall intervention rate
            # -----------------------------------------------

            if intervention is not None:

                intervention_values.append(
                    intervention
                )

            # -----------------------------------------------
            # T01 learning intervention
            # -----------------------------------------------

            if (
                trial_id
                in LEARNING_TRIALS
                and intervention is not None
            ):

                learning_intervention_values.append(
                    intervention
                )

            # -----------------------------------------------
            # T02/T03 execution intervention
            # -----------------------------------------------

            if (
                trial_id
                in EXECUTION_TRIALS
            ):

                if intervention is not None:

                    execution_intervention_values.append(
                        intervention
                    )

                # Execution success means:
                #
                # 1. task was completed successfully
                # 2. no technician intervention occurred
                #
                if (
                    task_success is not None
                    and intervention is not None
                ):

                    execution_success = (
                        task_success
                        and not intervention
                    )

                    execution_success_values.append(
                        execution_success
                    )

                if intervention is True:

                    execution_intervention_trials.append(
                        trial_id
                    )

        # ----------------------------------------------------
        # Intervention rates
        # ----------------------------------------------------

        if intervention_values:

            intervention_rate = (
                sum(
                    intervention_values
                )
                / len(
                    intervention_values
                )
            )

        else:

            intervention_rate = None

        if learning_intervention_values:

            learning_intervention_rate = (
                sum(
                    learning_intervention_values
                )
                / len(
                    learning_intervention_values
                )
            )

        else:

            learning_intervention_rate = None

        if execution_intervention_values:

            execution_intervention_rate = (
                sum(
                    execution_intervention_values
                )
                / len(
                    execution_intervention_values
                )
            )

        else:

            execution_intervention_rate = None

        if execution_success_values:

            execution_success_rate = (
                sum(
                    execution_success_values
                )
                / len(
                    execution_success_values
                )
            )

        else:

            execution_success_rate = None

        # ====================================================
        # Condition-level task outcome policy
        # ====================================================

        # Raw task failure remains a concern.
        #
        # T01 is still recorded here because task_success
        # represents whether the physical task was completed.
        #
        # Intervention itself is handled separately below.

        if (
            success_rate is not None
            and success_rate < 1.0
        ):

            if status != "fail":
                status = "review"

            review_reasons.append(
                "Not all trials were successfully completed."
            )

        # ----------------------------------------------------
        # EXECUTION INTERVENTION POLICY
        # ----------------------------------------------------
        #
        # DO NOT penalize intervention in T01.
        #
        # Any T02/T03 intervention = condition FAIL.
        #
        # This should already be reflected in the individual
        # validation_report.json after validate_trial.py is
        # rerun, but this check makes the condition summary
        # robust and explicit.
        # ----------------------------------------------------

        if execution_intervention_trials:

            status = "fail"

            unique_execution_intervention_trials = list(
                dict.fromkeys(
                    execution_intervention_trials
                )
            )

            message = (
                "Technician/researcher intervention occurred "
                "during execution trial(s): "
                + ", ".join(
                    unique_execution_intervention_trials
                )
                + "."
            )

            if message not in issues:

                issues.append(
                    message
                )

        # ====================================================
        # Telemetry summaries
        # ====================================================

        num_rows_values = [
            r.get(
                "telemetry_summary",
                {},
            ).get(
                "num_rows"
            )
            for r in condition_reports
            if r.get(
                "telemetry_summary",
                {},
            ).get(
                "num_rows"
            )
            is not None
        ]

        duration_values = [
            r.get(
                "telemetry_summary",
                {},
            ).get(
                "duration_seconds"
            )
            for r in condition_reports
            if r.get(
                "telemetry_summary",
                {},
            ).get(
                "duration_seconds"
            )
            is not None
        ]

        ee_missing_values = [
            r.get(
                "telemetry_summary",
                {},
            ).get(
                "ee_missing_ratio"
            )
            for r in condition_reports
            if r.get(
                "telemetry_summary",
                {},
            ).get(
                "ee_missing_ratio"
            )
            is not None
        ]

        # ====================================================
        # Remove duplicate messages
        # ====================================================

        issues = list(
            dict.fromkeys(
                issues
            )
        )

        review_reasons = list(
            dict.fromkeys(
                review_reasons
            )
        )

        # ====================================================
        # Output row
        # ====================================================

        row = {
            "participant_id": participant_id,

            "condition": condition,

            "condition_status": status,

            "num_trials_found": len(
                condition_reports
            ),

            "required_trials": ",".join(
                REQUIRED_TRIALS
            ),

            "found_trials": ",".join(
                sorted(
                    found_trials
                )
            ),

            "missing_trials": ",".join(
                missing_trials
            ),

            # Raw task completion
            "success_rate": success_rate,

            # T02/T03 task completion with no intervention
            "execution_success_rate": execution_success_rate,

            # Descriptive intervention metrics
            "intervention_rate": intervention_rate,

            "learning_intervention_rate": (
                learning_intervention_rate
            ),

            "execution_intervention_rate": (
                execution_intervention_rate
            ),

            "mean_num_rows": (
                sum(
                    num_rows_values
                )
                / len(
                    num_rows_values
                )
                if num_rows_values
                else None
            ),

            "mean_duration_seconds": (
                sum(
                    duration_values
                )
                / len(
                    duration_values
                )
                if duration_values
                else None
            ),

            "mean_ee_missing_ratio": (
                sum(
                    ee_missing_values
                )
                / len(
                    ee_missing_values
                )
                if ee_missing_values
                else None
            ),

            "num_issues": len(
                issues
            ),

            "num_review_reasons": len(
                review_reasons
            ),

            "issues": " | ".join(
                issues
            ),

            "review_reasons": " | ".join(
                review_reasons
            ),
        }

        rows.append(
            row
        )

    return pd.DataFrame(
        rows
    )


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

    reports = (
        find_trial_validation_reports(
            data_dir
        )
    )

    if len(
        reports
    ) == 0:

        raise ValueError(
            "No validation_report.json files found. "
            "Run validate_all_trials.py first."
        )

    condition_df = (
        build_condition_summary(
            reports
        )
    )

    output_csv = (
        data_dir
        / "condition_validation_summary.csv"
    )

    output_json = (
        data_dir
        / "condition_validation_summary.json"
    )

    condition_df.to_csv(
        output_csv,
        index=False,
    )

    save_json(
        condition_df.to_dict(
            orient="records"
        ),
        output_json,
    )

    print(
        f"Saved condition validation summary CSV: "
        f"{output_csv}"
    )

    print(
        f"Saved condition validation summary JSON: "
        f"{output_json}"
    )

    print("")
    print(
        "Condition summary:"
    )

    display_cols = [
        "participant_id",
        "condition",
        "condition_status",
        "num_trials_found",
        "success_rate",
        "execution_success_rate",
        "intervention_rate",
        "learning_intervention_rate",
        "execution_intervention_rate",
        "mean_num_rows",
        "mean_duration_seconds",
        "mean_ee_missing_ratio",
    ]

    existing_cols = [
        col
        for col in display_cols
        if col
        in condition_df.columns
    ]

    print(
        condition_df[
            existing_cols
        ].to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()