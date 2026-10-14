#!/usr/bin/env python3

from pathlib import Path
import re

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D


# ============================================================
# SETTINGS
# ============================================================

DATA_DIR = Path("data")

PAIRED_PARTICIPANTS = [
    "P02",
    "P03",
    "P04",
    "P06",
    "P08",
    "P09",
    "P11",
    "P12",
    "P13",
    "P14",
    "P15",
    "P16",
    "P17",
    "P18",
]

CONDITIONS = ["REAL", "2D", "VR"]

TRIALS = ["T02", "T03"]

COLORS = {
    "REAL": "#7FA8D8",
    "2D": "#B191D8",
    "VR": "#8BCB9B",
}

EDGE_COLORS = {
    "REAL": "#587EAB",
    "2D": "#8666B0",
    "VR": "#5E9F6F",
}


# ============================================================
# PAPER TYPOGRAPHY
# ============================================================

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 7,
    "axes.labelsize": 7,
    "xtick.labelsize": 6,
    "ytick.labelsize": 6,
    "legend.fontsize": 6.5,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


# ============================================================
# HELPERS
# ============================================================

def load_trial(participant, condition, trial):

    f = (
        DATA_DIR
        / f"{participant}_{condition}_{trial}"
        / "telemetry.csv"
    )

    if not f.exists():
        return None

    df = pd.read_csv(f)

    required = [
        "object_x",
        "object_y",
        "object_z",
    ]

    if not all(
        c in df.columns
        for c in required
    ):
        return None

    xyz = (
        df[required]
        .apply(
            pd.to_numeric,
            errors="coerce"
        )
        .dropna()
        .to_numpy()
    )

    if len(xyz) < 10:
        return None

    return xyz


def path_length(xyz):

    if xyz is None or len(xyz) < 2:
        return 0.0

    d = np.diff(
        xyz,
        axis=0
    )

    return np.sqrt(
        (d ** 2).sum(axis=1)
    ).sum()


def trim_static_edges(xyz):

    """
    Remove long static sections before/after the object transfer.

    Uses point-to-point motion magnitude to detect where the puck
    actually starts and stops moving.
    """

    if xyz is None or len(xyz) < 20:
        return xyz

    step = np.sqrt(
        (
            np.diff(
                xyz,
                axis=0
            ) ** 2
        ).sum(axis=1)
    )

    # Light smoothing
    kernel = np.ones(15) / 15

    smooth = np.convolve(
        step,
        kernel,
        mode="same"
    )

    # Robust threshold based on observed motion
    q75 = np.nanpercentile(
        smooth,
        75
    )

    threshold = max(
        q75 * 0.15,
        1e-5
    )

    moving = np.where(
        smooth > threshold
    )[0]

    if len(moving) == 0:
        return xyz

    start = max(
        int(moving[0]) - 10,
        0
    )

    end = min(
        int(moving[-1]) + 12,
        len(xyz) - 1
    )

    trimmed = xyz[
        start:end + 1
    ]

    if len(trimmed) < 10:
        return xyz

    return trimmed


def resample_path(xyz, n=250):

    """
    Resample a 3D path by cumulative distance, not raw time.
    This allows trajectories with different durations to be averaged.
    """

    if xyz is None or len(xyz) < 2:
        return None

    diffs = np.diff(
        xyz,
        axis=0
    )

    seg = np.sqrt(
        (diffs ** 2).sum(axis=1)
    )

    cumulative = np.concatenate(
        [
            [0.0],
            np.cumsum(seg)
        ]
    )

    total = cumulative[-1]

    if total <= 1e-8:
        return None

    u = cumulative / total

    target = np.linspace(
        0,
        1,
        n
    )

    out = np.column_stack([
        np.interp(
            target,
            u,
            xyz[:, dim]
        )
        for dim in range(3)
    ])

    return out


def normalize_start(xyz):

    """
    Shift every path so table pickup starts at (0, 0, 0).
    """

    if xyz is None:
        return None

    return xyz - xyz[0]


def participant_condition_path(
    participant,
    condition
):

    paths = []

    for trial in TRIALS:

        xyz = load_trial(
            participant,
            condition,
            trial
        )

        if xyz is None:
            continue

        # Reject missing / effectively flat object trajectories.
        raw_length = path_length(xyz)

        if raw_length < 0.20:
            print(
                f"EXCLUDE {participant} {condition} {trial}: "
                f"object path too small ({raw_length:.3f} m)"
            )
            continue

        xyz = trim_static_edges(
            xyz
        )

        xyz = normalize_start(
            xyz
        )

        xyz = resample_path(
            xyz,
            n=250
        )

        if xyz is not None:
            paths.append(xyz)

    if len(paths) == 0:
        return None

    # Average T02 and T03 for this participant
    return np.nanmean(
        np.stack(paths),
        axis=0
    )


# ============================================================
# BUILD PATH DATA
# ============================================================

all_paths = {
    condition: []
    for condition in CONDITIONS
}


for condition in CONDITIONS:

    for participant in PAIRED_PARTICIPANTS:

        path = participant_condition_path(
            participant,
            condition
        )

        if path is not None:
            all_paths[
                condition
            ].append(
                (
                    participant,
                    path
                )
            )


print("Participants represented:")

for condition in CONDITIONS:

    print(
        condition,
        len(
            all_paths[
                condition
            ]
        )
    )


# ============================================================
# GLOBAL AXIS LIMITS
# ============================================================

all_xyz = []

for condition in CONDITIONS:

    for _, path in all_paths[
        condition
    ]:
        all_xyz.append(
            path
        )


stacked = np.concatenate(
    all_xyz,
    axis=0
)


xmin, ymin, zmin = np.nanpercentile(
    stacked,
    1,
    axis=0
)

xmax, ymax, zmax = np.nanpercentile(
    stacked,
    99,
    axis=0
)


# small padding
def pad(lo, hi, frac=0.08):

    span = hi - lo

    if span <= 0:
        span = 1

    return (
        lo - span * frac,
        hi + span * frac
    )


xlim = pad(
    xmin,
    xmax
)

ylim = pad(
    ymin,
    ymax
)

zlim = pad(
    zmin,
    zmax
)


# ============================================================
# PLOT
# ============================================================

fig = plt.figure(
    figsize=(7.15, 2.8)
)


for idx, condition in enumerate(
    CONDITIONS,
    start=1
):

    ax = fig.add_subplot(
        1,
        3,
        idx,
        projection="3d"
    )

    paths = [
        p
        for _, p
        in all_paths[
            condition
        ]
    ]

    # Thin participant paths
    for path in paths:

        ax.plot(
            path[:, 0],
            path[:, 1],
            path[:, 2],
            color=COLORS[
                condition
            ],
            alpha=0.20,
            linewidth=0.65,
            zorder=1
        )

    # Condition mean
    mean_path = np.nanmean(
        np.stack(paths),
        axis=0
    )

    ax.plot(
        mean_path[:, 0],
        mean_path[:, 1],
        mean_path[:, 2],
        color=EDGE_COLORS[
            condition
        ],
        linewidth=2.4,
        zorder=5
    )

    # Start marker
    ax.scatter(
        mean_path[0, 0],
        mean_path[0, 1],
        mean_path[0, 2],
        s=32,
        marker="o",
        facecolor="white",
        edgecolor="black",
        linewidth=0.8,
        zorder=8
    )

    # Placement marker
    ax.scatter(
        mean_path[-1, 0],
        mean_path[-1, 1],
        mean_path[-1, 2],
        s=42,
        marker="^",
        color=EDGE_COLORS[
            condition
        ],
        zorder=8
    )

    title = (
        "In-person"
        if condition == "REAL"
        else condition
    )

    ax.set_title(
        f"{title} (n={len(paths)})",
        color=EDGE_COLORS[
            condition
        ],
        fontsize=8,
        fontweight="bold",
        pad=7
    )

    ax.set_xlabel(
        "Horizontal displacement X (m)",
        labelpad=2
    )

    ax.set_ylabel(
        "Horizontal displacement Y (m)",
        labelpad=2
    )

    ax.set_zlabel(
        "Vertical displacement (m)",
        labelpad=2
    )

    ax.set_xlim(
        *xlim
    )

    ax.set_ylim(
        *ylim
    )

    ax.set_zlim(
        *zlim
    )

    ax.view_init(
        elev=24,
        azim=-55
    )

    ax.grid(
        True,
        alpha=0.15
    )


# ============================================================
# LEGEND
# ============================================================

from matplotlib.lines import Line2D

legend_elements = [
    Line2D(
        [0],
        [0],
        color="0.70",
        linewidth=0.8,
        label="Participant trajectory"
    ),

    Line2D(
        [0],
        [0],
        color="0.30",
        linewidth=2.4,
        label="Condition mean"
    ),

    Line2D(
        [0],
        [0],
        marker="o",
        linestyle="None",
        markerfacecolor="white",
        markeredgecolor="black",
        markersize=5,
        label="Table start"
    ),

    Line2D(
        [0],
        [0],
        marker="^",
        linestyle="None",
        color="0.35",
        markersize=6,
        label="Shelf placement"
    ),
]


fig.legend(
    handles=legend_elements,
    loc="upper center",
    bbox_to_anchor=(
        0.5,
        1.03
    ),
    ncol=4,
    frameon=False
)


fig.subplots_adjust(
    top=0.82,
    bottom=0.09,
    left=0.02,
    right=0.98,
    wspace=0.08
)


# ============================================================
# SAVE
# ============================================================

out_pdf = (
    "puck_transfer_trajectories_full.pdf"
)

out_png = (
    "puck_transfer_trajectories_full.png"
)


plt.savefig(
    out_pdf,
    bbox_inches="tight",
    pad_inches=0.02
)

plt.savefig(
    out_png,
    dpi=600,
    bbox_inches="tight",
    pad_inches=0.02
)

print("\nSaved:")
print(out_pdf)
print(out_png)


