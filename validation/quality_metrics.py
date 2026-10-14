#!/usr/bin/env python3

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


# ---------------------------------------------------------------------
# Main tuning parameters
# ---------------------------------------------------------------------

RESAMPLE_HZ = 20.0
RESAMPLE_DT = 1.0 / RESAMPLE_HZ

SMOOTH_WINDOW_SECONDS = 0.25

OBJECT_STALE_EPS = 0.001
BASE_STALE_EPS = 0.001

# Minimum individual movement used when counting meaningful
# gripper direction changes/reversals.
GRIPPER_MOVEMENT_EPS = 0.0005

# Minimum total gripper range required before chatter/cycle
# metrics are considered valid.
GRIPPER_FLATLINE_THRESHOLD = 0.001

# Jump-speed thresholds
EE_JUMP_SPEED_THRESHOLD = 1.5
OBJECT_JUMP_SPEED_THRESHOLD = 1.5
BASE_JUMP_SPEED_THRESHOLD = 1.0

# If more than this number of implausible EE jumps are detected,
# Cartesian trajectory metrics are considered unreliable.
EE_MAX_ALLOWED_JUMPS = 5


# ---------------------------------------------------------------------
# Basic file helpers
# ---------------------------------------------------------------------

def load_metadata(trial_dir):
    trial_dir = Path(trial_dir)
    metadata_path = trial_dir / "metadata.yaml"

    with metadata_path.open("r") as f:
        return yaml.safe_load(f)


def load_telemetry(trial_dir):
    trial_dir = Path(trial_dir)
    telemetry_path = trial_dir / "telemetry.csv"

    df = pd.read_csv(telemetry_path)

    if "time" not in df.columns:
        raise ValueError(
            "telemetry.csv must contain a 'time' column."
        )

    df["time"] = pd.to_numeric(
        df["time"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["time"]
    )

    df = df.sort_values(
        "time"
    )

    return df


def save_json(data, output_path):
    output_path = Path(output_path)

    with output_path.open("w") as f:
        json.dump(
            data,
            f,
            indent=2
        )


# ---------------------------------------------------------------------
# Numeric helpers
# ---------------------------------------------------------------------

def numeric_series(df, col):
    if df is None:
        return None

    if col not in df.columns:
        return None

    return pd.to_numeric(
        df[col],
        errors="coerce"
    )


def numeric_matrix(df, cols):
    if df is None:
        return None

    if not all(
        col in df.columns
        for col in cols
    ):
        return None

    return (
        df[cols]
        .apply(
            pd.to_numeric,
            errors="coerce"
        )
    )


def remove_duplicate_timestamps(df):
    """
    Keeps one row per timestamp by averaging numeric values.

    IMPORTANT:
    All input columns are preserved, even when a column contains
    only NaN values. This prevents optional streams such as
    object_x/object_y/object_z from disappearing during resampling.
    """

    if df is None or len(df) == 0:
        return df

    df = df.copy()

    if "time" not in df.columns:
        return df

    df["time"] = pd.to_numeric(
        df["time"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["time"]
    )

    value_cols = [
        col
        for col in df.columns
        if col != "time"
    ]

    for col in value_cols:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    if len(value_cols) == 0:
        return (
            df[["time"]]
            .drop_duplicates(
                subset=["time"]
            )
            .sort_values("time")
            .reset_index(drop=True)
        )

    grouped = (
        df.groupby(
            "time",
            as_index=False,
            dropna=False
        )[value_cols]
        .mean()
    )

    # Explicitly restore any requested columns if pandas somehow
    # omitted one because it contained no usable values.
    for col in value_cols:
        if col not in grouped.columns:
            grouped[col] = np.nan

    return grouped[
        ["time"] + value_cols
    ]


def resample_uniform(
    df,
    cols,
    dt=RESAMPLE_DT
):
    """
    Resamples selected columns to a uniform time grid.

    Missing streams are handled safely:
    - missing requested column -> None
    - entirely empty requested signal -> column remains NaN
    - no valid timestamps -> None

    This function never invents zeros for unavailable signals.
    """

    if df is None or len(df) < 2:
        return None

    required_cols = [
        "time"
    ] + list(cols)

    if not all(
        col in df.columns
        for col in required_cols
    ):
        return None

    working = df[
        required_cols
    ].copy()

    working["time"] = pd.to_numeric(
        working["time"],
        errors="coerce"
    )

    for col in cols:
        working[col] = pd.to_numeric(
            working[col],
            errors="coerce"
        )

    working = working.dropna(
        subset=["time"]
    )

    working = working.sort_values(
        "time"
    )

    working = remove_duplicate_timestamps(
        working
    )

    if working is None or len(working) < 2:
        return None

    # Safety check after duplicate removal.
    for col in cols:
        if col not in working.columns:
            working[col] = np.nan

    start_t = float(
        working["time"].iloc[0]
    )

    end_t = float(
        working["time"].iloc[-1]
    )

    if end_t <= start_t:
        return None

    new_time = np.arange(
        start_t,
        end_t,
        dt
    )

    if len(new_time) < 5:
        return None

    resampled = pd.DataFrame({
        "time": new_time
    })

    for col in cols:

        if col not in working.columns:
            resampled[col] = np.nan
            continue

        values = (
            working[
                ["time", col]
            ]
            .dropna(
                subset=[col]
            )
        )

        # Need at least two real observations to interpolate.
        if len(values) < 2:
            resampled[col] = np.nan
            continue

        resampled[col] = np.interp(
            new_time,
            values["time"].to_numpy(),
            values[col].to_numpy()
        )

    return resampled


def smooth_dataframe(
    df,
    cols,
    window_seconds=SMOOTH_WINDOW_SECONDS,
    dt=RESAMPLE_DT
):
    if df is None:
        return None

    window_samples = max(
        3,
        int(
            round(
                window_seconds / dt
            )
        )
    )

    if window_samples % 2 == 0:
        window_samples += 1

    smoothed = df.copy()

    for col in cols:

        if col not in smoothed.columns:
            continue

        smoothed[col] = (
            pd.to_numeric(
                smoothed[col],
                errors="coerce"
            )
            .rolling(
                window=window_samples,
                center=True,
                min_periods=1
            )
            .mean()
        )

    return smoothed


def path_length(df, cols):
    if df is None:
        return None

    if not all(
        col in df.columns
        for col in cols
    ):
        return None

    arr = (
        df[cols]
        .apply(
            pd.to_numeric,
            errors="coerce"
        )
        .to_numpy()
    )

    arr = arr[
        ~np.isnan(arr).any(axis=1)
    ]

    if len(arr) < 2:
        return None

    diffs = np.diff(
        arr,
        axis=0
    )

    return float(
        np.sum(
            np.linalg.norm(
                diffs,
                axis=1
            )
        )
    )


def signal_range(df, col):
    if df is None:
        return None

    if col not in df.columns:
        return None

    values = (
        pd.to_numeric(
            df[col],
            errors="coerce"
        )
        .dropna()
    )

    if len(values) < 2:
        return None

    return float(
        values.max()
        - values.min()
    )


def compute_jerk_metrics(df, cols):
    """
    Computes jerk after:
    1. duplicate timestamp removal
    2. uniform resampling
    3. smoothing

    Returns RMS jerk and peak jerk using vector norm.
    """

    if df is None:
        return {
            "jerk_rms": None,
            "jerk_peak": None,
            "resampled_rows": 0,
        }

    if not all(
        col in df.columns
        for col in cols
    ):
        return {
            "jerk_rms": None,
            "jerk_peak": None,
            "resampled_rows": 0,
        }

    uniform = resample_uniform(
        df,
        cols
    )

    if uniform is None:
        return {
            "jerk_rms": None,
            "jerk_peak": None,
            "resampled_rows": 0,
        }

    uniform = smooth_dataframe(
        uniform,
        cols
    )

    if not all(
        col in uniform.columns
        for col in cols
    ):
        return {
            "jerk_rms": None,
            "jerk_peak": None,
            "resampled_rows": int(
                len(uniform)
            ),
        }

    values = (
        uniform[cols]
        .apply(
            pd.to_numeric,
            errors="coerce"
        )
        .to_numpy()
    )

    if np.isnan(values).all():
        return {
            "jerk_rms": None,
            "jerk_peak": None,
            "resampled_rows": int(
                len(uniform)
            ),
        }

    values_df = pd.DataFrame(
        values,
        columns=cols
    )

    # Require each dimension to have enough real information.
    valid_counts = (
        values_df
        .notna()
        .sum()
    )

    if (
        valid_counts < 2
    ).any():
        return {
            "jerk_rms": None,
            "jerk_peak": None,
            "resampled_rows": int(
                len(uniform)
            ),
        }

    values_df = (
        values_df
        .interpolate(
            limit_direction="both"
        )
    )

    if values_df.isna().any().any():
        return {
            "jerk_rms": None,
            "jerk_peak": None,
            "resampled_rows": int(
                len(uniform)
            ),
        }

    values = values_df.to_numpy()

    if len(values) < 5:
        return {
            "jerk_rms": None,
            "jerk_peak": None,
            "resampled_rows": int(
                len(uniform)
            ),
        }

    dt = RESAMPLE_DT

    velocity = np.gradient(
        values,
        dt,
        axis=0
    )

    acceleration = np.gradient(
        velocity,
        dt,
        axis=0
    )

    jerk = np.gradient(
        acceleration,
        dt,
        axis=0
    )

    jerk_norm = np.linalg.norm(
        jerk,
        axis=1
    )

    if (
        len(jerk_norm) == 0
        or np.isnan(jerk_norm).all()
    ):
        return {
            "jerk_rms": None,
            "jerk_peak": None,
            "resampled_rows": int(
                len(uniform)
            ),
        }

    return {
        "jerk_rms": float(
            np.sqrt(
                np.nanmean(
                    jerk_norm ** 2
                )
            )
        ),
        "jerk_peak": float(
            np.nanmax(
                jerk_norm
            )
        ),
        "resampled_rows": int(
            len(uniform)
        ),
    }


def compute_stale_ratio(
    df,
    cols,
    eps
):
    if df is None:
        return None

    if not all(
        col in df.columns
        for col in ["time"] + cols
    ):
        return None

    arr = (
        df[
            ["time"] + cols
        ]
        .apply(
            pd.to_numeric,
            errors="coerce"
        )
        .dropna()
        .to_numpy()
    )

    if len(arr) < 2:
        return None

    xyz = arr[:, 1:]

    diffs = np.linalg.norm(
        np.diff(
            xyz,
            axis=0
        ),
        axis=1
    )

    stale = (
        diffs < eps
    )

    return float(
        np.mean(
            stale
        )
    )


def compute_jump_metrics(
    df,
    cols,
    speed_threshold
):
    if df is None:
        return {
            "jump_count": None,
            "max_speed": None,
        }

    if not all(
        col in df.columns
        for col in ["time"] + cols
    ):
        return {
            "jump_count": None,
            "max_speed": None,
        }

    arr = (
        df[
            ["time"] + cols
        ]
        .apply(
            pd.to_numeric,
            errors="coerce"
        )
        .dropna()
        .to_numpy()
    )

    if len(arr) < 2:
        return {
            "jump_count": None,
            "max_speed": None,
        }

    t = arr[:, 0]
    xyz = arr[:, 1:]

    dt = np.diff(
        t
    )

    dist = np.linalg.norm(
        np.diff(
            xyz,
            axis=0
        ),
        axis=1
    )

    valid = (
        dt > 1e-6
    )

    if valid.sum() == 0:
        return {
            "jump_count": None,
            "max_speed": None,
        }

    speed = (
        dist[valid]
        / dt[valid]
    )

    if len(speed) == 0:
        return {
            "jump_count": None,
            "max_speed": None,
        }

    jump_count = int(
        np.sum(
            speed
            > speed_threshold
        )
    )

    max_speed = float(
        np.max(
            speed
        )
    )

    return {
        "jump_count": jump_count,
        "max_speed": max_speed,
    }


def clean_path_length_with_speed_filter(
    df,
    cols,
    speed_threshold
):
    """
    Computes path length while ignoring impossible jumps.

    Missing streams return None. No rows or values are invented.
    """

    if df is None:
        return None

    if not all(
        col in df.columns
        for col in ["time"] + cols
    ):
        return None

    arr = (
        df[
            ["time"] + cols
        ]
        .apply(
            pd.to_numeric,
            errors="coerce"
        )
        .dropna()
        .to_numpy()
    )

    if len(arr) < 2:
        return None

    t = arr[:, 0]
    xyz = arr[:, 1:]

    dt = np.diff(
        t
    )

    diffs = np.diff(
        xyz,
        axis=0
    )

    dist = np.linalg.norm(
        diffs,
        axis=1
    )

    valid_dt = (
        dt > 1e-6
    )

    if valid_dt.sum() == 0:
        return None

    speed = np.full(
        len(dist),
        np.nan,
        dtype=float
    )

    speed[valid_dt] = (
        dist[valid_dt]
        / dt[valid_dt]
    )

    valid_motion = (
        valid_dt
        & np.isfinite(speed)
        & (
            speed
            <= speed_threshold
        )
    )

    if valid_motion.sum() == 0:
        return 0.0

    return float(
        np.sum(
            dist[
                valid_motion
            ]
        )
    )


def count_directional_reversals(
    values,
    eps=GRIPPER_MOVEMENT_EPS
):
    """
    Counts meaningful direction changes in gripper movement.
    Tiny noise is ignored.
    """

    values = (
        pd.Series(
            values
        )
        .dropna()
        .to_numpy()
    )

    if len(values) < 3:
        return 0

    diffs = np.diff(
        values
    )

    directions = []

    for d in diffs:

        if abs(d) < eps:
            continue

        if d > 0:
            directions.append(1)
        else:
            directions.append(-1)

    if len(directions) < 2:
        return 0

    reversals = 0

    for i in range(
        1,
        len(directions)
    ):
        if (
            directions[i]
            != directions[i - 1]
        ):
            reversals += 1

    return int(
        reversals
    )


def count_gripper_cycles(
    values,
    eps=GRIPPER_MOVEMENT_EPS
):
    """
    Rough open/close cycle estimate
    based on directional reversals.
    """

    reversals = (
        count_directional_reversals(
            values,
            eps=eps
        )
    )

    return int(
        reversals // 2
    )


# ---------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------

def analyze_trial(trial_dir):

    trial_dir = Path(
        trial_dir
    )

    metadata = load_metadata(
        trial_dir
    )

    df = load_telemetry(
        trial_dir
    )

    metrics = {}

    participant_id = metadata.get(
        "participant_id"
    )

    condition = metadata.get(
        "condition"
    )

    trial_id = metadata.get(
        "trial_id"
    )

    task_success = metadata.get(
        "task_success"
    )

    technician_intervention = metadata.get(
        "technician_intervention"
    )

    notes = metadata.get(
        "notes"
    )

    # -------------------------------------------------------------
    # Time
    # -------------------------------------------------------------

    t = (
        pd.to_numeric(
            df["time"],
            errors="coerce"
        )
        .dropna()
    )

    if len(t) >= 2:

        metrics[
            "completion_time"
        ] = float(
            t.iloc[-1]
            - t.iloc[0]
        )

        metrics[
            "num_rows"
        ] = int(
            len(df)
        )

        diffs = np.diff(
            t.to_numpy()
        )

        metrics[
            "min_time_gap"
        ] = (
            float(
                np.min(
                    diffs
                )
            )
            if len(diffs) > 0
            else None
        )

        metrics[
            "mean_time_gap"
        ] = (
            float(
                np.mean(
                    diffs
                )
            )
            if len(diffs) > 0
            else None
        )

        metrics[
            "max_time_gap"
        ] = (
            float(
                np.max(
                    diffs
                )
            )
            if len(diffs) > 0
            else None
        )

        metrics[
            "duplicate_timestamp_count"
        ] = int(
            df["time"]
            .duplicated()
            .sum()
        )

    else:

        metrics[
            "completion_time"
        ] = None

        metrics[
            "num_rows"
        ] = int(
            len(df)
        )

        metrics[
            "min_time_gap"
        ] = None

        metrics[
            "mean_time_gap"
        ] = None

        metrics[
            "max_time_gap"
        ] = None

        metrics[
            "duplicate_timestamp_count"
        ] = None

    # -------------------------------------------------------------
    # Joint metrics
    # -------------------------------------------------------------

    joint_cols = [
        f"joint_{i}"
        for i in range(1, 8)
    ]

    if all(
        col in df.columns
        for col in joint_cols
    ):

        joint_uniform = (
            resample_uniform(
                df,
                joint_cols
            )
        )

        if (
            joint_uniform
            is not None
        ):

            joint_uniform = (
                smooth_dataframe(
                    joint_uniform,
                    joint_cols
                )
            )

            metrics[
                "joint_path_length"
            ] = path_length(
                joint_uniform,
                joint_cols
            )

        else:

            metrics[
                "joint_path_length"
            ] = path_length(
                df,
                joint_cols
            )

        joint_jerk = (
            compute_jerk_metrics(
                df,
                joint_cols
            )
        )

        metrics[
            "joint_jerk"
        ] = (
            joint_jerk[
                "jerk_rms"
            ]
        )

        metrics[
            "joint_jerk_rms"
        ] = (
            joint_jerk[
                "jerk_rms"
            ]
        )

        metrics[
            "joint_jerk_peak"
        ] = (
            joint_jerk[
                "jerk_peak"
            ]
        )

        metrics[
            "joint_resampled_rows"
        ] = (
            joint_jerk[
                "resampled_rows"
            ]
        )

        joint_ranges = []

        for col in joint_cols:

            r = signal_range(
                df,
                col
            )

            metrics[
                f"range_{col}"
            ] = r

            if r is not None:
                joint_ranges.append(
                    r
                )

        metrics[
            "total_joint_range"
        ] = (
            float(
                np.sum(
                    joint_ranges
                )
            )
            if joint_ranges
            else None
        )

    else:

        metrics[
            "joint_path_length"
        ] = None

        metrics[
            "joint_jerk"
        ] = None

        metrics[
            "joint_jerk_rms"
        ] = None

        metrics[
            "joint_jerk_peak"
        ] = None

        metrics[
            "joint_resampled_rows"
        ] = 0

        metrics[
            "total_joint_range"
        ] = None

        for col in joint_cols:
            metrics[
                f"range_{col}"
            ] = None

    # -------------------------------------------------------------
    # Joint effort
    # -------------------------------------------------------------

    effort_cols = [
        f"effort_{i}"
        for i in range(1, 8)
    ]

    if all(
        col in df.columns
        for col in effort_cols
    ):

        effort = (
            df[
                effort_cols
            ]
            .apply(
                pd.to_numeric,
                errors="coerce"
            )
            .to_numpy()
        )

        if (
            len(effort) == 0
            or np.isnan(
                effort
            ).all()
        ):

            metrics[
                "joint_effort"
            ] = None

        else:

            effort_norm = (
                np.linalg.norm(
                    effort,
                    axis=1
                )
            )

            if np.isnan(
                effort_norm
            ).all():

                metrics[
                    "joint_effort"
                ] = None

            else:

                metrics[
                    "joint_effort"
                ] = float(
                    np.nanmean(
                        effort_norm
                    )
                )

    else:

        metrics[
            "joint_effort"
        ] = None

    # -------------------------------------------------------------
    # End-effector Cartesian path, jerk, and TF jump checks
    # -------------------------------------------------------------

    ee_cols = [
        "ee_x",
        "ee_y",
        "ee_z"
    ]

    ee_available = all(
        col in df.columns
        for col in ee_cols
    )

    if ee_available:

        ee_numeric = (
            df[
                ee_cols
            ]
            .apply(
                pd.to_numeric,
                errors="coerce"
            )
        )

        ee_valid_rows = (
            ee_numeric
            .notna()
            .all(axis=1)
            .sum()
        )

        ee_missing_ratio = float(
            ee_numeric
            .isna()
            .all(axis=1)
            .mean()
        )

        metrics[
            "ee_missing_ratio"
        ] = ee_missing_ratio

        if (
            ee_valid_rows >= 2
            and ee_missing_ratio < 0.9
        ):

            ee_uniform = (
                resample_uniform(
                    df,
                    ee_cols
                )
            )

            if (
                ee_uniform
                is not None
            ):

                ee_uniform = (
                    smooth_dataframe(
                        ee_uniform,
                        ee_cols
                    )
                )

                metrics[
                    "cartesian_path_length"
                ] = path_length(
                    ee_uniform,
                    ee_cols
                )

            else:

                metrics[
                    "cartesian_path_length"
                ] = path_length(
                    df,
                    ee_cols
                )

            metrics[
                "cartesian_path_length_clean"
            ] = (
                clean_path_length_with_speed_filter(
                    df,
                    ee_cols,
                    EE_JUMP_SPEED_THRESHOLD
                )
            )

            ee_jump = (
                compute_jump_metrics(
                    df,
                    ee_cols,
                    EE_JUMP_SPEED_THRESHOLD
                )
            )

            metrics[
                "ee_jump_count"
            ] = (
                ee_jump[
                    "jump_count"
                ]
            )

            metrics[
                "ee_max_speed"
            ] = (
                ee_jump[
                    "max_speed"
                ]
            )

            ee_signal_invalid = (
                metrics[
                    "ee_jump_count"
                ] is not None
                and metrics[
                    "ee_jump_count"
                ] > EE_MAX_ALLOWED_JUMPS
            )

            ee_jerk = (
                compute_jerk_metrics(
                    df,
                    ee_cols
                )
            )

            metrics[
                "cartesian_jerk"
            ] = (
                ee_jerk[
                    "jerk_rms"
                ]
            )

            metrics[
                "cartesian_jerk_rms"
            ] = (
                ee_jerk[
                    "jerk_rms"
                ]
            )

            metrics[
                "cartesian_jerk_peak"
            ] = (
                ee_jerk[
                    "jerk_peak"
                ]
            )

            metrics[
                "cartesian_resampled_rows"
            ] = (
                ee_jerk[
                    "resampled_rows"
                ]
            )

            # Raw Cartesian path is retained for audit.
            # Analysis-ready Cartesian values are invalidated
            # if TF jump corruption is excessive.
            if ee_signal_invalid:

                metrics[
                    "cartesian_path_length_clean"
                ] = None

                metrics[
                    "cartesian_jerk"
                ] = None

                metrics[
                    "cartesian_jerk_rms"
                ] = None

                metrics[
                    "cartesian_jerk_peak"
                ] = None

        else:

            metrics[
                "cartesian_path_length"
            ] = None

            metrics[
                "cartesian_path_length_clean"
            ] = None

            metrics[
                "ee_jump_count"
            ] = None

            metrics[
                "ee_max_speed"
            ] = None

            metrics[
                "cartesian_jerk"
            ] = None

            metrics[
                "cartesian_jerk_rms"
            ] = None

            metrics[
                "cartesian_jerk_peak"
            ] = None

            metrics[
                "cartesian_resampled_rows"
            ] = 0

    else:

        metrics[
            "ee_missing_ratio"
        ] = None

        metrics[
            "cartesian_path_length"
        ] = None

        metrics[
            "cartesian_path_length_clean"
        ] = None

        metrics[
            "ee_jump_count"
        ] = None

        metrics[
            "ee_max_speed"
        ] = None

        metrics[
            "cartesian_jerk"
        ] = None

        metrics[
            "cartesian_jerk_rms"
        ] = None

        metrics[
            "cartesian_jerk_peak"
        ] = None

        metrics[
            "cartesian_resampled_rows"
        ] = 0

    # -------------------------------------------------------------
    # Base path, stale-pose, jump checks
    # -------------------------------------------------------------

    base_cols = [
        "base_x",
        "base_y"
    ]

    base_available = all(
        col in df.columns
        for col in base_cols
    )

    if base_available:

        base_numeric = (
            df[
                base_cols
            ]
            .apply(
                pd.to_numeric,
                errors="coerce"
            )
        )

        base_valid_rows = (
            base_numeric
            .notna()
            .all(axis=1)
            .sum()
        )

        if base_valid_rows >= 2:

            base_uniform = (
                resample_uniform(
                    df,
                    base_cols
                )
            )

            if (
                base_uniform
                is not None
            ):

                base_uniform = (
                    smooth_dataframe(
                        base_uniform,
                        base_cols
                    )
                )

                metrics[
                    "base_path_length"
                ] = path_length(
                    base_uniform,
                    base_cols
                )

            else:

                metrics[
                    "base_path_length"
                ] = path_length(
                    df,
                    base_cols
                )

            metrics[
                "base_path_length_clean"
            ] = (
                clean_path_length_with_speed_filter(
                    df,
                    base_cols,
                    BASE_JUMP_SPEED_THRESHOLD
                )
            )

            base_jump = (
                compute_jump_metrics(
                    df,
                    base_cols,
                    BASE_JUMP_SPEED_THRESHOLD
                )
            )

            metrics[
                "base_jump_count"
            ] = (
                base_jump[
                    "jump_count"
                ]
            )

            metrics[
                "base_max_speed"
            ] = (
                base_jump[
                    "max_speed"
                ]
            )

            metrics[
                "base_stale_ratio"
            ] = (
                compute_stale_ratio(
                    df,
                    base_cols,
                    BASE_STALE_EPS
                )
            )

        else:

            metrics[
                "base_path_length"
            ] = None

            metrics[
                "base_path_length_clean"
            ] = None

            metrics[
                "base_jump_count"
            ] = None

            metrics[
                "base_max_speed"
            ] = None

            metrics[
                "base_stale_ratio"
            ] = None

    else:

        metrics[
            "base_path_length"
        ] = None

        metrics[
            "base_path_length_clean"
        ] = None

        metrics[
            "base_jump_count"
        ] = None

        metrics[
            "base_max_speed"
        ] = None

        metrics[
            "base_stale_ratio"
        ] = None

    # -------------------------------------------------------------
    # Object path, stale-pose, jump checks
    # -------------------------------------------------------------

    object_cols = [
        "object_x",
        "object_y",
        "object_z"
    ]

    object_available = all(
        col in df.columns
        for col in object_cols
    )

    if object_available:

        object_numeric = (
            df[
                object_cols
            ]
            .apply(
                pd.to_numeric,
                errors="coerce"
            )
        )

        object_valid_rows = (
            object_numeric
            .notna()
            .all(axis=1)
            .sum()
        )

        if object_valid_rows >= 2:

            object_uniform = (
                resample_uniform(
                    df,
                    object_cols
                )
            )

            if (
                object_uniform
                is not None
            ):

                object_uniform = (
                    smooth_dataframe(
                        object_uniform,
                        object_cols
                    )
                )

                metrics[
                    "object_path_length"
                ] = path_length(
                    object_uniform,
                    object_cols
                )

            else:

                metrics[
                    "object_path_length"
                ] = path_length(
                    df,
                    object_cols
                )

            metrics[
                "object_path_length_clean"
            ] = (
                clean_path_length_with_speed_filter(
                    df,
                    object_cols,
                    OBJECT_JUMP_SPEED_THRESHOLD
                )
            )

            object_jump = (
                compute_jump_metrics(
                    df,
                    object_cols,
                    OBJECT_JUMP_SPEED_THRESHOLD
                )
            )

            metrics[
                "object_jump_count"
            ] = (
                object_jump[
                    "jump_count"
                ]
            )

            metrics[
                "object_max_speed"
            ] = (
                object_jump[
                    "max_speed"
                ]
            )

            metrics[
                "object_stale_ratio"
            ] = (
                compute_stale_ratio(
                    df,
                    object_cols,
                    OBJECT_STALE_EPS
                )
            )

            for col in object_cols:

                metrics[
                    f"range_{col}"
                ] = (
                    signal_range(
                        df,
                        col
                    )
                )

        else:

            metrics[
                "object_path_length"
            ] = None

            metrics[
                "object_path_length_clean"
            ] = None

            metrics[
                "object_jump_count"
            ] = None

            metrics[
                "object_max_speed"
            ] = None

            metrics[
                "object_stale_ratio"
            ] = None

            for col in object_cols:
                metrics[
                    f"range_{col}"
                ] = None

    else:

        metrics[
            "object_path_length"
        ] = None

        metrics[
            "object_path_length_clean"
        ] = None

        metrics[
            "object_jump_count"
        ] = None

        metrics[
            "object_max_speed"
        ] = None

        metrics[
            "object_stale_ratio"
        ] = None

        for col in object_cols:
            metrics[
                f"range_{col}"
            ] = None

    # -------------------------------------------------------------
    # Gripper movement / chatter
    # -------------------------------------------------------------

    if (
        "gripper_state"
        in df.columns
    ):

        gripper = (
            pd.to_numeric(
                df[
                    "gripper_state"
                ],
                errors="coerce"
            )
        )

        gripper_range = (
            signal_range(
                df,
                "gripper_state"
            )
        )

        metrics[
            "gripper_range"
        ] = gripper_range

        gripper_flatline = (
            task_success is True
            and gripper_range is not None
            and gripper_range
            < GRIPPER_FLATLINE_THRESHOLD
        )

        if gripper_range is None:

            metrics[
                "gripper_reversal_count"
            ] = None

            metrics[
                "gripper_open_close_cycles"
            ] = None

            metrics[
                "gripper_chatter"
            ] = None

        elif gripper_flatline:

            metrics[
                "gripper_reversal_count"
            ] = None

            metrics[
                "gripper_open_close_cycles"
            ] = None

            metrics[
                "gripper_chatter"
            ] = None

        else:

            reversal_count = (
                count_directional_reversals(
                    gripper,
                    eps=GRIPPER_MOVEMENT_EPS
                )
            )

            cycle_count = (
                count_gripper_cycles(
                    gripper,
                    eps=GRIPPER_MOVEMENT_EPS
                )
            )

            metrics[
                "gripper_reversal_count"
            ] = reversal_count

            metrics[
                "gripper_open_close_cycles"
            ] = cycle_count

            metrics[
                "gripper_chatter"
            ] = reversal_count

    else:

        metrics[
            "gripper_range"
        ] = None

        metrics[
            "gripper_reversal_count"
        ] = None

        metrics[
            "gripper_open_close_cycles"
        ] = None

        metrics[
            "gripper_chatter"
        ] = None

    # -------------------------------------------------------------
    # Health flags
    # -------------------------------------------------------------

    health_flags = []

    if (
        metrics.get(
            "duplicate_timestamp_count"
        )
        is not None
        and metrics[
            "duplicate_timestamp_count"
        ] > 0
    ):
        health_flags.append(
            "duplicate_timestamps_detected"
        )

    # EE tracking unavailable
    if not ee_available:
        health_flags.append(
            "ee_tracking_unavailable"
        )

    # EE TF jumps
    if (
        metrics.get(
            "ee_jump_count"
        )
        is not None
    ):

        if (
            metrics[
                "ee_jump_count"
            ] > 0
        ):
            health_flags.append(
                "ee_tracking_jumps_detected"
            )

        if (
            metrics[
                "ee_jump_count"
            ] > EE_MAX_ALLOWED_JUMPS
        ):
            health_flags.append(
                "ee_cartesian_metrics_invalid"
            )

    # Object tracking unavailable
    if (
        not object_available
        or metrics.get(
            "object_path_length"
        ) is None
    ):
        health_flags.append(
            "object_tracking_unavailable"
        )

    # Object tracking jumps
    if (
        metrics.get(
            "object_jump_count"
        )
        is not None
        and metrics[
            "object_jump_count"
        ] > 0
    ):
        health_flags.append(
            "object_tracking_jumps_detected"
        )

    # Base tracking unavailable
    if (
        not base_available
        or metrics.get(
            "base_path_length"
        ) is None
    ):
        health_flags.append(
            "base_tracking_unavailable"
        )

    # Base tracking jumps
    if (
        metrics.get(
            "base_jump_count"
        )
        is not None
        and metrics[
            "base_jump_count"
        ] > 0
    ):
        health_flags.append(
            "base_tracking_jumps_detected"
        )

    # Object stale signal
    if (
        metrics.get(
            "object_stale_ratio"
        )
        is not None
        and metrics[
            "object_stale_ratio"
        ] > 0.95
    ):
        health_flags.append(
            "object_pose_mostly_stale"
        )

    # Base stale signal
    if (
        metrics.get(
            "base_stale_ratio"
        )
        is not None
        and metrics[
            "base_stale_ratio"
        ] > 0.95
    ):
        health_flags.append(
            "base_pose_mostly_stale"
        )

    # Extreme joint jerk sanity check
    if (
        metrics.get(
            "joint_jerk_peak"
        )
        is not None
        and metrics[
            "joint_jerk_peak"
        ] > 100000
    ):
        health_flags.append(
            "extreme_peak_joint_jerk"
        )

    # Gripper flatline during successful trial
    if (
        metrics.get(
            "gripper_range"
        )
        is not None
        and task_success is True
        and metrics[
            "gripper_range"
        ] < GRIPPER_FLATLINE_THRESHOLD
    ):
        health_flags.append(
            "gripper_flatline_despite_success"
        )

    metrics[
        "health_flags"
    ] = health_flags

    # -------------------------------------------------------------
    # Final report
    # -------------------------------------------------------------

    report = {
        "participant_id": participant_id,
        "condition": condition,
        "trial_id": trial_id,
        "task_success": task_success,
        "technician_intervention": technician_intervention,
        "notes": notes,
        "metrics": metrics,
    }

    output_path = (
        trial_dir
        / "quality_report.json"
    )

    save_json(
        report,
        output_path
    )

    return report