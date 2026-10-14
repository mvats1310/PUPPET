#!/usr/bin/env python3

import os
import re
import glob

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from matplotlib.lines import Line2D


# ============================================================
# SETTINGS
# ============================================================

DATA_GLOB = "data/*/telemetry.csv"
OUTPUT_DIR = "trajectory_repeatability_results"

CONDITIONS = ["REAL", "2D", "VR"]
TRIALS_TO_USE = ["T02", "T03"]

TRAJ_TYPE = "object"

# EXACT CONDITION COLORS
COLORS = {
    "REAL": "#2b8cbe",
    "2D":   "#756bb1",
    "VR":   "#2ca25f",
}

DISPLAY = {
    "REAL": "In-person",
    "2D":   "2D",
    "VR":   "VR",
}

ROLLING_WINDOW = 11
MIN_SEGMENT_FRAMES = 30
GAP_FILL = 12
PAD_FRAMES = 10
N_RESAMPLE = 150

# VISUAL SETTINGS
RAW_ALPHA = 0.18
RAW_LW = 1.15
MEDIAN_LW = 2.8


# ============================================================
# FILE PARSING
# ============================================================

def parse_trial_folder(path):

    folder = os.path.basename(
        os.path.dirname(path)
    )

    match = re.match(
        r"(P\d+)_(REAL|2D|VR)_(T\d+)$",
        folder
    )

    if not match:
        return None

    return match.groups()


# ============================================================
# BOOLEAN HELPERS
# ============================================================

def fill_small_false_gaps(mask, max_gap=10):

    mask = mask.copy().astype(bool)

    n = len(mask)
    i = 0

    while i < n:

        if mask[i]:
            i += 1
            continue

        j = i

        while j < n and not mask[j]:
            j += 1

        gap_len = j - i

        left_true = (
            i > 0
            and mask[i - 1]
        )

        right_true = (
            j < n
            and mask[j]
        )

        if (
            left_true
            and right_true
            and gap_len <= max_gap
        ):
            mask[i:j] = True

        i = j

    return mask


def contiguous_true_segments(mask):

    segments = []

    in_segment = False
    start = None

    for i, value in enumerate(mask):

        if value and not in_segment:

            start = i
            in_segment = True

        elif not value and in_segment:

            segments.append(
                (start, i - 1)
            )

            in_segment = False

    if in_segment:

        segments.append(
            (start, len(mask) - 1)
        )

    return segments


# ============================================================
# RESAMPLING
# ============================================================

def resample_curve(arr, n_points=N_RESAMPLE):

    if len(arr) < 2:
        return None

    t_old = np.linspace(
        0,
        1,
        len(arr)
    )

    t_new = np.linspace(
        0,
        1,
        n_points
    )

    out = np.zeros(
        (
            n_points,
            arr.shape[1]
        )
    )

    for dim in range(
        arr.shape[1]
    ):

        out[:, dim] = np.interp(
            t_new,
            t_old,
            arr[:, dim]
        )

    return out


# ============================================================
# XY ROTATION
# ============================================================

def rotate_xy(points_xy, angle_rad):

    c = np.cos(angle_rad)
    s = np.sin(angle_rad)

    rotation = np.array([
        [c, -s],
        [s,  c]
    ])

    return points_xy @ rotation.T


# ============================================================
# DETECT MAIN TRANSFER SEGMENT
# ============================================================

def detect_main_transfer_segment(
    df,
    cols
):

    sub = (
        df[cols]
        .apply(
            pd.to_numeric,
            errors="coerce"
        )
        .dropna()
    )

    if len(sub) < 50:
        return None


    # --------------------------------------------------------
    # Gentle smoothing
    # --------------------------------------------------------

    smooth = (
        sub
        .rolling(
            window=ROLLING_WINDOW,
            center=True,
            min_periods=1
        )
        .mean()
    )

    xyz = smooth.to_numpy(
        dtype=float
    )


    # --------------------------------------------------------
    # Frame-to-frame movement magnitude
    # --------------------------------------------------------

    step = np.linalg.norm(
        np.diff(
            xyz,
            axis=0
        ),
        axis=1
    )

    step = np.concatenate([
        [0.0],
        step
    ])


    # --------------------------------------------------------
    # Adaptive movement threshold
    # --------------------------------------------------------

    p90 = np.percentile(
        step,
        90
    )

    p75 = np.percentile(
        step,
        75
    )

    threshold = max(
        0.0015,
        0.35 * p75,
        0.20 * p90
    )

    moving = (
        step > threshold
    )

    moving = fill_small_false_gaps(
        moving,
        GAP_FILL
    )


    # --------------------------------------------------------
    # Candidate movement regions
    # --------------------------------------------------------

    segments = contiguous_true_segments(
        moving
    )

    candidates = []


    for start, end in segments:

        start_pad = max(
            0,
            start - PAD_FRAMES
        )

        end_pad = min(
            len(xyz) - 1,
            end + PAD_FRAMES
        )

        segment = xyz[
            start_pad:
            end_pad + 1
        ]


        if (
            len(segment)
            < MIN_SEGMENT_FRAMES
        ):
            continue


        diffs = np.diff(
            segment,
            axis=0
        )

        path_length = np.sum(
            np.linalg.norm(
                diffs,
                axis=1
            )
        )

        end_displacement = np.linalg.norm(
            segment[-1]
            -
            segment[0]
        )


        if TRAJ_TYPE == "object":

            if (
                path_length < 0.15
                or
                end_displacement < 0.10
            ):
                continue

        else:

            if (
                path_length < 0.08
                or
                end_displacement < 0.05
            ):
                continue


        score = (
            path_length
            +
            1.5 * end_displacement
        )

        candidates.append(
            (
                score,
                segment
            )
        )


    if not candidates:
        return None


    candidates.sort(
        key=lambda item: item[0],
        reverse=True
    )

    best = candidates[0][1]


    # --------------------------------------------------------
    # Start-align
    # --------------------------------------------------------

    best = (
        best
        -
        best[0]
    )

    return best


# ============================================================
# LOAD ALL TRAJECTORIES
# ============================================================

def load_all_trajectories():

    trajectories = {
        condition: []
        for condition in CONDITIONS
    }

    if TRAJ_TYPE == "object":

        cols = [
            "object_x",
            "object_y",
            "object_z"
        ]

    else:

        cols = [
            "ee_x",
            "ee_y",
            "ee_z"
        ]


    for path in sorted(
        glob.glob(DATA_GLOB)
    ):

        parsed = parse_trial_folder(
            path
        )

        if parsed is None:
            continue


        participant, condition, trial = parsed


        if (
            condition not in CONDITIONS
            or
            trial not in TRIALS_TO_USE
        ):
            continue


        try:

            df = pd.read_csv(
                path
            )

        except Exception:

            continue


        if not all(
            col in df.columns
            for col in cols
        ):
            continue


        segment = detect_main_transfer_segment(
            df,
            cols
        )


        if segment is None:
            continue


        trajectories[
            condition
        ].append(
            segment
        )


    return trajectories


# ============================================================
# ALIGN INTO COMMON TASK DIRECTION
# ============================================================

def align_task_direction(
    trajectories
):

    aligned = {}


    for condition in CONDITIONS:

        segments = trajectories[
            condition
        ]


        if not segments:

            aligned[
                condition
            ] = []

            continue


        endpoints = np.array([
            segment[-1, :2]
            for segment in segments
        ])


        median_endpoint = np.median(
            endpoints,
            axis=0
        )


        angle = np.arctan2(
            median_endpoint[1],
            median_endpoint[0]
        )


        condition_aligned = []


        for segment in segments:

            transformed = (
                segment.copy()
            )


            transformed[:, :2] = rotate_xy(
                transformed[:, :2],
                -angle
            )


            # Ensure overall task direction points toward +X
            if transformed[-1, 0] < 0:

                transformed[:, :2] = rotate_xy(
                    transformed[:, :2],
                    np.pi
                )


            condition_aligned.append(
                transformed
            )


        aligned[
            condition
        ] = condition_aligned


    return aligned


# ============================================================
# CONDITION MEDIAN
# ============================================================

def build_condition_median(
    segments
):

    if not segments:
        return None


    resampled = []


    for segment in segments:

        curve = resample_curve(
            segment,
            N_RESAMPLE
        )


        if curve is not None:

            resampled.append(
                curve
            )


    if not resampled:
        return None


    stack = np.stack(
        resampled,
        axis=0
    )


    return np.nanmedian(
        stack,
        axis=0
    )


# ============================================================
# ROBUST SHARED AXIS LIMITS
# ============================================================

def get_global_limits(
    trajectories
):

    xs = []
    ys = []


    for condition in CONDITIONS:

        for segment in trajectories[
            condition
        ]:

            xs.extend(
                segment[:, 0]
            )

            ys.extend(
                segment[:, 1]
            )


    xs = np.asarray(xs)
    ys = np.asarray(ys)


    x_low, x_high = np.percentile(
        xs,
        [1, 99]
    )

    y_low, y_high = np.percentile(
        ys,
        [1, 99]
    )


    x_span = (
        x_high
        -
        x_low
    )

    y_span = (
        y_high
        -
        y_low
    )


    x_pad = (
        0.07
        *
        max(
            x_span,
            0.1
        )
    )

    y_pad = (
        0.10
        *
        max(
            y_span,
            0.1
        )
    )


    # Ensure origin is visible
    x_low = min(
        x_low,
        -0.05
    )

    y_low = min(
        y_low,
        -0.05
    )

    y_high = max(
        y_high,
        0.05
    )


    return (
        (
            x_low - x_pad,
            x_high + x_pad
        ),
        (
            y_low - y_pad,
            y_high + y_pad
        )
    )


# ============================================================
# PAPER OVERLAY PLOT
# ============================================================

def plot_overlay(
    trajectories
):

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )


    # --------------------------------------------------------
    # ICRA-friendly typography
    # --------------------------------------------------------

    plt.rcParams.update({

        "font.family":
            "serif",

        "font.size":
            8.5,

        "axes.labelsize":
            9,

        "xtick.labelsize":
            8,

        "ytick.labelsize":
            8,

        "legend.fontsize":
            8,

        "pdf.fonttype":
            42,

        "ps.fonttype":
            42,
    })


    xlim, ylim = get_global_limits(
        trajectories
    )


    # --------------------------------------------------------
    # Compact single-plot figure
    # --------------------------------------------------------

    fig, ax = plt.subplots(
        figsize=(
            4.9,
            3.75
        )
    )


    medians = {}


    # ========================================================
    # LIGHT INDIVIDUAL EXECUTION TRAJECTORIES
    # ========================================================

    for condition in CONDITIONS:

        for segment in trajectories[
            condition
        ]:

            ax.plot(
                segment[:, 0],
                segment[:, 1],
                color=COLORS[
                    condition
                ],
                linewidth=RAW_LW,
                alpha=RAW_ALPHA,
                zorder=1
            )


    # ========================================================
    # BOLD MEDIAN TRAJECTORIES
    # ========================================================

    for condition in CONDITIONS:

        median = build_condition_median(
            trajectories[
                condition
            ]
        )


        if median is None:
            continue


        medians[
            condition
        ] = median


        ax.plot(
            median[:, 0],
            median[:, 1],
            color=COLORS[
                condition
            ],
            linewidth=MEDIAN_LW,
            alpha=1.0,
            solid_capstyle="round",
            zorder=5
        )


    # ========================================================
    # COMMON START MARKER
    # ========================================================

    ax.scatter(
        0,
        0,
        s=48,
        marker="o",
        facecolor="white",
        edgecolor="black",
        linewidth=1.4,
        zorder=10
    )


    ax.annotate(
        "Start",
        xy=(0, 0),
        xytext=(-5, -15),
        textcoords="offset points",
        ha="center",
        fontsize=7.5
    )


    # ========================================================
    # END MARKERS
    # ========================================================

    end_offsets = {
        "REAL": (5, 7),
        "2D":   (5, -14),
        "VR":   (5, 6),
    }


    for condition in CONDITIONS:

        if condition not in medians:
            continue


        end = medians[
            condition
        ][-1]


        ax.scatter(
            end[0],
            end[1],
            s=55,
            marker="^",
            facecolor=COLORS[
                condition
            ],
            edgecolor=COLORS[
                condition
            ],
            linewidth=0.8,
            zorder=10
        )


        offset = end_offsets[
            condition
        ]


        ax.annotate(
            DISPLAY[
                condition
            ],
            xy=(
                end[0],
                end[1]
            ),
            xytext=offset,
            textcoords="offset points",
            fontsize=7.5,
            color=COLORS[
                condition
            ],
            fontweight="bold"
        )


    # ========================================================
    # AXES
    # ========================================================

    ax.set_xlim(
        xlim
    )

    ax.set_ylim(
        ylim
    )


    ax.set_xlabel(
        "Task-axis displacement (m)"
    )

    ax.set_ylabel(
        "Signed lateral deviation (m)"
    )


    ax.grid(
        alpha=0.14,
        linewidth=0.45
    )


    ax.spines[
        "top"
    ].set_visible(
        False
    )

    ax.spines[
        "right"
    ].set_visible(
        False
    )


    # ========================================================
    # LEGEND
    # ========================================================

    legend_handles = [

        Line2D(
            [0],
            [0],
            color=COLORS[
                "REAL"
            ],
            linewidth=2.6,
            label="In-person"
        ),

        Line2D(
            [0],
            [0],
            color=COLORS[
                "2D"
            ],
            linewidth=2.6,
            label="2D"
        ),

        Line2D(
            [0],
            [0],
            color=COLORS[
                "VR"
            ],
            linewidth=2.6,
            label="VR"
        ),

        Line2D(
            [0],
            [0],
            color="#bdbdbd",
            linewidth=1.0,
            alpha=0.75,
            label="Execution trajectories"
        ),

        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="None",
            markerfacecolor="white",
            markeredgecolor="black",
            markersize=5.5,
            label="Start"
        ),

        Line2D(
            [0],
            [0],
            marker="^",
            linestyle="None",
            markerfacecolor="black",
            markeredgecolor="black",
            markersize=5.5,
            label="End"
        ),
    ]


    ax.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(
            0.5,
            1.19
        ),
        ncol=3,
        frameon=False,
        columnspacing=1.1,
        handlelength=2.2,
        handletextpad=0.5
    )


    # ========================================================
    # LAYOUT
    # ========================================================

    fig.subplots_adjust(
        left=0.15,
        right=0.985,
        bottom=0.15,
        top=0.80
    )


    # ========================================================
    # SAVE AS VECTOR PDF + HIGH-RES PNG
    # ========================================================

    if TRAJ_TYPE == "object":

        basename = (
            "H2_object_repeatability_"
            "overlay_ICRA"
        )

    else:

        basename = (
            "H2_ee_repeatability_"
            "overlay_ICRA"
        )


    pdf_path = os.path.join(
        OUTPUT_DIR,
        basename + ".pdf"
    )

    png_path = os.path.join(
        OUTPUT_DIR,
        basename + ".png"
    )


    plt.savefig(
        pdf_path,
        format="pdf",
        bbox_inches="tight",
        pad_inches=0.02
    )


    plt.savefig(
        png_path,
        dpi=600,
        bbox_inches="tight",
        pad_inches=0.02
    )


    print("\nSaved:")
    print(pdf_path)
    print(png_path)


    plt.show()


# ============================================================
# MAIN
# ============================================================

def main():

    trajectories = load_all_trajectories()


    print(
        "\nExecution trajectories detected:"
    )


    for condition in CONDITIONS:

        print(
            f"{DISPLAY[condition]}: "
            f"{len(trajectories[condition])}"
        )


    aligned = align_task_direction(
        trajectories
    )


    plot_overlay(
        aligned
    )


if __name__ == "__main__":
    main()
