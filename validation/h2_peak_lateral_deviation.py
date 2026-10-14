#!/usr/bin/env python3

import os
import re
import glob

import numpy as np
import pandas as pd

from scipy.stats import friedmanchisquare, wilcoxon


# ============================================================
# SETTINGS
# ============================================================

DATA_ROOT = "data"

CONDITIONS = [
    "REAL",
    "2D",
    "VR",
]

TRIALS = [
    "T02",
    "T03",
]

DISPLAY = {
    "REAL": "In-person",
    "2D": "2D",
    "VR": "VR",
}

# Same large-jump threshold used in the paper trajectory plot
MAX_STEP = 0.12


# ============================================================
# FIND ALL T02 / T03 TELEMETRY FILES
# ============================================================

pattern = re.compile(
    r"^(P\d+)_(REAL|2D|VR)_(T0[23])$"
)

records = []

for f in glob.glob(
    os.path.join(
        DATA_ROOT,
        "*",
        "telemetry.csv",
    )
):
    folder = os.path.basename(
        os.path.dirname(f)
    )

    match = pattern.fullmatch(folder)

    if not match:
        continue

    participant, condition, trial = match.groups()

    records.append({
        "participant": participant,
        "condition": condition,
        "trial": trial,
        "file": f,
    })


files = pd.DataFrame(records)

if files.empty:
    raise RuntimeError(
        "No T02/T03 telemetry files found."
    )


files = (
    files
    .sort_values(
        [
            "participant",
            "condition",
            "trial",
        ]
    )
    .reset_index(drop=True)
)


print("\n========================================")
print("EXECUTION FILES")
print("========================================")

print(
    files.to_string(index=False)
)

print(
    "\nNumber of T02/T03 files:",
    len(files),
)

print(
    "Participants found:",
    files["participant"].nunique(),
)


# ============================================================
# LOAD + CLEAN OBJECT TRAJECTORY
#
# Uses the same object columns and basic cleaning as the
# paper trajectory visualization.
# ============================================================

def load_object_path(csv_path):

    df = pd.read_csv(csv_path)

    required = [
        "object_x",
        "object_y",
        "object_z",
    ]

    missing = [
        c
        for c in required
        if c not in df.columns
    ]

    if missing:
        print(
            f"Missing columns in {csv_path}: {missing}"
        )
        return None


    xyz = (
        df[required]
        .apply(
            pd.to_numeric,
            errors="coerce",
        )
        .dropna()
        .to_numpy(dtype=float)
    )


    if len(xyz) < 20:
        return None


    # --------------------------------------------------------
    # Remove giant tracking jumps
    # --------------------------------------------------------

    step = np.linalg.norm(
        np.diff(
            xyz,
            axis=0,
        ),
        axis=1,
    )

    keep = np.concatenate([
        [True],
        step < MAX_STEP,
    ])

    xyz = xyz[keep]


    if len(xyz) < 20:
        return None


    # --------------------------------------------------------
    # Gentle median filter
    # Same as the paper visualization script
    # --------------------------------------------------------

    xyz = (
        pd.DataFrame(
            xyz,
            columns=[
                "x",
                "y",
                "z",
            ],
        )
        .rolling(
            window=7,
            center=True,
            min_periods=1,
        )
        .median()
        .to_numpy()
    )


    return xyz


# ============================================================
# PEAK LATERAL DEVIATION
#
# Defined in horizontal XY plane.
#
# For each trial:
#   - straight line from object start to object end
#   - calculate perpendicular distance of every XY point
#     from this task line
#   - peak deviation = maximum perpendicular distance
#
# NOTE:
# This metric should still be sanity-checked before inclusion
# in the paper.
# ============================================================

def peak_lateral_deviation(xyz):

    xy = xyz[:, :2]

    start = xy[0]
    end = xy[-1]

    task_vector = (
        end - start
    )

    task_length = np.linalg.norm(
        task_vector
    )


    if task_length <= 1e-8:
        return np.nan


    task_unit = (
        task_vector
        /
        task_length
    )


    relative = (
        xy - start
    )


    along = (
        relative
        @ task_unit
    )


    projected = (
        start
        +
        np.outer(
            along,
            task_unit,
        )
    )


    deviation = np.linalg.norm(
        xy - projected,
        axis=1,
    )


    return float(
        np.nanmax(
            deviation
        )
    )


# ============================================================
# TRIAL-LEVEL METRIC
# ============================================================

trial_results = []


for _, row in files.iterrows():

    xyz = load_object_path(
        row["file"]
    )


    if xyz is None:
        peak = np.nan
    else:
        peak = peak_lateral_deviation(
            xyz
        )


    trial_results.append({
        "participant":
            row["participant"],

        "condition":
            row["condition"],

        "trial":
            row["trial"],

        "peak_lateral_deviation_m":
            peak,
    })


trial_df = pd.DataFrame(
    trial_results
)


print("\n========================================")
print("TRIAL-LEVEL PEAK LATERAL DEVIATION")
print("========================================")

print(
    trial_df
    .round(4)
    .to_string(index=False)
)


# ============================================================
# PARTICIPANT-LEVEL METRIC
#
# Mean of T02 and T03 within each participant × condition
# ============================================================

participant_df = (
    trial_df
    .groupby(
        [
            "participant",
            "condition",
        ],
        as_index=False,
    )[
        "peak_lateral_deviation_m"
    ]
    .mean()
)


wide = (
    participant_df
    .pivot(
        index="participant",
        columns="condition",
        values="peak_lateral_deviation_m",
    )
    .reindex(
        columns=CONDITIONS
    )
)


print("\n========================================")
print("PARTICIPANT-LEVEL VALUES")
print("Mean of T02 and T03")
print("========================================")

print(
    wide
    .round(4)
    .to_string()
)


# ============================================================
# COMPLETE PARTICIPANTS FOR 3-CONDITION TEST
# ============================================================

complete = (
    wide
    .dropna(
        subset=[
            "REAL",
            "2D",
            "VR",
        ]
    )
)


print("\n========================================")
print("COMPLETE PARTICIPANTS USED IN STATISTICS")
print("========================================")

print(
    complete.index.tolist()
)

print(
    "N =",
    len(complete),
)


# ============================================================
# CONDITION DESCRIPTIVES
#
# IMPORTANT:
# Use the same complete repeated-measures participant set for
# the condition summaries reported alongside the Friedman test.
# ============================================================

summary_rows = []


for condition in CONDITIONS:

    vals = complete[
        condition
    ].dropna()


    summary_rows.append({
        "condition":
            DISPLAY[condition],

        "n":
            len(vals),

        "mean_m":
            vals.mean(),

        "sd_m":
            vals.std(ddof=1),

        "median_m":
            vals.median(),

        "q1_m":
            vals.quantile(0.25),

        "q3_m":
            vals.quantile(0.75),

        "min_m":
            vals.min(),

        "max_m":
            vals.max(),
    })


summary = pd.DataFrame(
    summary_rows
)


print("\n========================================")
print("CONDITION SUMMARY")
print("COMPLETE REPEATED-MEASURES SAMPLE")
print("========================================")

print(
    summary
    .round(4)
    .to_string(index=False)
)


# ============================================================
# FRIEDMAN TEST
# ============================================================

friedman_stat, friedman_p = (
    friedmanchisquare(
        complete["REAL"],
        complete["2D"],
        complete["VR"],
    )
)


print("\n========================================")
print("FRIEDMAN TEST")
print("========================================")

print(
    f"N = {len(complete)}"
)

print(
    f"chi-square = {friedman_stat:.4f}"
)

print(
    f"p = {friedman_p:.6f}"
)


# ============================================================
# PAIRED WILCOXON TESTS
#
# These use the complete three-condition sample so that the
# reported pairwise comparisons use the same participant set.
# ============================================================

def run_wilcoxon(
    df,
    a,
    b,
):

    paired = (
        df[
            [
                a,
                b,
            ]
        ]
        .dropna()
    )


    differences = (
        paired[a]
        -
        paired[b]
    )


    if np.allclose(
        differences,
        0,
    ):
        return {
            "n": len(paired),
            "W": 0.0,
            "p": 1.0,
        }


    W, p = wilcoxon(
        paired[a],
        paired[b],
        alternative="two-sided",
        zero_method="wilcox",
    )


    return {
        "n": len(paired),
        "W": float(W),
        "p": float(p),
    }


vr_vs_2d = run_wilcoxon(
    complete,
    "VR",
    "2D",
)

vr_vs_real = run_wilcoxon(
    complete,
    "VR",
    "REAL",
)


print("\n========================================")
print("PLANNED PAIRED COMPARISONS")
print("========================================")


print("\nVR vs 2D")

print(
    f"N = {vr_vs_2d['n']}"
)

print(
    f"W = {vr_vs_2d['W']:.3f}"
)

print(
    f"p = {vr_vs_2d['p']:.6f}"
)


print("\nVR vs In-person")

print(
    f"N = {vr_vs_real['n']}"
)

print(
    f"W = {vr_vs_real['W']:.3f}"
)

print(
    f"p = {vr_vs_real['p']:.6f}"
)


# ============================================================
# EXTRA SANITY CHECK:
# PRINT LARGEST VALUES
# ============================================================

print("\n========================================")
print("LARGEST TRIAL-LEVEL DEVIATIONS")
print("========================================")

print(
    trial_df
    .sort_values(
        "peak_lateral_deviation_m",
        ascending=False,
    )
    .head(20)
    .round(4)
    .to_string(index=False)
)


# ============================================================
# SAVE RESULTS
# ============================================================

trial_df.to_csv(
    "h2_peak_lateral_deviation_trials.csv",
    index=False,
)

participant_df.to_csv(
    "h2_peak_lateral_deviation_participants.csv",
    index=False,
)

complete.to_csv(
    "h2_peak_lateral_deviation_complete_participants.csv"
)

summary.to_csv(
    "h2_peak_lateral_deviation_summary.csv",
    index=False,
)


print("\n========================================")
print("SAVED")
print("========================================")

print(
    "h2_peak_lateral_deviation_trials.csv"
)

print(
    "h2_peak_lateral_deviation_participants.csv"
)

print(
    "h2_peak_lateral_deviation_complete_participants.csv"
)

print(
    "h2_peak_lateral_deviation_summary.csv"
)
