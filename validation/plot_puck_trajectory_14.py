#!/usr/bin/env python3

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
from matplotlib.lines import Line2D


# ============================================================
# SETTINGS
# ============================================================

DATA_DIR = "data"

PAIRED_PARTICIPANTS = [
    "P02", "P03", "P04", "P06",
    "P08", "P09", "P11", "P12",
    "P13", "P14", "P15", "P16",
    "P17", "P18"
]

CONDITIONS = ["2D", "VR"]

# Execution trials only
TRIALS = ["T02", "T03"]

colors = {
    "2D": "#bcbddc",
    "VR": "#99d8c9"
}

edge_colors = {
    "2D": "#756bb1",
    "VR": "#2ca25f"
}


# ============================================================
# LOAD OBJECT TRAJECTORY
# ============================================================

def load_trial(participant, condition, trial):

    path = os.path.join(
        DATA_DIR,
        f"{participant}_{condition}_{trial}",
        "telemetry.csv"
    )

    if not os.path.exists(path):
        return None

    df = pd.read_csv(path)

    cols = [
        "object_x",
        "object_y",
        "object_z"
    ]

    if not all(c in df.columns for c in cols):
        return None

    xyz = (
        df[cols]
        .apply(pd.to_numeric, errors="coerce")
        .replace([np.inf, -np.inf], np.nan)
        .dropna()
        .to_numpy(dtype=float)
    )

    if len(xyz) < 20:
        return None

    # Reject flat object tracking
    ranges = np.ptp(
        xyz,
        axis=0
    )

    if np.linalg.norm(ranges) < 0.01:
        return None

    return xyz


# ============================================================
# CLEAN TRACKING
# ============================================================

def clean_tracking(xyz):

    if xyz is None or len(xyz) < 3:
        return None

    df = pd.DataFrame(
        xyz,
        columns=["x", "y", "z"]
    )

    # --------------------------------------------------------
    # Remove obvious tracking jumps
    # --------------------------------------------------------

    step = np.linalg.norm(
        np.diff(
            df[["x", "y", "z"]].values,
            axis=0
        ),
        axis=1
    )

    bad = np.concatenate([
        [False],
        step > 0.12
    ])

    df.loc[
        bad,
        ["x", "y", "z"]
    ] = np.nan

    # Fill short tracking gaps
    df = (
        df
        .interpolate(
            limit=12,
            limit_direction="both"
        )
        .dropna()
    )

    # --------------------------------------------------------
    # Smooth OptiTrack jitter
    # --------------------------------------------------------

    df = (
        df
        .rolling(
            window=9,
            center=True,
            min_periods=1
        )
        .median()
    )

    xyz = df[
        ["x", "y", "z"]
    ].to_numpy()

    if len(xyz) < 20:
        return None

    return xyz


# ============================================================
# FIND STABLE HIGH SHELF REGION
# ============================================================

def find_shelf_region(xyz):

    """
    Find a stable high-z region representing final shelf placement.
    """

    z = xyz[:, 2]

    n = len(xyz)

    window = max(
        10,
        int(0.03 * n)
    )

    # Rolling median height
    z_series = pd.Series(z)

    z_med = (
        z_series
        .rolling(
            window=window,
            center=True,
            min_periods=1
        )
        .median()
        .to_numpy()
    )

    # Upper portion of observed height
    z_low = np.percentile(
        z_med,
        10
    )

    z_high = np.percentile(
        z_med,
        95
    )

    z_range = (
        z_high - z_low
    )

    if z_range < 0.03:
        return None

    # Shelf candidate:
    # at least 65% of the way from low to high
    threshold = (
        z_low +
        0.65 * z_range
    )

    high_idx = np.where(
        z_med >= threshold
    )[0]

    if len(high_idx) == 0:
        return None

    # Prefer later high region because shelf placement
    # should happen after pickup
    later_half = high_idx[
        high_idx > int(0.35 * n)
    ]

    if len(later_half) > 0:
        high_idx = later_half

    # Group consecutive indices
    groups = []

    current = [high_idx[0]]

    for idx in high_idx[1:]:

        if idx == current[-1] + 1:
            current.append(idx)

        else:
            groups.append(current)
            current = [idx]

    groups.append(current)

    # Prefer the longest high stable region
    best_group = max(
        groups,
        key=len
    )

    shelf_center = int(
        np.median(best_group)
    )

    return shelf_center


# ============================================================
# EXTRACT TABLE -> SHELF TRANSFER
# ============================================================

def extract_transfer(xyz):

    xyz = clean_tracking(
        xyz
    )

    if xyz is None or len(xyz) < 20:
        return None

    n = len(xyz)

    # --------------------------------------------------------
    # Stable table start
    # --------------------------------------------------------

    start_window = max(
        10,
        int(0.05 * n)
    )

    table_ref = np.median(
        xyz[:start_window],
        axis=0
    )

    # --------------------------------------------------------
    # Find actual shelf region
    # --------------------------------------------------------

    shelf_center = find_shelf_region(
        xyz
    )

    if shelf_center is None:
        return None

    shelf_window = max(
        8,
        int(0.02 * n)
    )

    shelf_start = max(
        0,
        shelf_center - shelf_window
    )

    shelf_end = min(
        n,
        shelf_center + shelf_window + 1
    )

    shelf_ref = np.median(
        xyz[
            shelf_start:shelf_end
        ],
        axis=0
    )

    # --------------------------------------------------------
    # Confirm shelf is actually above table
    # --------------------------------------------------------

    delta_z = (
        shelf_ref[2] -
        table_ref[2]
    )

    # If first samples were already elevated,
    # use lower stable percentile as table height reference
    if delta_z < 0.03:

        z = xyz[:, 2]

        low_indices = np.where(
            z <= np.percentile(z, 20)
        )[0]

        early_low = low_indices[
            low_indices < shelf_center
        ]

        if len(early_low) > 0:

            table_center = int(
                np.median(early_low)
            )

            t0 = max(
                0,
                table_center - start_window
            )

            t1 = min(
                n,
                table_center + start_window + 1
            )

            table_ref = np.median(
                xyz[t0:t1],
                axis=0
            )

            delta_z = (
                shelf_ref[2] -
                table_ref[2]
            )

    # Still must be higher
    if delta_z < 0.03:
        return None

    # --------------------------------------------------------
    # Detect when puck leaves table
    # --------------------------------------------------------

    dist_from_table = np.linalg.norm(
        xyz - table_ref,
        axis=1
    )

    departure_candidates = np.where(
        dist_from_table > 0.025
    )[0]

    departure_candidates = departure_candidates[
        departure_candidates < shelf_center
    ]

    if len(departure_candidates) == 0:
        return None

    start_idx = max(
        departure_candidates[0] - 5,
        0
    )

    # --------------------------------------------------------
    # Detect shelf arrival
    # --------------------------------------------------------

    dist_to_shelf = np.linalg.norm(
        xyz - shelf_ref,
        axis=1
    )

    arrival_candidates = np.where(
        dist_to_shelf < 0.04
    )[0]

    arrival_candidates = arrival_candidates[
        arrival_candidates > start_idx
    ]

    if len(arrival_candidates) > 0:

        end_idx = min(
            arrival_candidates[0] + 10,
            n - 1
        )

    else:

        end_idx = min(
            shelf_center + 10,
            n - 1
        )

    if end_idx <= start_idx:
        return None

    segment = xyz[
        start_idx:end_idx + 1
    ]

    if len(segment) < 15:
        return None

    # --------------------------------------------------------
    # Align trajectory to table start
    # --------------------------------------------------------

    segment = (
        segment -
        segment[0]
    )

    # --------------------------------------------------------
    # Check final point is above start
    # --------------------------------------------------------

    if segment[-1, 2] < 0.02:
        return None

    return segment


# ============================================================
# RESAMPLE BY PATH PROGRESS
# ============================================================

def resample_trajectory(xyz, n=220):

    if xyz is None or len(xyz) < 2:
        return None

    step = np.linalg.norm(
        np.diff(
            xyz,
            axis=0
        ),
        axis=1
    )

    cumulative = np.concatenate([
        [0],
        np.cumsum(step)
    ])

    total = cumulative[-1]

    if total < 1e-6:
        return None

    progress = (
        cumulative / total
    )

    target = np.linspace(
        0,
        1,
        n
    )

    out = np.zeros(
        (n, 3)
    )

    for d in range(3):

        out[:, d] = np.interp(
            target,
            progress,
            xyz[:, d]
        )

    return out


# ============================================================
# COLLECT PARTICIPANT TRAJECTORIES
# ============================================================

condition_trajectories = {
    "2D": [],
    "VR": []
}

included = {
    "2D": [],
    "VR": []
}

excluded = {
    "2D": [],
    "VR": []
}


for condition in CONDITIONS:

    for participant in PAIRED_PARTICIPANTS:

        valid_trials = []

        print(
            f"\n{participant} {condition}"
        )

        for trial in TRIALS:

            xyz = load_trial(
                participant,
                condition,
                trial
            )

            if xyz is None:

                print(
                    f"  {trial}: unusable raw tracking"
                )

                continue

            segment = extract_transfer(
                xyz
            )

            if segment is None:

                print(
                    f"  {trial}: transfer not detected"
                )

                continue

            print(
                f"  {trial}: usable "
                f"| delta_z={segment[-1, 2]:.3f} m "
                f"| points={len(segment)}"
            )

            segment_rs = resample_trajectory(
                segment,
                n=220
            )

            if segment_rs is not None:

                valid_trials.append(
                    segment_rs
                )

        # ----------------------------------------------------
        # Keep participant if either T2 or T3 is usable
        # ----------------------------------------------------

        if len(valid_trials) == 0:

            excluded[
                condition
            ].append(
                participant
            )

            continue

        participant_mean = np.mean(
            np.stack(valid_trials),
            axis=0
        )

        condition_trajectories[
            condition
        ].append(
            participant_mean
        )

        included[
            condition
        ].append(
            participant
        )


# ============================================================
# REPORT COUNTS
# ============================================================

print("\n" + "=" * 65)
print("TRAJECTORY ANALYSIS PARTICIPANTS")
print("=" * 65)

for condition in CONDITIONS:

    print(
        f"\n{condition}: "
        f"n={len(included[condition])}"
    )

    print(
        "Included:",
        included[condition]
    )

    print(
        "Excluded:",
        excluded[condition]
    )


# ============================================================
# CONDITION MEANS
# ============================================================

condition_means = {}

for condition in CONDITIONS:

    trajectories = (
        condition_trajectories[
            condition
        ]
    )

    if len(trajectories) == 0:

        condition_means[
            condition
        ] = None

    else:

        condition_means[
            condition
        ] = np.mean(
            np.stack(
                trajectories
            ),
            axis=0
        )


# ============================================================
# TYPOGRAPHY
# ============================================================

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 13,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "legend.fontsize": 9,
    "pdf.fonttype": 42,
    "ps.fonttype": 42
})


# ============================================================
# COMMON AXIS LIMITS
# ============================================================

all_xyz = np.concatenate(
    [
        traj
        for condition in CONDITIONS
        for traj in condition_trajectories[
            condition
        ]
    ],
    axis=0
)

lower = np.percentile(
    all_xyz,
    2,
    axis=0
)

upper = np.percentile(
    all_xyz,
    98,
    axis=0
)

ranges = upper - lower

padding = np.maximum(
    ranges * 0.10,
    0.02
)

lower -= padding
upper += padding


# ============================================================
# FIGURE
# ============================================================

fig = plt.figure(
    figsize=(9.2, 4.5)
)

axes = [
    fig.add_subplot(
        1,
        2,
        1,
        projection="3d"
    ),
    fig.add_subplot(
        1,
        2,
        2,
        projection="3d"
    )
]


for ax, condition in zip(
    axes,
    CONDITIONS
):

    trajectories = (
        condition_trajectories[
            condition
        ]
    )

    mean_traj = (
        condition_means[
            condition
        ]
    )

    # --------------------------------------------------------
    # PARTICIPANT TRAJECTORIES
    # --------------------------------------------------------

    for traj in trajectories:

        ax.plot(
            traj[:, 0],
            traj[:, 1],
            traj[:, 2],
            color=colors[condition],
            linewidth=1.1,
            alpha=0.30,
            zorder=1
        )

    # --------------------------------------------------------
    # CONDITION MEAN
    # --------------------------------------------------------

    if mean_traj is not None:

        ax.plot(
            mean_traj[:, 0],
            mean_traj[:, 1],
            mean_traj[:, 2],
            color=edge_colors[condition],
            linewidth=4.0,
            alpha=1.0,
            zorder=5
        )

        # Table start
        ax.scatter(
            mean_traj[0, 0],
            mean_traj[0, 1],
            mean_traj[0, 2],
            s=70,
            facecolor="white",
            edgecolor="black",
            linewidth=1.3,
            marker="o",
            zorder=10
        )

        # Shelf placement
        ax.scatter(
            mean_traj[-1, 0],
            mean_traj[-1, 1],
            mean_traj[-1, 2],
            s=90,
            facecolor=edge_colors[condition],
            edgecolor=edge_colors[condition],
            marker="^",
            zorder=10
        )

    # --------------------------------------------------------
    # AXES
    # --------------------------------------------------------

    ax.set_xlim(
        lower[0],
        upper[0]
    )

    ax.set_ylim(
        lower[1],
        upper[1]
    )

    ax.set_zlim(
        lower[2],
        upper[2]
    )

    ax.set_xlabel(
        "Horizontal displacement X (m)",
        labelpad=7
    )

    ax.set_ylabel(
        "Horizontal displacement Y (m)",
        labelpad=7
    )

    ax.set_zlabel(
        "Vertical displacement (m)",
        labelpad=8
    )

    ax.set_title(
        f"{condition}  "
        f"(n={len(trajectories)})",
        color=edge_colors[condition],
        fontweight="bold",
        pad=12
    )

    ax.grid(True)

    # Initial view only.
    # You can rotate interactively.
    ax.view_init(
        elev=22,
        azim=-58
    )


# ============================================================
# TITLE
# ============================================================

fig.suptitle(
    "Puck Transfer Trajectories: Table to Shelf",
    fontsize=14,
    y=0.98
)


# ============================================================
# LEGEND
# ============================================================

legend_handles = [

    Line2D(
        [0],
        [0],
        color="gray",
        linewidth=1.3,
        alpha=0.35,
        label="Participant trajectory"
    ),

    Line2D(
        [0],
        [0],
        color="gray",
        linewidth=4,
        label="Condition mean"
    ),

    Line2D(
        [0],
        [0],
        marker="o",
        linestyle="None",
        markerfacecolor="white",
        markeredgecolor="black",
        markersize=7,
        label="Table start"
    ),

    Line2D(
        [0],
        [0],
        marker="^",
        linestyle="None",
        markerfacecolor="gray",
        markeredgecolor="gray",
        markersize=8,
        label="Shelf placement"
    )
]


fig.legend(
    handles=legend_handles,
    loc="upper center",
    bbox_to_anchor=(0.5, 0.91),
    ncol=4,
    frameon=False
)


# ============================================================
# NOTE
# ============================================================

fig.text(
    0.5,
    0.02,
    "Participant trajectories are averaged across available "
    "T2--T3 execution trials and translated to a common table start.",
    ha="center",
    fontsize=8
)


# ============================================================
# PRINT CAMERA ANGLES AFTER ROTATION
# ============================================================

def print_angles(event):

    print("\nCURRENT CAMERA ANGLES")

    for i, ax in enumerate(
        axes
    ):

        print(
            f"Panel {i+1}: "
            f"elev={ax.elev:.1f}, "
            f"azim={ax.azim:.1f}, "
            f"roll={getattr(ax, 'roll', 0):.1f}"
        )


fig.canvas.mpl_connect(
    "button_release_event",
    print_angles
)


# ============================================================
# LAYOUT
# ============================================================

fig.subplots_adjust(
    left=0.03,
    right=0.97,
    bottom=0.11,
    top=0.82,
    wspace=0.02
)


# ============================================================
# SAVE STATIC VERSION
# ============================================================

plt.savefig(
    "data/PUPPET_2D_VR_table_to_shelf_3D_fixed.pdf",
    format="pdf",
    bbox_inches="tight",
    pad_inches=0.03
)

plt.savefig(
    "data/PUPPET_2D_VR_table_to_shelf_3D_fixed.png",
    dpi=600,
    bbox_inches="tight",
    pad_inches=0.03
)


# ============================================================
# SHOW INTERACTIVE
# ============================================================

plt.show(block=True)