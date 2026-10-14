#!/usr/bin/env python3

import os
import re
import glob

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D


# ============================================================
# SETTINGS
# ============================================================

DATA_ROOT = "data"
OUTPUT_DIR = "trajectory_repeatability_results"

CONDITIONS = ["REAL", "2D", "VR"]
EXECUTION_TRIALS = ["T02", "T03"]

DISPLAY = {
    "REAL": "In-person",
    "2D": "2D",
    "VR": "VR",
}

COLORS = {
    "REAL": "#2b8cbe",
    "2D":   "#756bb1",
    "VR":   "#2ca25f",
}

LIGHT_COLORS = {
    "REAL": "#a6bddb",
    "2D":   "#bcbddc",
    "VR":   "#99d8c9",
}

N_RESAMPLE = 100

# Only add participants here if there is a documented reason.
EXCLUDE_PARTICIPANTS = set()


# ============================================================
# OUTPUT
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# FIND TELEMETRY FILES
# ============================================================

pattern = re.compile(
    r"^(P\d+)_(REAL|2D|VR)_(T0[123])$"
)

records = []

for path in glob.glob(
    os.path.join(
        DATA_ROOT,
        "*",
        "telemetry.csv"
    )
):

    folder = os.path.basename(
        os.path.dirname(path)
    )

    match = pattern.match(folder)

    if not match:
        continue

    participant = match.group(1)
    condition = match.group(2)
    trial = match.group(3)

    if participant in EXCLUDE_PARTICIPANTS:
        continue

    records.append({
        "participant": participant,
        "condition": condition,
        "trial": trial,
        "path": path,
    })


files = pd.DataFrame(records)

if files.empty:
    raise RuntimeError(
        "No trial-level telemetry.csv files found under data/"
    )


files = (
    files
    .sort_values(
        ["participant", "condition", "trial"]
    )
    .reset_index(drop=True)
)


print("\n============================================================")
print("TELEMETRY FILES FOUND")
print("============================================================")
print(f"Total trial telemetry files: {len(files)}")

print(
    files.groupby("condition")
    .size()
    .reindex(CONDITIONS)
)


# ============================================================
# TRAJECTORY DEFINITIONS
# ============================================================

TRAJECTORY_COLUMNS = {

    "object": [
        "object_x",
        "object_y",
        "object_z",
    ],

    "ee": [
        "ee_x",
        "ee_y",
        "ee_z",
    ],

    "base": [
        "base_x",
        "base_y",
    ],
}


# ============================================================
# LOAD TRAJECTORY
# ============================================================

def load_trajectory(
    csv_path,
    trajectory_type,
):

    df = pd.read_csv(csv_path)

    cols = TRAJECTORY_COLUMNS[
        trajectory_type
    ]

    missing = [
        c for c in cols
        if c not in df.columns
    ]

    if missing:
        return None

    xyz = (
        df[cols]
        .apply(
            pd.to_numeric,
            errors="coerce"
        )
        .dropna()
        .to_numpy(dtype=float)
    )

    if len(xyz) < 5:
        return None

    if trajectory_type == "base":

        xyz = np.column_stack([
            xyz[:, 0],
            xyz[:, 1],
            np.zeros(len(xyz)),
        ])

    finite = np.isfinite(xyz).all(axis=1)

    xyz = xyz[finite]

    if len(xyz) < 5:
        return None

    step = np.linalg.norm(
        np.diff(
            xyz,
            axis=0
        ),
        axis=1
    )

    keep = np.concatenate([
        [True],
        step > 1e-8,
    ])

    xyz = xyz[keep]

    if len(xyz) < 5:
        return None

    return xyz


# ============================================================
# PATH LENGTH
# ============================================================

def path_length(xyz):

    if xyz is None or len(xyz) < 2:
        return np.nan

    return np.linalg.norm(
        np.diff(
            xyz,
            axis=0
        ),
        axis=1
    ).sum()


# ============================================================
# START ALIGN
# ============================================================

def start_align(xyz):

    return (
        xyz
        -
        xyz[0]
    )


# ============================================================
# ARC-LENGTH RESAMPLE
# ============================================================

def resample_path(
    xyz,
    n=N_RESAMPLE,
):

    segment_lengths = np.linalg.norm(
        np.diff(
            xyz,
            axis=0
        ),
        axis=1
    )

    cumulative = np.concatenate([
        [0.0],
        np.cumsum(segment_lengths),
    ])

    total = cumulative[-1]

    if (
        not np.isfinite(total)
        or total <= 1e-9
    ):
        return None

    unique = np.concatenate([
        [True],
        np.diff(cumulative) > 1e-10,
    ])

    xyz = xyz[unique]
    cumulative = cumulative[unique]

    if len(xyz) < 2:
        return None

    target = np.linspace(
        0,
        cumulative[-1],
        n
    )

    output = np.column_stack([
        np.interp(
            target,
            cumulative,
            xyz[:, axis]
        )
        for axis in range(3)
    ])

    return output


# ============================================================
# POINTWISE RMS DISTANCE
# ============================================================

def trajectory_rms(a, b):

    if a is None or b is None:
        return np.nan

    distances = np.linalg.norm(
        a - b,
        axis=1
    )

    return np.sqrt(
        np.mean(
            distances ** 2
        )
    )


# ============================================================
# 3D DTW
# ============================================================

def dtw_distance(a, b):

    if a is None or b is None:
        return np.nan

    n = len(a)
    m = len(b)

    D = np.full(
        (n + 1, m + 1),
        np.inf,
        dtype=float
    )

    D[0, 0] = 0.0

    for i in range(1, n + 1):

        for j in range(1, m + 1):

            cost = np.linalg.norm(
                a[i - 1]
                -
                b[j - 1]
            )

            D[i, j] = (
                cost
                +
                min(
                    D[i - 1, j],
                    D[i, j - 1],
                    D[i - 1, j - 1],
                )
            )

    return D[n, m] / (n + m)


# ============================================================
# PROCESS ONE TRAJECTORY TYPE
# ============================================================

def analyze_trajectory_type(
    trajectory_type,
):

    print("\n============================================================")
    print(
        f"ANALYZING {trajectory_type.upper()} TRAJECTORIES"
    )
    print("============================================================")

    execution_files = files[
        files["trial"].isin(
            EXECUTION_TRIALS
        )
    ].copy()

    trajectories = {}

    # --------------------------------------------------------
    # LOAD T02 / T03
    # --------------------------------------------------------

    for _, row in execution_files.iterrows():

        raw = load_trajectory(
            row["path"],
            trajectory_type
        )

        if raw is None:
            continue

        aligned = start_align(
            raw
        )

        resampled = resample_path(
            aligned
        )

        if resampled is None:
            continue

        key = (
            row["participant"],
            row["condition"],
            row["trial"],
        )

        trajectories[key] = {
            "raw": raw,
            "aligned": aligned,
            "resampled": resampled,
            "path_length": path_length(raw),
        }


    # ========================================================
    # T02 ↔ T03 REPEATABILITY
    # ========================================================

    metric_rows = []

    participants = sorted(
        files["participant"]
        .unique()
    )

    for participant in participants:

        for condition in CONDITIONS:

            key2 = (
                participant,
                condition,
                "T02",
            )

            key3 = (
                participant,
                condition,
                "T03",
            )

            if (
                key2 not in trajectories
                or
                key3 not in trajectories
            ):
                continue

            t2 = trajectories[key2]
            t3 = trajectories[key3]

            rms = trajectory_rms(
                t2["resampled"],
                t3["resampled"]
            )

            dtw = dtw_distance(
                t2["resampled"],
                t3["resampled"]
            )

            path2 = t2[
                "path_length"
            ]

            path3 = t3[
                "path_length"
            ]

            mean_path = (
                path2 + path3
            ) / 2.0

            if mean_path > 0:

                path_diff_pct = (
                    abs(
                        path3
                        -
                        path2
                    )
                    /
                    mean_path
                    *
                    100
                )

            else:

                path_diff_pct = np.nan

            metric_rows.append({

                "participant":
                    participant,

                "condition":
                    condition,

                "trajectory":
                    trajectory_type,

                "rms_distance_m":
                    rms,

                "dtw_distance_m":
                    dtw,

                "T02_path_length_m":
                    path2,

                "T03_path_length_m":
                    path3,

                "path_length_difference_pct":
                    path_diff_pct,
            })


    metrics = pd.DataFrame(
        metric_rows
    )

    metrics_path = os.path.join(
        OUTPUT_DIR,
        f"{trajectory_type}_repeatability_by_participant.csv"
    )

    metrics.to_csv(
        metrics_path,
        index=False
    )

    print("\nPARTICIPANT-LEVEL REPEATABILITY:")
    print(
        metrics.round(4)
        .to_string(index=False)
    )


    # ========================================================
    # CONDITION SUMMARY
    # ========================================================

    if not metrics.empty:

        summary = (
            metrics
            .groupby("condition")[
                [
                    "rms_distance_m",
                    "dtw_distance_m",
                    "path_length_difference_pct",
                ]
            ]
            .agg(
                ["count", "mean", "median", "std"]
            )
            .reindex(CONDITIONS)
        )

        print("\nCONDITION SUMMARY")
        print(
            "(LOWER = MORE REPEATABLE)"
        )

        print(
            summary.round(4)
            .to_string()
        )

        summary.to_csv(
            os.path.join(
                OUTPUT_DIR,
                f"{trajectory_type}_repeatability_summary.csv"
            )
        )


    # ========================================================
    # 3D FIGURE
    # ========================================================

    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 9,
        "axes.labelsize": 9,
        "axes.titlesize": 10,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })

    all_paths = []

    condition_paths = {
        c: []
        for c in CONDITIONS
    }

    for (
        participant,
        condition,
        trial
    ), value in trajectories.items():

        condition_paths[
            condition
        ].append(
            value["resampled"]
        )

        all_paths.append(
            value["resampled"]
        )

    if not all_paths:

        print(
            f"No valid {trajectory_type} paths found."
        )

        return metrics

    all_points = np.concatenate(
        all_paths,
        axis=0
    )

    xyz_min = np.nanmin(
        all_points,
        axis=0
    )

    xyz_max = np.nanmax(
        all_points,
        axis=0
    )

    span = (
        xyz_max
        -
        xyz_min
    )

    span[
        span < 1e-6
    ] = 0.1

    margin = (
        span * 0.05
    )

    xyz_min = (
        xyz_min
        -
        margin
    )

    xyz_max = (
        xyz_max
        +
        margin
    )

    fig = plt.figure(
        figsize=(8.8, 3.0)
    )

    for panel, condition in enumerate(
        CONDITIONS,
        start=1
    ):

        ax = fig.add_subplot(
            1,
            3,
            panel,
            projection="3d"
        )

        paths = condition_paths[
            condition
        ]

        # ----------------------------------------------------
        # INDIVIDUAL T02/T03 PATHS
        # ----------------------------------------------------

        for path in paths:

            ax.plot(
                path[:, 0],
                path[:, 1],
                path[:, 2],
                color=LIGHT_COLORS[
                    condition
                ],
                linewidth=0.8,
                alpha=0.30
            )

        # ----------------------------------------------------
        # MEAN TRAJECTORY
        # ----------------------------------------------------

        if paths:

            stack = np.stack(
                paths,
                axis=0
            )

            mean_path = np.nanmean(
                stack,
                axis=0
            )

            ax.plot(
                mean_path[:, 0],
                mean_path[:, 1],
                mean_path[:, 2],
                color=COLORS[
                    condition
                ],
                linewidth=2.7
            )

            ax.scatter(
                mean_path[0, 0],
                mean_path[0, 1],
                mean_path[0, 2],
                s=25,
                facecolor="white",
                edgecolor=COLORS[
                    condition
                ],
                linewidth=1.2
            )

            ax.scatter(
                mean_path[-1, 0],
                mean_path[-1, 1],
                mean_path[-1, 2],
                s=25,
                color=COLORS[
                    condition
                ]
            )

        ax.set_xlim(
            xyz_min[0],
            xyz_max[0]
        )

        ax.set_ylim(
            xyz_min[1],
            xyz_max[1]
        )

        ax.set_zlim(
            xyz_min[2],
            xyz_max[2]
        )

        ax.set_xlabel(
            "X (m)",
            labelpad=0
        )

        ax.set_ylabel(
            "Y (m)",
            labelpad=0
        )

        ax.set_zlabel(
            "Z (m)",
            labelpad=0
        )

        ax.set_title(
            f"({chr(96 + panel)}) "
            f"{DISPLAY[condition]}",
            fontweight="bold",
            pad=1
        )

        ax.view_init(
            elev=22,
            azim=-58
        )

    fig.subplots_adjust(
        left=0.01,
        right=0.99,
        bottom=0.02,
        top=0.95,
        wspace=0.00
    )

    pdf_path = os.path.join(
        OUTPUT_DIR,
        f"{trajectory_type}_trajectory_repeatability_3D.pdf"
    )

    png_path = os.path.join(
        OUTPUT_DIR,
        f"{trajectory_type}_trajectory_repeatability_3D.png"
    )

    plt.savefig(
        pdf_path,
        format="pdf",
        bbox_inches="tight",
        pad_inches=0.01
    )

    plt.savefig(
        png_path,
        dpi=600,
        bbox_inches="tight",
        pad_inches=0.01
    )

    plt.close()

    print("\nSAVED:")
    print(pdf_path)
    print(png_path)

    return metrics


# ============================================================
# RUN OBJECT + END-EFFECTOR
# ============================================================

object_metrics = analyze_trajectory_type(
    "object"
)

ee_metrics = analyze_trajectory_type(
    "ee"
)


# ============================================================
# OPTIONAL BASE
# ============================================================

# base_metrics = analyze_trajectory_type(
#     "base"
# )


print("\n============================================================")
print("DONE")
print("============================================================")

print(
    f"Results are in: {OUTPUT_DIR}/"
)

print(
    "\nLower RMS, lower DTW, and lower path-length difference "
    "= greater T02-T03 repeatability."
)
