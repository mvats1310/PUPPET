#!/usr/bin/env python3

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

# ============================================================
# SETTINGS
# ============================================================

DATA_DIR = Path("data")

PARTICIPANTS = [
    "P02", "P03", "P04", "P06", "P08", "P09", "P11",
    "P12", "P13", "P14", "P15", "P16", "P17", "P18"
]

CONDITIONS = ["REAL", "2D", "VR"]
TRIALS = ["T02", "T03"]

COLORS = {
    "REAL": "#a6bddb",
    "2D":   "#bcbddc",
    "VR":   "#99d8c9"
}

EDGE_COLORS = {
    "REAL": "#2b8cbe",
    "2D":   "#756bb1",
    "VR":   "#2ca25f"
}

DISPLAY = {
    "REAL": "In-person",
    "2D": "2D",
    "VR": "VR"
}

N_POINTS = 150

# reject only clearly unusable object tracks
MIN_PATH_LENGTH = 0.20


# ============================================================
# HELPERS
# ============================================================

def path_length(xyz):
    if len(xyz) < 2:
        return 0.0

    return np.linalg.norm(
        np.diff(xyz, axis=0),
        axis=1
    ).sum()


def trim_static_ends(xyz, threshold=0.003):
    if len(xyz) < 5:
        return xyz

    steps = np.linalg.norm(
        np.diff(xyz, axis=0),
        axis=1
    )

    moving = np.where(
        steps > threshold
    )[0]

    if len(moving) == 0:
        return xyz

    start = max(
        0,
        moving[0] - 3
    )

    end = min(
        len(xyz),
        moving[-1] + 5
    )

    return xyz[start:end]


def start_align(xyz):
    return xyz - xyz[0]


def resample_by_distance(xyz, n=N_POINTS):
    if len(xyz) < 2:
        return None

    steps = np.linalg.norm(
        np.diff(xyz, axis=0),
        axis=1
    )

    cumdist = np.concatenate(
        [[0.0], np.cumsum(steps)]
    )

    total = cumdist[-1]

    if total <= 1e-6:
        return None

    target = np.linspace(
        0,
        total,
        n
    )

    out = np.zeros(
        (n, 3)
    )

    for j in range(3):
        out[:, j] = np.interp(
            target,
            cumdist,
            xyz[:, j]
        )

    return out


# ============================================================
# LOAD TRIAL TRAJECTORIES
# ============================================================

trial_trajectories = {
    c: {}
    for c in CONDITIONS
}

excluded = []

for participant in PARTICIPANTS:

    for condition in CONDITIONS:

        usable_trials = []

        for trial in TRIALS:

            f = (
                DATA_DIR
                / f"{participant}_{condition}_{trial}"
                / "telemetry.csv"
            )

            if not f.exists():
                excluded.append(
                    (
                        participant,
                        condition,
                        trial,
                        "missing telemetry"
                    )
                )
                continue

            df = pd.read_csv(f)

            cols = [
                "object_x",
                "object_y",
                "object_z"
            ]

            if not all(
                c in df.columns
                for c in cols
            ):
                excluded.append(
                    (
                        participant,
                        condition,
                        trial,
                        "missing object columns"
                    )
                )
                continue

            xyz = (
                df[cols]
                .apply(
                    pd.to_numeric,
                    errors="coerce"
                )
                .dropna()
                .to_numpy()
            )

            if len(xyz) < 20:
                excluded.append(
                    (
                        participant,
                        condition,
                        trial,
                        "too few rows"
                    )
                )
                continue

            raw_path = path_length(
                xyz
            )

            if raw_path < MIN_PATH_LENGTH:
                excluded.append(
                    (
                        participant,
                        condition,
                        trial,
                        f"path too short ({raw_path:.3f} m)"
                    )
                )
                continue

            xyz = trim_static_ends(
                xyz
            )

            xyz = start_align(
                xyz
            )

            xyz = resample_by_distance(
                xyz
            )

            if xyz is None:
                excluded.append(
                    (
                        participant,
                        condition,
                        trial,
                        "resampling failed"
                    )
                )
                continue

            usable_trials.append(
                xyz
            )

        # participant mean over T02/T03
        if len(usable_trials) > 0:

            participant_mean = (
                np.mean(
                    usable_trials,
                    axis=0
                )
            )

            trial_trajectories[
                condition
            ][participant] = (
                participant_mean
            )


# ============================================================
# PRINT COVERAGE
# ============================================================

print("\nPARTICIPANTS REPRESENTED")

for condition in CONDITIONS:

    pts = sorted(
        trial_trajectories[
            condition
        ].keys()
    )

    print(
        f"{condition}: "
        f"n={len(pts)} -> "
        f"{', '.join(pts)}"
    )


print("\nEXCLUDED TRIALS")

for item in excluded:
    print(
        item
    )


# ============================================================
# CONDITION MEANS
# ============================================================

condition_means = {}

for condition in CONDITIONS:

    trajs = list(
        trial_trajectories[
            condition
        ].values()
    )

    if len(trajs) == 0:
        condition_means[
            condition
        ] = None
        continue

    condition_means[
        condition
    ] = np.mean(
        trajs,
        axis=0
    )


# ============================================================
# PAPER TYPOGRAPHY
# ============================================================

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 7,
    "axes.labelsize": 7,
    "xtick.labelsize": 6,
    "ytick.labelsize": 6,
    "legend.fontsize": 6.2,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


# ============================================================
# PLOT
# ============================================================

fig = plt.figure(
    figsize=(7.0, 2.65)
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

    participant_dict = (
        trial_trajectories[
            condition
        ]
    )

    # thin participant means
    for participant, traj in (
        participant_dict.items()
    ):

        ax.plot(
            traj[:, 0],
            traj[:, 1],
            traj[:, 2],
            color=colors[
                condition
            ],
            alpha=0.35,
            linewidth=0.8,
            zorder=2
        )

    # bold condition mean
    mean_traj = (
        condition_means[
            condition
        ]
    )

    if mean_traj is not None:

        ax.plot(
            mean_traj[:, 0],
            mean_traj[:, 1],
            mean_traj[:, 2],
            color=EDGE_COLORS[
                condition
            ],
            linewidth=2.8,
            zorder=4
        )

        # start
        ax.scatter(
            mean_traj[0, 0],
            mean_traj[0, 1],
            mean_traj[0, 2],
            s=28,
            facecolor="white",
            edgecolor="black",
            linewidth=0.8,
            zorder=6
        )

        # endpoint
        ax.scatter(
            mean_traj[-1, 0],
            mean_traj[-1, 1],
            mean_traj[-1, 2],
            s=42,
            marker="^",
            color=EDGE_COLORS[
                condition
            ],
            zorder=6
        )

    ax.set_title(
        f"{DISPLAY[condition]} "
        f"(n={len(participant_dict)})",
        color=EDGE_COLORS[
            condition
        ],
        fontweight="bold",
        fontsize=8
    )

    ax.set_xlabel(
        r"$\Delta X$ (m)"
    )

    ax.set_ylabel(
        r"$\Delta Y$ (m)"
    )

    ax.set_zlabel(
        r"$\Delta Z$ (m)"
    )

    ax.grid(
        True,
        alpha=0.15
    )

    # same viewing angle
    ax.view_init(
        elev=22,
        azim=-58
    )


# ============================================================
# SAME AXIS LIMITS ACROSS CONDITIONS
# ============================================================

all_trajs = []

for condition in CONDITIONS:

    all_trajs.extend(
        trial_trajectories[
            condition
        ].values()
    )

if len(all_trajs) > 0:

    all_xyz = np.concatenate(
        all_trajs,
        axis=0
    )

    mins = np.nanpercentile(
        all_xyz,
        1,
        axis=0
    )

    maxs = np.nanpercentile(
        all_xyz,
        99,
        axis=0
    )

    pads = (
        (maxs - mins)
        * 0.08
    )

    for ax in fig.axes:

        ax.set_xlim(
            mins[0] - pads[0],
            maxs[0] + pads[0]
        )

        ax.set_ylim(
            mins[1] - pads[1],
            maxs[1] + pads[1]
        )

        ax.set_zlim(
            mins[2] - pads[2],
            maxs[2] + pads[2]
        )


# ============================================================
# LEGEND
# ============================================================

from matplotlib.lines import Line2D

legend_items = [

    Line2D(
        [0],
        [0],
        color="#999999",
        linewidth=0.8,
        alpha=0.45,
        label="Participant mean"
    ),

    Line2D(
        [0],
        [0],
        color="#555555",
        linewidth=2.8,
        label="Condition mean"
    ),

    Line2D(
        [0],
        [0],
        marker="o",
        markerfacecolor="white",
        markeredgecolor="black",
        linestyle="None",
        markersize=5,
        label="Table start"
    ),

    Line2D(
        [0],
        [0],
        marker="^",
        color="#555555",
        linestyle="None",
        markersize=5,
        label="Shelf placement"
    )
]


fig.legend(
    handles=legend_items,
    loc="upper center",
    bbox_to_anchor=(
        0.5,
        1.02
    ),
    ncol=4,
    frameon=False
)


fig.tight_layout(
    rect=[
        0,
        0,
        1,
        0.92
    ]
)


# ============================================================
# SAVE
# ============================================================

plt.savefig(
    "puck_transfer_trajectories_14pts.pdf",
    format="pdf",
    bbox_inches="tight",
    pad_inches=0.02
)

plt.savefig(
    "puck_transfer_trajectories_14pts.png",
    dpi=600,
    bbox_inches="tight",
    pad_inches=0.02
)

print(
    "\nSaved:"
)

print(
    "puck_transfer_trajectories_14pts.pdf"
)

print(
    "puck_transfer_trajectories_14pts.png"
)
