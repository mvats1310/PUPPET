#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


MIN_TELEMETRY_ROWS = 50

REQUIRED_METADATA_FIELDS = [
    "participant_id",
    "condition",
    "trial_id",
    "training_group",
    "task_name",
    "task_success",
    "technician_intervention",
    "intervention_severity",
    "intervention_count",
    "notes",
]

REQUIRED_TELEMETRY_COLUMNS = [
    "time",
    "joint_1",
    "joint_2",
    "joint_3",
    "joint_4",
    "joint_5",
    "joint_6",
    "joint_7",
    "gripper_state",
    "base_x",
    "base_y",
    "base_yaw",
    "object_x",
    "object_y",
    "object_z",
]

OPTIONAL_TELEMETRY_COLUMNS = [
    "ee_x",
    "ee_y",
    "ee_z",
    "quat_x",
    "quat_y",
    "quat_z",
    "quat_w",
    "effort_1",
    "effort_2",
    "effort_3",
    "effort_4",
    "effort_5",
    "effort_6",
    "effort_7",
    "torso_lift_joint",
    "robot_marker_x",
    "robot_marker_y",
    "robot_marker_z",
]


# ============================================================
# Health-check thresholds
# ============================================================

MAX_TIME_GAP_SECONDS = 1.0

# Flat / missing motion checks.
# These detect likely data-capture problems, not "bad performance".
MIN_OBJECT_PATH_FOR_SUCCESS = 0.02
MIN_GRIPPER_RANGE_FOR_SUCCESS = 0.002
MIN_TOTAL_JOINT_RANGE_FOR_SUCCESS = 0.05

# Only extremely implausible jerk is flagged.
EXTREME_JOINT_JERK_THRESHOLD = 50000.0


def load_yaml(path):
    with path.open("r") as f:
        return yaml.safe_load(f)


def load_json(path):
    with path.open("r") as f:
        return json.load(f)


def save_json(data, path):
    path = Path(path)

    with path.open("w") as f:
        json.dump(
            data,
            f,
            indent=2,
        )


def resolve_path(base_dir, maybe_relative_path):
    """
    Resolve either:
      - an absolute path
      - a project-relative path such as data/P01_VR/full_session.bag
      - a trial-folder-relative path

    Project-relative paths are checked first so:
        data/P01_VR/full_session.bag
    does NOT become:
        data/P01_VR_T01/data/P01_VR/full_session.bag
    """

    if maybe_relative_path is None:
        return None

    path = Path(
        str(maybe_relative_path)
    )

    if path.is_absolute():
        return path

    project_relative = (
        Path.cwd()
        / path
    ).resolve()

    if project_relative.exists():
        return project_relative

    return (
        base_dir
        / path
    ).resolve()


def to_bool(value):
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return (
            value.strip().lower()
            in [
                "true",
                "yes",
                "1",
            ]
        )

    return bool(value)


def path_length_from_columns(
    df,
    cols,
):
    if not all(
        col in df.columns
        for col in cols
    ):
        return None

    arr = (
        df[cols]
        .apply(
            pd.to_numeric,
            errors="coerce",
        )
        .to_numpy()
    )

    arr = arr[
        ~np.isnan(arr).any(
            axis=1
        )
    ]

    if len(arr) < 2:
        return None

    diffs = np.diff(
        arr,
        axis=0,
    )

    distances = (
        np.linalg.norm(
            diffs,
            axis=1,
        )
    )

    return float(
        np.sum(
            distances
        )
    )


def signal_range(
    df,
    col,
):
    if col not in df.columns:
        return None

    values = (
        pd.to_numeric(
            df[col],
            errors="coerce",
        )
        .dropna()
    )

    if len(values) < 2:
        return None

    return float(
        values.max()
        - values.min()
    )


# ============================================================
# METADATA CHECK
# ============================================================

def check_metadata(
    trial_dir,
    metadata,
):
    issues = []
    review_reasons = []
    informational_notes = []

    for field in REQUIRED_METADATA_FIELDS:

        if field not in metadata:

            issues.append(
                f"Missing required metadata field: {field}"
            )

    session = metadata.get(
        "session",
        {},
    )

    if not session:

        review_reasons.append(
            "Missing session section in metadata.yaml."
        )

    else:

        if session.get(
            "rosbag"
        ) is None:

            review_reasons.append(
                "Missing session.rosbag path."
            )

        if session.get(
            "events_csv"
        ) is None:

            review_reasons.append(
                "Missing session.events_csv path."
            )

        if session.get(
            "trial_start_time"
        ) is None:

            review_reasons.append(
                "Missing session.trial_start_time."
            )

        if session.get(
            "trial_end_time"
        ) is None:

            review_reasons.append(
                "Missing session.trial_end_time."
            )

    # --------------------------------------------------------
    # Manual validation
    # --------------------------------------------------------

    manual_validation = metadata.get(
        "manual_validation",
        {},
    )

    if not manual_validation:

        review_reasons.append(
            "Missing manual_validation section."
        )

    else:

        expected_manual_fields = [
            "object_picked",
            "object_placed_on_shelf",
            "object_dropped",
            "unsafe_robot_motion",
            "reset_required",
            "researcher_helped_task",
        ]

        for field in expected_manual_fields:

            if field not in manual_validation:

                review_reasons.append(
                    f"Missing manual_validation.{field}"
                )

    # --------------------------------------------------------
    # Video validation
    # --------------------------------------------------------

    video_validation = metadata.get(
        "video_validation",
        {},
    )

    if not video_validation:

        review_reasons.append(
            "Missing video_validation section."
        )

    else:

        if (
            "video_covers_full_trial"
            not in video_validation
        ):

            review_reasons.append(
                "Missing video_validation.video_covers_full_trial"
            )

        if (
            "camera_freeze_or_dropout"
            not in video_validation
        ):

            review_reasons.append(
                "Missing video_validation.camera_freeze_or_dropout"
            )

        if (
            video_validation.get(
                "video_covers_full_trial"
            )
            is False
        ):

            review_reasons.append(
                "Video does not cover the full trial."
            )

        if (
            video_validation.get(
                "camera_freeze_or_dropout"
            )
            is True
        ):

            review_reasons.append(
                "Camera freeze/dropout reported in video validation."
            )

    # --------------------------------------------------------
    # Task result
    # --------------------------------------------------------

    if (
        metadata.get(
            "task_success"
        )
        is False
    ):

        review_reasons.append(
            "Trial marked unsuccessful."
        )

    # ========================================================
    # Intervention policy
    # ========================================================
    #
    # T01 = LEARNING TRIAL
    #   - Technician intervention is allowed.
    #   - Intervention is still recorded in metadata.
    #   - Intervention alone does NOT cause REVIEW or FAIL.
    #
    # T02 / T03 = EXECUTION TRIALS
    #   - ANY technician/researcher intervention causes REVIEW.
    #   - Count and severity are still recorded for analysis.
    #
    # Metadata inconsistencies remain REVIEW conditions
    # regardless of trial number.
    #
    # Other technical/data-quality checks remain independent.
    # ========================================================

    trial_id = str(
        metadata.get(
            "trial_id",
            "",
        )
    ).strip().upper()

    intervention = to_bool(
        metadata.get(
            "technician_intervention",
            False,
        )
    )

    severity = str(
        metadata.get(
            "intervention_severity",
            "none",
        )
    ).strip().lower()

    try:
        intervention_count = int(
            metadata.get(
                "intervention_count",
                0,
            )
        )
    except (TypeError, ValueError):
        intervention_count = 0

    # --------------------------------------------------------
    # No intervention recorded
    # --------------------------------------------------------

    if not intervention:

        if intervention_count != 0:

            review_reasons.append(
                "technician_intervention=false but "
                f"intervention_count={intervention_count}. "
                "Check metadata consistency."
            )

        elif severity != "none":

            review_reasons.append(
                "technician_intervention=false but "
                f"intervention_severity={severity}. "
                "Check metadata consistency."
            )

        else:

            informational_notes.append(
                "No technician/researcher intervention recorded."
            )

    # --------------------------------------------------------
    # Intervention recorded
    # --------------------------------------------------------

    else:

        # ----------------------------------------------------
        # Metadata consistency checks
        # ----------------------------------------------------

        if intervention_count <= 0:

            review_reasons.append(
                "Technician/researcher intervention is marked true "
                "but intervention_count is not greater than zero."
            )

        if severity == "none":

            review_reasons.append(
                "technician_intervention=true but "
                "intervention_severity=none. "
                "Check metadata consistency."
            )

        elif severity not in [
            "minor",
            "major",
        ]:

            review_reasons.append(
                f"Unknown intervention severity '{severity}'. "
                "Check metadata."
            )

        # ----------------------------------------------------
        # T01 = learning trial
        # Intervention allowed and recorded.
        # ----------------------------------------------------

        if trial_id == "T01":

            informational_notes.append(
                f"Technician/researcher intervention occurred during "
                f"learning trial T01 "
                f"({intervention_count} intervention(s), "
                f"severity={severity}); "
                f"intervention does not invalidate the learning trial."
            )

        # ----------------------------------------------------
        # T02 / T03 = execution trials
        # ANY intervention => REVIEW
        # ----------------------------------------------------

        elif trial_id in [
            "T02",
            "T03",
        ]:

            review_reasons.append(
                f"Technician/researcher intervention occurred during "
                f"execution trial {trial_id} "
                f"({intervention_count} intervention(s), "
                f"severity={severity})."
            )

        # ----------------------------------------------------
        # Unexpected trial ID
        # ----------------------------------------------------

        else:

            review_reasons.append(
                f"Unknown trial_id '{trial_id}' while evaluating "
                "technician intervention."
            )

    return (
        issues,
        review_reasons,
        informational_notes,
    )


# ============================================================
# SESSION FILE CHECK
# ============================================================

def check_session_files(
    trial_dir,
    metadata,
):
    issues = []
    review_reasons = []

    session = metadata.get(
        "session",
        {},
    )

    rosbag_path = resolve_path(
        trial_dir,
        session.get(
            "rosbag"
        ),
    )

    events_path = resolve_path(
        trial_dir,
        session.get(
            "events_csv"
        ),
    )

    if (
        rosbag_path is not None
        and not rosbag_path.exists()
    ):

        issues.append(
            f"Referenced rosbag does not exist: {rosbag_path}"
        )

    if (
        events_path is not None
        and not events_path.exists()
    ):

        issues.append(
            f"Referenced events.csv does not exist: {events_path}"
        )

    video = metadata.get(
        "video",
        {},
    )

    for key, value in video.items():

        if value is None:
            continue

        value_str = str(
            value
        )

        # ROS topics start with "/".
        if value_str.startswith(
            "/"
        ):
            continue

        video_path = resolve_path(
            trial_dir,
            value_str,
        )

        if not video_path.exists():

            review_reasons.append(
                f"Referenced video file missing: "
                f"{key} -> {video_path}"
            )

    return (
        issues,
        review_reasons,
    )


# ============================================================
# BASIC TELEMETRY CHECK
# ============================================================

def check_telemetry_basic(
    trial_dir,
):
    issues = []
    review_reasons = []
    telemetry_summary = {}

    telemetry_path = (
        trial_dir
        / "telemetry.csv"
    )

    if not telemetry_path.exists():

        issues.append(
            "Missing telemetry.csv."
        )

        return (
            issues,
            review_reasons,
            telemetry_summary,
            None,
        )

    try:

        df = pd.read_csv(
            telemetry_path
        )

    except Exception as exc:

        issues.append(
            f"Could not read telemetry.csv: {exc}"
        )

        return (
            issues,
            review_reasons,
            telemetry_summary,
            None,
        )

    telemetry_summary[
        "num_rows"
    ] = int(
        len(df)
    )

    telemetry_summary[
        "columns"
    ] = list(
        df.columns
    )

    if (
        len(df)
        < MIN_TELEMETRY_ROWS
    ):

        issues.append(
            f"Telemetry has too few rows: {len(df)} rows."
        )

    for col in REQUIRED_TELEMETRY_COLUMNS:

        if col not in df.columns:

            issues.append(
                f"Missing required telemetry column: {col}"
            )

    missing_optional = []

    for col in OPTIONAL_TELEMETRY_COLUMNS:

        if col not in df.columns:

            missing_optional.append(
                col
            )

    telemetry_summary[
        "missing_optional_columns"
    ] = (
        missing_optional
    )

    # --------------------------------------------------------
    # Time duration
    # --------------------------------------------------------

    if "time" in df.columns:

        t = (
            pd.to_numeric(
                df["time"],
                errors="coerce",
            )
            .dropna()
        )

        if len(t) >= 2:

            telemetry_summary[
                "duration_seconds"
            ] = float(
                t.iloc[-1]
                - t.iloc[0]
            )

            if (
                telemetry_summary[
                    "duration_seconds"
                ]
                <= 0
            ):

                issues.append(
                    "Telemetry time duration is not positive."
                )

        else:

            issues.append(
                "Telemetry time column has fewer than 2 valid values."
            )

    # --------------------------------------------------------
    # Missing ratios
    # --------------------------------------------------------

    for col in REQUIRED_TELEMETRY_COLUMNS:

        if col in df.columns:

            numeric = pd.to_numeric(
                df[col],
                errors="coerce",
            )

            missing_ratio = float(
                numeric.isna().mean()
            )

            telemetry_summary[
                f"missing_ratio_{col}"
            ] = missing_ratio

            if (
                missing_ratio
                > 0.5
            ):

                review_reasons.append(
                    f"High missing ratio in {col}: "
                    f"{missing_ratio:.2f}"
                )

    # --------------------------------------------------------
    # End-effector coverage
    # --------------------------------------------------------

    if all(
        col in df.columns
        for col in [
            "ee_x",
            "ee_y",
            "ee_z",
        ]
    ):

        ee = (
            df[
                [
                    "ee_x",
                    "ee_y",
                    "ee_z",
                ]
            ]
            .apply(
                pd.to_numeric,
                errors="coerce",
            )
        )

        ee_missing_ratio = float(
            ee.isna()
            .all(
                axis=1
            )
            .mean()
        )

        telemetry_summary[
            "ee_missing_ratio"
        ] = (
            ee_missing_ratio
        )

        if (
            ee_missing_ratio
            > 0.9
        ):

            review_reasons.append(
                "End-effector Cartesian pose mostly missing. "
                "Check TF extraction."
            )

    return (
        issues,
        review_reasons,
        telemetry_summary,
        df,
    )


# ============================================================
# TELEMETRY HEALTH
# ============================================================

def check_telemetry_health(
    df,
    metadata,
):
    issues = []
    review_reasons = []
    health_summary = {}

    if (
        df is None
        or len(df) == 0
    ):

        issues.append(
            "Cannot run telemetry health checks because telemetry is empty."
        )

        return (
            issues,
            review_reasons,
            health_summary,
        )

    task_success = to_bool(
        metadata.get(
            "task_success",
            False,
        )
    )

    # --------------------------------------------------------
    # 1. Timestamp gaps
    # --------------------------------------------------------

    if "time" in df.columns:

        t = (
            pd.to_numeric(
                df["time"],
                errors="coerce",
            )
            .dropna()
            .to_numpy()
        )

        if len(t) >= 2:

            gaps = np.diff(
                t
            )

            max_gap = float(
                np.max(
                    gaps
                )
            )

            mean_gap = float(
                np.mean(
                    gaps
                )
            )

            health_summary[
                "max_time_gap_seconds"
            ] = max_gap

            health_summary[
                "mean_time_gap_seconds"
            ] = mean_gap

            if max_gap > 2.0:

                review_reasons.append(
                    f"Large timestamp gap detected: "
                    f"{max_gap:.3f}s."
                )

            elif max_gap > 1.0:

                health_summary[
                    "timestamp_gap_informational"
                ] = (
                    f"Brief timestamp gap detected: "
                    f"{max_gap:.3f}s."
                )

    # --------------------------------------------------------
    # 2. Object path
    # --------------------------------------------------------

    object_path = (
        path_length_from_columns(
            df,
            [
                "object_x",
                "object_y",
                "object_z",
            ],
        )
    )

    health_summary[
        "object_path_length_healthcheck"
    ] = object_path

    if (
        object_path is not None
        and task_success
        and object_path
        < MIN_OBJECT_PATH_FOR_SUCCESS
    ):

        review_reasons.append(
            "Object path length is near zero despite "
            "task_success=true. Check object tracking, "
            "trial segmentation, or manual label."
        )

    # --------------------------------------------------------
    # 3. Object flatline
    # --------------------------------------------------------

    object_ranges = {}

    for col in [
        "object_x",
        "object_y",
        "object_z",
    ]:

        r = signal_range(
            df,
            col,
        )

        object_ranges[
            col
        ] = r

        health_summary[
            f"range_{col}"
        ] = r

    if all(
        r is not None
        and r < 0.005
        for r
        in object_ranges.values()
    ):

        review_reasons.append(
            "Object tracking appears nearly flat across x/y/z."
        )

    # --------------------------------------------------------
    # 4. Gripper flatline
    # --------------------------------------------------------

    gripper_range = (
        signal_range(
            df,
            "gripper_state",
        )
    )

    health_summary[
        "range_gripper_state"
    ] = gripper_range

    if (
        gripper_range is not None
        and task_success
        and gripper_range
        < MIN_GRIPPER_RANGE_FOR_SUCCESS
    ):

        review_reasons.append(
            "Gripper state is nearly flat during a successful "
            "pick-place trial. Check whether gripper motion "
            "was captured correctly."
        )

    # --------------------------------------------------------
    # 5. Base path
    # --------------------------------------------------------

    base_path = (
        path_length_from_columns(
            df,
            [
                "base_x",
                "base_y",
            ],
        )
    )

    health_summary[
        "base_path_length_healthcheck"
    ] = base_path

    # No upper base-path threshold.
    #
    # Different interfaces can naturally produce different
    # movement magnitudes. This is an experimental metric,
    # not a validity failure.

    # --------------------------------------------------------
    # 6. Joint movement
    # --------------------------------------------------------

    joint_cols = [
        f"joint_{i}"
        for i in range(
            1,
            8,
        )
        if f"joint_{i}"
        in df.columns
    ]

    joint_ranges = []

    for col in joint_cols:

        r = signal_range(
            df,
            col,
        )

        health_summary[
            f"range_{col}"
        ] = r

        if r is not None:

            joint_ranges.append(
                r
            )

    if len(
        joint_ranges
    ) > 0:

        total_joint_range = float(
            np.sum(
                joint_ranges
            )
        )

        health_summary[
            "total_joint_range"
        ] = total_joint_range

        # ----------------------------------------------------
        # Account for torso-assisted and EE motion
        # ----------------------------------------------------

        torso_range = signal_range(
            df,
            "torso_lift_joint",
        )

        health_summary[
            "range_torso_lift_joint"
        ] = torso_range

        ee_ranges = {}

        for col in [
            "ee_x",
            "ee_y",
            "ee_z",
        ]:

            r = signal_range(
                df,
                col,
            )

            ee_ranges[col] = r

            health_summary[
                f"range_{col}"
            ] = r

        valid_ee_ranges = [
            float(v)
            for v in ee_ranges.values()
            if v is not None
            and pd.notna(v)
        ]

        max_ee_range = (
            max(valid_ee_ranges)
            if valid_ee_ranges
            else None
        )

        arm_motion_small = (
            total_joint_range
            < MIN_TOTAL_JOINT_RANGE_FOR_SUCCESS
        )

        torso_motion_small = (
            torso_range is None
            or pd.isna(torso_range)
            or float(torso_range) < 0.02
        )

        ee_motion_small = (
            max_ee_range is None
            or float(max_ee_range) < 0.02
        )

        if (
            task_success
            and arm_motion_small
            and torso_motion_small
            and ee_motion_small
        ):

            review_reasons.append(
                "Arm, torso, and end-effector motion are all very small "
                "despite task_success=true. Check whether the trial "
                "segment captured the actual task."
            )

    return (
        issues,
        review_reasons,
        health_summary,
    )


# ============================================================
# QUALITY REPORT
# ============================================================

def check_quality_report_health(
    trial_dir,
):
    issues = []
    review_reasons = []
    informational_notes = []
    quality_summary = {}

    quality_path = (
        trial_dir
        / "quality_report.json"
    )

    if not quality_path.exists():

        informational_notes.append(
            "quality_report.json not found yet. "
            "Run analyze_trial.py for derived quality metrics."
        )

        return (
            issues,
            review_reasons,
            informational_notes,
            quality_summary,
        )

    try:

        report = load_json(
            quality_path
        )

    except Exception as exc:

        informational_notes.append(
            f"Could not read quality_report.json: {exc}"
        )

        return (
            issues,
            review_reasons,
            informational_notes,
            quality_summary,
        )

    metrics = report.get(
        "metrics",
        {},
    )

    for key, value in metrics.items():

        quality_summary[
            key
        ] = value

    # --------------------------------------------------------
    # Extreme jerk sanity check
    # --------------------------------------------------------

    joint_jerk = metrics.get(
        "joint_jerk"
    )

    if joint_jerk is not None:

        try:

            joint_jerk_value = float(
                joint_jerk
            )

            if (
                joint_jerk_value
                > EXTREME_JOINT_JERK_THRESHOLD
            ):

                review_reasons.append(
                    f"Joint jerk is extremely high: "
                    f"{joint_jerk_value:.3f}. "
                    "Check for timestamp issues or noisy telemetry."
                )

        except Exception:
            pass

    # --------------------------------------------------------
    # Object path consistency
    # --------------------------------------------------------

    object_path = metrics.get(
        "object_path_length"
    )

    task_success = report.get(
        "task_success"
    )

    if (
        object_path is not None
        and task_success is True
    ):

        try:

            object_path_value = float(
                object_path
            )

            if (
                object_path_value
                < MIN_OBJECT_PATH_FOR_SUCCESS
            ):

                review_reasons.append(
                    "quality_report object_path_length is near "
                    "zero despite task_success=true."
                )

        except Exception:
            pass

    return (
        issues,
        review_reasons,
        informational_notes,
        quality_summary,
    )


# ============================================================
# FINAL STATUS POLICY
# ============================================================

def decide_status(
    issues,
    review_reasons,
):
    """
    PASS:
        Required experimental data is present and usable,
        and no review condition is present.

    REVIEW:
        Data is analyzable, but a genuine data-validity
        concern or post-learning technician intervention
        requires inspection.

    FAIL:
        Critical required data is missing or corrupt.

    Intervention policy:
        T01:
            Learning trial. Technician intervention is allowed
            and does not affect status by itself.

        T02/T03:
            Execution trials. Any technician/researcher
            intervention causes REVIEW.

    Metadata inconsistencies concerning intervention fields
    remain REVIEW conditions.

    Normal differences in movement magnitude between REAL,
    2D and VR do not affect status.
    """

    if len(
        issues
    ) > 0:

        return "fail"

    if len(
        review_reasons
    ) > 0:

        return "review"

    return "pass"


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "trial_dir",
        help=(
            "Trial folder, e.g. "
            "data/P01_VR_T01"
        ),
    )

    args = parser.parse_args()

    trial_dir = Path(
        args.trial_dir
    )

    metadata_path = (
        trial_dir
        / "metadata.yaml"
    )

    report = {
        "trial_dir": str(
            trial_dir
        ),

        "status": None,

        "issues": [],

        "review_reasons": [],

        "informational_notes": [],

        "metadata_summary": {},

        "telemetry_summary": {},

        "telemetry_health_summary": {},

        "quality_summary": {},
    }

    # --------------------------------------------------------
    # Metadata existence
    # --------------------------------------------------------

    if not metadata_path.exists():

        report[
            "status"
        ] = "fail"

        report[
            "issues"
        ].append(
            "Missing metadata.yaml."
        )

        save_json(
            report,
            trial_dir
            / "validation_report.json",
        )

        print(
            f"Saved validation report: "
            f"{trial_dir / 'validation_report.json'}"
        )

        print(
            "Status: fail"
        )

        return

    metadata = load_yaml(
        metadata_path
    )

    report[
        "metadata_summary"
    ] = {

        "participant_id": metadata.get(
            "participant_id"
        ),

        "condition": metadata.get(
            "condition"
        ),

        "trial_id": metadata.get(
            "trial_id"
        ),

        "training_group": metadata.get(
            "training_group"
        ),

        "task_success": metadata.get(
            "task_success"
        ),

        "technician_intervention": metadata.get(
            "technician_intervention"
        ),

        "intervention_severity": metadata.get(
            "intervention_severity"
        ),

        "intervention_count": metadata.get(
            "intervention_count",
            0,
        ),
    }

    # --------------------------------------------------------
    # Run checks
    # --------------------------------------------------------

    (
        metadata_issues,
        metadata_reviews,
        metadata_info,
    ) = check_metadata(
        trial_dir,
        metadata,
    )

    (
        file_issues,
        file_reviews,
    ) = check_session_files(
        trial_dir,
        metadata,
    )

    (
        telemetry_issues,
        telemetry_reviews,
        telemetry_summary,
        df,
    ) = check_telemetry_basic(
        trial_dir
    )

    (
        health_issues,
        health_reviews,
        health_summary,
    ) = check_telemetry_health(
        df,
        metadata,
    )

    (
        quality_issues,
        quality_reviews,
        quality_info,
        quality_summary,
    ) = check_quality_report_health(
        trial_dir
    )

    # --------------------------------------------------------
    # Aggregate
    # --------------------------------------------------------

    report[
        "issues"
    ].extend(
        metadata_issues
    )

    report[
        "issues"
    ].extend(
        file_issues
    )

    report[
        "issues"
    ].extend(
        telemetry_issues
    )

    report[
        "issues"
    ].extend(
        health_issues
    )

    report[
        "issues"
    ].extend(
        quality_issues
    )

    report[
        "review_reasons"
    ].extend(
        metadata_reviews
    )

    report[
        "review_reasons"
    ].extend(
        file_reviews
    )

    report[
        "review_reasons"
    ].extend(
        telemetry_reviews
    )

    report[
        "review_reasons"
    ].extend(
        health_reviews
    )

    report[
        "review_reasons"
    ].extend(
        quality_reviews
    )

    report[
        "informational_notes"
    ].extend(
        metadata_info
    )

    report[
        "informational_notes"
    ].extend(
        quality_info
    )

    # --------------------------------------------------------
    # Remove duplicate messages
    # --------------------------------------------------------

    report[
        "issues"
    ] = list(
        dict.fromkeys(
            report[
                "issues"
            ]
        )
    )

    report[
        "review_reasons"
    ] = list(
        dict.fromkeys(
            report[
                "review_reasons"
            ]
        )
    )

    report[
        "informational_notes"
    ] = list(
        dict.fromkeys(
            report[
                "informational_notes"
            ]
        )
    )

    # --------------------------------------------------------
    # Summaries
    # --------------------------------------------------------

    report[
        "telemetry_summary"
    ] = telemetry_summary

    report[
        "telemetry_health_summary"
    ] = health_summary

    report[
        "quality_summary"
    ] = quality_summary

    # --------------------------------------------------------
    # Final status
    # --------------------------------------------------------

    report[
        "status"
    ] = decide_status(
        report[
            "issues"
        ],

        report[
            "review_reasons"
        ],
    )

    output_path = (
        trial_dir
        / "validation_report.json"
    )

    save_json(
        report,
        output_path,
    )

    # --------------------------------------------------------
    # Terminal output
    # --------------------------------------------------------

    print(
        f"Saved validation report: "
        f"{output_path}"
    )

    print(
        f"Status: "
        f"{report['status']}"
    )

    if report[
        "issues"
    ]:

        print("")
        print(
            "Issues:"
        )

        for issue in report[
            "issues"
        ]:

            print(
                f"  - {issue}"
            )

    if report[
        "review_reasons"
    ]:

        print("")
        print(
            "Review reasons:"
        )

        for reason in report[
            "review_reasons"
        ]:

            print(
                f"  - {reason}"
            )

    if report[
        "informational_notes"
    ]:

        print("")
        print(
            "Informational notes:"
        )

        for note in report[
            "informational_notes"
        ]:

            print(
                f"  - {note}"
            )

    print("")
    print(
        "Telemetry health:"
    )

    for (
        key,
        value,
    ) in health_summary.items():

        print(
            f"  {key}: {value}"
        )


if __name__ == "__main__":
    main()