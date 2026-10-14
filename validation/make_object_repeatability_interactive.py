#!/usr/bin/env python3

import os
import re
import glob

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from mpl_toolkits.mplot3d import Axes3D
from matplotlib.lines import Line2D


# ============================================================
# SETTINGS
# ============================================================

DATA_ROOT = "data"
OUTPUT_DIR = "trajectory_repeatability_results"

CONDITIONS = ["REAL", "2D", "VR"]
TRIALS = ["T02", "T03"]

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

LIGHT = {
    "REAL": "#a6bddb",
    "2D":   "#bcbddc",
    "VR":   "#99d8c9",
}

N_RESAMPLE = 150

# Initial view only.
# You can rotate interactively later.
INITIAL_ELEV = 18
INITIAL_AZIM = -68

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# FIND EXECUTION-TRIAL TELEMETRY
# ============================================================

pattern = re.compile(
    r"^(P\d+)_(REAL|2D|VR)_(T0[23])$"
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

    participant, condition, trial = match.groups()

    records.append({
        "participant": participant,
        "condition": condition,
        "trial": trial,
        "path": path,
    })


files = pd.DataFrame(records)

if files.empty:
    raise RuntimeError(
        "No T02/T03 telemetry.csv files found."
    )


# ============================================================
# LOAD OBJECT TRAJECTORY
# ============================================================

def load_object(path):

    df = pd.read_csv(path)

    cols = [
        "object_x",
        "object_y",
        "object_z",
    ]

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

    # Remove consecutive duplicate samples
    step = np.linalg.norm(
        np.diff(
            xyz,
            axis=0
        ),
        axis=1
    )

    keep = np.concatenate([
        [True],
        step > 1e-8
    ])

    xyz = xyz[keep]

    if len(xyz) < 5:
        return None

    # Start-align each trial
    xyz = (
        xyz
        -
        xyz[0]
    )

    return xyz


# ============================================================
# RESAMPLE BY ARC LENGTH
# ============================================================

def resample(xyz):

    step = np.linalg.norm(
        np.diff(
            xyz,
            axis=0
        ),
        axis=1
    )

    s = np.concatenate([
        [0.0],
        np.cumsum(step)
    ])

    if s[-1] <= 1e-9:
        return None

    unique = np.concatenate([
        [True],
        np.diff(s) > 1e-10
    ])

    xyz = xyz[unique]
    s = s[unique]

    if len(xyz) < 2:
        return None

    target = np.linspace(
        0,
        s[-1],
        N_RESAMPLE
    )

    return np.column_stack([
        np.interp(
            target,
            s,
            xyz[:, axis]
        )
        for axis in range(3)
    ])


# ============================================================
# LOAD TRAJECTORIES
# ============================================================

paths = {
    condition: []
    for condition in CONDITIONS
}

participants = {
    condition: set()
    for condition in CONDITIONS
}


for _, row in files.iterrows():

    xyz = load_object(
        row["path"]
    )

    if xyz is None:
        continue

    xyz = resample(
        xyz
    )

    if xyz is None:
        continue

    paths[
        row["condition"]
    ].append(
        xyz
    )

    participants[
        row["condition"]
    ].add(
        row["participant"]
    )


print("\nTRAJECTORIES INCLUDED")

for condition in CONDITIONS:

    print(
        f"{DISPLAY[condition]}: "
        f"{len(paths[condition])} trajectories, "
        f"{len(participants[condition])} participants"
    )


# ============================================================
# COMMON AXIS LIMITS
# ============================================================

all_xyz = np.concatenate(
    [
        trajectory
        for condition in CONDITIONS
        for trajectory in paths[condition]
    ],
    axis=0
)

mins = np.nanmin(
    all_xyz,
    axis=0
)

maxs = np.nanmax(
    all_xyz,
    axis=0
)

span = maxs - mins

span[
    span < 1e-6
] = 0.1

mins -= span * 0.03
maxs += span * 0.03


# ============================================================
# TYPOGRAPHY
# ============================================================

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 14,
    "axes.labelsize": 13,
    "axes.titlesize": 18,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 12,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


# ============================================================
# FIGURE
# ============================================================

fig = plt.figure(
    figsize=(16.5, 5.8)
)

axes = []


for panel_index, condition in enumerate(
    CONDITIONS,
    start=1
):

    ax = fig.add_subplot(
        1,
        3,
        panel_index,
        projection="3d"
    )

    axes.append(ax)

    condition_paths = paths[
        condition
    ]


    # --------------------------------------------------------
    # INDIVIDUAL TRAJECTORIES
    # --------------------------------------------------------

    for trajectory in condition_paths:

        ax.plot(
            trajectory[:, 0],
            trajectory[:, 1],
            trajectory[:, 2],
            color=LIGHT[
                condition
            ],
            linewidth=1.15,
            alpha=0.24,
            zorder=2
        )


    # --------------------------------------------------------
    # MEAN TRAJECTORY
    # --------------------------------------------------------

    if condition_paths:

        stack = np.stack(
            condition_paths,
            axis=0
        )

        mean_path = np.mean(
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
            linewidth=4.5,
            alpha=1.0,
            zorder=5
        )


        # ====================================================
        # START MARKER
        # open circle
        # ====================================================

        start = mean_path[0]

        ax.scatter(
            start[0],
            start[1],
            start[2],
            s=90,
            marker="o",
            facecolor="white",
            edgecolor=COLORS[
                condition
            ],
            linewidth=2.2,
            zorder=8
        )

        ax.text(
            start[0],
            start[1],
            start[2] + span[2] * 0.045,
            "Start",
            fontsize=10,
            ha="center",
            va="bottom",
            color="#222222",
            zorder=9
        )


        # ====================================================
        # FINISH MARKER
        # filled triangle
        # ====================================================

        finish = mean_path[-1]

        ax.scatter(
            finish[0],
            finish[1],
            finish[2],
            s=110,
            marker="^",
            facecolor=COLORS[
                condition
            ],
            edgecolor=COLORS[
                condition
            ],
            linewidth=1.5,
            zorder=8
        )

        ax.text(
            finish[0],
            finish[1],
            finish[2] + span[2] * 0.045,
            "Shelf",
            fontsize=10,
            ha="center",
            va="bottom",
            color="#222222",
            zorder=9
        )


    # ========================================================
    # AXES
    # ========================================================

    ax.set_xlim(
        mins[0],
        maxs[0]
    )

    ax.set_ylim(
        mins[1],
        maxs[1]
    )

    ax.set_zlim(
        mins[2],
        maxs[2]
    )

    ax.set_xlabel(
        "Horizontal displacement X (m)",
        labelpad=10
    )

    ax.set_ylabel(
        "Horizontal displacement Y (m)",
        labelpad=10
    )

    ax.set_zlabel(
        "Vertical displacement (m)",
        labelpad=10
    )

    n = len(
        participants[
            condition
        ]
    )

    ax.set_title(
        f"({chr(96 + panel_index)}) "
        f"{DISPLAY[condition]}  (n={n})",
        color=COLORS[
            condition
        ],
        fontweight="bold",
        pad=22
    )


    # ========================================================
    # INITIAL CAMERA
    # ========================================================

    ax.view_init(
        elev=INITIAL_ELEV,
        azim=INITIAL_AZIM
    )

    try:
        ax.set_proj_type("ortho")
    except Exception:
        pass


    # ========================================================
    # CLEANER GRID
    # ========================================================

    ax.grid(
        True,
        linewidth=0.45,
        alpha=0.25
    )

    try:
        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False

        ax.xaxis.pane.set_edgecolor("#dddddd")
        ax.yaxis.pane.set_edgecolor("#dddddd")
        ax.zaxis.pane.set_edgecolor("#dddddd")
    except Exception:
        pass


# ============================================================
# LEGEND
# ============================================================

legend_handles = [

    Line2D(
        [0],
        [0],
        color="#bbbbbb",
        linewidth=1.4,
        alpha=0.65,
        label="Execution trajectory"
    ),

    Line2D(
        [0],
        [0],
        color="#444444",
        linewidth=4.0,
        label="Condition mean"
    ),

    Line2D(
        [0],
        [0],
        marker="o",
        linestyle="None",
        markerfacecolor="white",
        markeredgecolor="black",
        markersize=8,
        label="Start"
    ),

    Line2D(
        [0],
        [0],
        marker="^",
        linestyle="None",
        markerfacecolor="black",
        markeredgecolor="black",
        markersize=8,
        label="Shelf placement"
    ),
]

fig.legend(
    handles=legend_handles,
    loc="upper center",
    bbox_to_anchor=(
        0.5,
        1.01
    ),
    ncol=4,
    frameon=False,
    columnspacing=1.8,
    handlelength=2.0
)


# ============================================================
# KEEP ALL PANELS SYNCHRONIZED
# ============================================================

sync_lock = False


def sync_views(event):

    global sync_lock

    if sync_lock:
        return

    sync_lock = True

    source_ax = event.inaxes

    if source_ax in axes:

        elev = source_ax.elev
        azim = source_ax.azim

        for ax in axes:

            if ax is not source_ax:

                ax.view_init(
                    elev=elev,
                    azim=azim
                )

        fig.canvas.draw_idle()

    sync_lock = False


fig.canvas.mpl_connect(
    "button_release_event",
    sync_views
)


# ============================================================
# KEYBOARD SHORTCUTS
#
# p = print current angle
# s = save current view
# ============================================================

def on_key(event):

    if event.key == "p":

        elev = axes[0].elev
        azim = axes[0].azim

        print(
            f"\nCURRENT VIEW:"
            f" ELEV={elev:.1f},"
            f" AZIM={azim:.1f}"
        )


    if event.key == "s":

        elev = axes[0].elev
        azim = axes[0].azim

        pdf = os.path.join(
            OUTPUT_DIR,
            "H2_object_repeatability_FINAL.pdf"
        )

        png = os.path.join(
            OUTPUT_DIR,
            "H2_object_repeatability_FINAL.png"
        )

        plt.savefig(
            pdf,
            format="pdf",
            bbox_inches="tight",
            pad_inches=0.04
        )

        plt.savefig(
            png,
            dpi=600,
            bbox_inches="tight",
            pad_inches=0.04
        )

        print("\nSAVED CURRENT VIEW:")
        print(pdf)
        print(png)

        print(
            f"VIEW USED:"
            f" ELEV={elev:.1f},"
            f" AZIM={azim:.1f}"
        )


fig.canvas.mpl_connect(
    "key_press_event",
    on_key
)


# ============================================================
# LAYOUT
# ============================================================

fig.subplots_adjust(
    left=0.02,
    right=0.99,
    bottom=0.07,
    top=0.88,
    wspace=0.08
)


# ============================================================
# INSTRUCTIONS
# ============================================================

print("\n============================================================")
print("INTERACTIVE VIEW")
print("============================================================")
print("Left-click + drag: rotate")
print("Right-click + drag: zoom")
print("Press p: print current camera angle")
print("Press s: save current view as final PDF + PNG")
print("All three panels synchronize after mouse release.")
print("============================================================")


# ============================================================
# SHOW INTERACTIVE WINDOW
# ============================================================

plt.show()
