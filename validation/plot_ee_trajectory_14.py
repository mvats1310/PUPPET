#!/usr/bin/env python3

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


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
# LOAD EE
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

    cols = ["ee_x", "ee_y", "ee_z"]

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

    if np.linalg.norm(np.ptp(xyz, axis=0)) < 0.01:
        return None

    return xyz


# ============================================================
# CLEAN
# ============================================================

def clean_trajectory(xyz):

    df = pd.DataFrame(
        xyz,
        columns=["x", "y", "z"]
    )

    step = np.linalg.norm(
        np.diff(df[["x", "y", "z"]].values, axis=0),
        axis=1
    )

    bad = np.concatenate([
        [False],
        step > 0.15
    ])

    df.loc[bad, ["x", "y", "z"]] = np.nan

    df = (
        df
        .interpolate(
            limit=10,
            limit_direction="both"
        )
        .dropna()
    )

    df = (
        df
        .rolling(
            window=7,
            center=True,
            min_periods=1
        )
        .mean()
    )

    return df[["x", "y", "z"]].to_numpy()


# ============================================================
# EXTRACT MAIN MOTION
# ============================================================

def extract_motion(xyz):

    xyz = clean_trajectory(xyz)

    if len(xyz) < 20:
        return None

    step = np.linalg.norm(
        np.diff(xyz, axis=0),
        axis=1
    )

    step_smooth = (
        pd.Series(step)
        .rolling(
            window=15,
            center=True,
            min_periods=1
        )
        .median()
        .to_numpy()
    )

    positive = step_smooth[
        step_smooth > 0
    ]

    if len(positive) == 0:
        return None

    threshold = max(
        np.percentile(positive, 30),
        0.0002
    )

    moving = np.where(
        step_smooth > threshold
    )[0]

    if len(moving) < 10:
        return None

    start = max(
        moving[0] - 5,
        0
    )

    end = min(
        moving[-1] + 6,
        len(xyz)
    )

    segment = xyz[start:end]

    if len(segment) < 20:
        return None

    # Align all trajectories to the same start
    segment = segment - segment[0]

    return segment


# ============================================================
# RESAMPLE
# ============================================================

def resample_trajectory(xyz, n=250):

    step = np.linalg.norm(
        np.diff(xyz, axis=0),
        axis=1
    )

    cumulative = np.concatenate([
        [0],
        np.cumsum(step)
    ])

    total = cumulative[-1]

    if total < 1e-6:
        return None

    progress = cumulative / total
    target = np.linspace(0, 1, n)

    out = np.zeros((n, 3))

    for d in range(3):

        out[:, d] = np.interp(
            target,
            progress,
            xyz[:, d]
        )

    return out


# ============================================================
# COLLECT PARTICIPANT MEANS
# ============================================================

condition_trajectories = {
    "2D": [],
    "VR": []
}

included = {
    "2D": [],
    "VR": []
}


for condition in CONDITIONS:

    for participant in PAIRED_PARTICIPANTS:

        valid_trials = []

        for trial in TRIALS:

            xyz = load_trial(
                participant,
                condition,
                trial
            )

            if xyz is None:
                continue

            segment = extract_motion(
                xyz
            )

            if segment is None:
                continue

            segment = resample_trajectory(
                segment,
                n=250
            )

            if segment is not None:
                valid_trials.append(
                    segment
                )

        if len(valid_trials) == 0:
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
# CONDITION MEAN + SEM
# ============================================================

condition_means = {}
condition_sem = {}

for condition in CONDITIONS:

    stack = np.stack(
        condition_trajectories[
            condition
        ]
    )

    condition_means[
        condition
    ] = np.mean(
        stack,
        axis=0
    )

    condition_sem[
        condition
    ] = (
        np.std(
            stack,
            axis=0,
            ddof=1
        )
        /
        np.sqrt(
            stack.shape[0]
        )
    )


print("\nEND-EFFECTOR TRAJECTORY PARTICIPANTS")

for condition in CONDITIONS:
    print(
        condition,
        f"n={len(included[condition])}",
        included[condition]
    )


# ============================================================
# TYPOGRAPHY
# ============================================================

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


# ============================================================
# PLOT
# ============================================================

fig, (ax1, ax2) = plt.subplots(
    1,
    2,
    figsize=(8.6, 3.5)
)


# ============================================================
# (a) TOP VIEW: X–Y
# ============================================================

for condition in CONDITIONS:

    mean = condition_means[
        condition
    ]

    ax1.plot(
        mean[:, 0],
        mean[:, 1],
        color=edge_colors[condition],
        linewidth=3.0,
        label=condition,
        zorder=3
    )

    ax1.scatter(
        mean[0, 0],
        mean[0, 1],
        s=45,
        facecolor="white",
        edgecolor=edge_colors[condition],
        linewidth=1.5,
        zorder=4
    )


ax1.set_xlabel(
    "End-effector displacement X (m)"
)

ax1.set_ylabel(
    "End-effector displacement Y (m)"
)

ax1.set_title(
    "(a) Top view",
    fontweight="bold"
)

ax1.grid(
    linewidth=0.5,
    alpha=0.15
)

ax1.spines["top"].set_visible(False)
ax1.spines["right"].set_visible(False)

ax1.set_aspect(
    "equal",
    adjustable="datalim"
)


# ============================================================
# (b) SIDE VIEW: X–Z
# ============================================================

for condition in CONDITIONS:

    mean = condition_means[
        condition
    ]

    ax2.plot(
        mean[:, 0],
        mean[:, 2],
        color=edge_colors[condition],
        linewidth=3.0,
        label=condition,
        zorder=3
    )

    ax2.scatter(
        mean[0, 0],
        mean[0, 2],
        s=45,
        facecolor="white",
        edgecolor=edge_colors[condition],
        linewidth=1.5,
        zorder=4
    )


ax2.set_xlabel(
    "End-effector displacement X (m)"
)

ax2.set_ylabel(
    "End-effector displacement Z (m)"
)

ax2.set_title(
    "(b) Side view",
    fontweight="bold"
)

ax2.grid(
    linewidth=0.5,
    alpha=0.15
)

ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_visible(False)


# ============================================================
# LEGEND
# ============================================================

handles, labels = ax2.get_legend_handles_labels()

fig.legend(
    handles,
    labels,
    loc="upper center",
    bbox_to_anchor=(0.5, 0.99),
    ncol=2,
    frameon=False
)


# ============================================================
# LAYOUT
# ============================================================

fig.subplots_adjust(
    left=0.09,
    right=0.99,
    bottom=0.18,
    top=0.82,
    wspace=0.35
)


# ============================================================
# SAVE
# ============================================================

plt.savefig(
    "data/PUPPET_EE_2D_projection_clean.pdf",
    format="pdf",
    bbox_inches="tight",
    pad_inches=0.03
)

plt.savefig(
    "data/PUPPET_EE_2D_projection_clean.png",
    dpi=600,
    bbox_inches="tight",
    pad_inches=0.03
)

plt.show()