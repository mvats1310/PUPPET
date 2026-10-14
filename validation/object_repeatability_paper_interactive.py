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
OUT = "trajectory_repeatability_results"

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

INITIAL_ELEV = 20
INITIAL_AZIM = -65

os.makedirs(OUT, exist_ok=True)


# ============================================================
# FIND T02/T03 FILES
# ============================================================

pat = re.compile(
    r"^(P\d+)_(REAL|2D|VR)_(T0[23])$"
)

records = []

for f in glob.glob(
    os.path.join(DATA_ROOT, "*", "telemetry.csv")
):

    folder = os.path.basename(
        os.path.dirname(f)
    )

    m = pat.fullmatch(folder)

    if not m:
        continue

    participant, condition, trial = m.groups()

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


# ============================================================
# LOAD + CLEAN OBJECT PATH
#
# IMPORTANT:
# Cleaning here is VISUAL ONLY.
# It does not replace the trajectories used in the RMS/DTW
# statistics you already calculated.
# ============================================================

def load_path(f):

    df = pd.read_csv(f)

    xyz = (
        df[
            [
                "object_x",
                "object_y",
                "object_z"
            ]
        ]
        .apply(
            pd.to_numeric,
            errors="coerce"
        )
        .dropna()
        .to_numpy(dtype=float)
    )

    if len(xyz) < 20:
        return None


    # --------------------------------------------------------
    # Remove individual giant tracking jumps.
    # --------------------------------------------------------

    step = np.linalg.norm(
        np.diff(xyz, axis=0),
        axis=1
    )

    good = np.concatenate([
        [True],
        step < 0.12
    ])

    xyz = xyz[good]

    if len(xyz) < 20:
        return None


    # --------------------------------------------------------
    # Gentle median filter for visualization only.
    # --------------------------------------------------------

    xyz = (
        pd.DataFrame(
            xyz,
            columns=["x", "y", "z"]
        )
        .rolling(
            window=7,
            center=True,
            min_periods=1
        )
        .median()
        .to_numpy()
    )


    # --------------------------------------------------------
    # Start-align.
    # --------------------------------------------------------

    xyz = xyz - xyz[0]

    return xyz


# ============================================================
# ARC-LENGTH RESAMPLE
# ============================================================

def resample(xyz):

    ds = np.linalg.norm(
        np.diff(xyz, axis=0),
        axis=1
    )

    s = np.concatenate([
        [0.0],
        np.cumsum(ds)
    ])

    if s[-1] <= 1e-8:
        return None

    unique = np.concatenate([
        [True],
        np.diff(s) > 1e-9
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
            xyz[:, k]
        )
        for k in range(3)
    ])


# ============================================================
# LOAD ALL VALID EXECUTION PATHS
# ============================================================

paths = {
    c: []
    for c in CONDITIONS
}

participants = {
    c: set()
    for c in CONDITIONS
}


for _, row in files.iterrows():

    xyz = load_path(
        row["file"]
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


print("\nPLOTTED DATA:")

for c in CONDITIONS:

    print(
        f"{DISPLAY[c]}: "
        f"{len(paths[c])} execution trajectories "
        f"from {len(participants[c])} participants"
    )


# ============================================================
# ROBUST DISPLAY LIMITS
#
# Use percentiles instead of extreme min/max so one tracking
# excursion cannot destroy the visual scale.
# ============================================================

all_points = np.concatenate(
    [
        p
        for c in CONDITIONS
        for p in paths[c]
    ],
    axis=0
)


low = np.nanpercentile(
    all_points,
    1.0,
    axis=0
)

high = np.nanpercentile(
    all_points,
    99.0,
    axis=0
)

span = high - low

span[
    span < 0.05
] = 0.05

low -= span * 0.08
high += span * 0.08


# ============================================================
# TYPOGRAPHY
# ============================================================

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 12,
    "axes.labelsize": 11,
    "axes.titlesize": 16,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 11,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


# ============================================================
# FIGURE
# ============================================================

fig = plt.figure(
    figsize=(15.5, 5.1)
)

axes = []


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

    axes.append(ax)

    cond_paths = paths[
        condition
    ]


    # --------------------------------------------------------
    # ALL VALID EXECUTIONS — very faint
    # --------------------------------------------------------

    for trajectory in cond_paths:

        ax.plot(
            trajectory[:, 0],
            trajectory[:, 1],
            trajectory[:, 2],
            color=LIGHT[
                condition
            ],
            linewidth=0.75,
            alpha=0.12,
            zorder=1
        )


    # --------------------------------------------------------
    # MEDIAN trajectory
    #
    # Median is less distorted by unusual participant paths.
    # --------------------------------------------------------

    stack = np.stack(
        cond_paths,
        axis=0
    )

    centre = np.nanmedian(
        stack,
        axis=0
    )


    ax.plot(
        centre[:, 0],
        centre[:, 1],
        centre[:, 2],
        color=COLORS[
            condition
        ],
        linewidth=4.0,
        zorder=5
    )


    # ========================================================
    # START ○
    # ========================================================

    start = centre[0]

    ax.scatter(
        start[0],
        start[1],
        start[2],
        s=75,
        marker="o",
        facecolor="white",
        edgecolor=COLORS[
            condition
        ],
        linewidth=2.0,
        zorder=10
    )


    # ========================================================
    # END ▲
    # ========================================================

    end = centre[-1]

    ax.scatter(
        end[0],
        end[1],
        end[2],
        s=90,
        marker="^",
        facecolor=COLORS[
            condition
        ],
        edgecolor=COLORS[
            condition
        ],
        linewidth=1.2,
        zorder=10
    )


    # ========================================================
    # LABELS
    # ========================================================

    label_offset = max(
        (high[2] - low[2]) * 0.035,
        0.015
    )

    ax.text(
        start[0],
        start[1],
        start[2] + label_offset,
        "Start",
        fontsize=9,
        ha="center"
    )

    ax.text(
        end[0],
        end[1],
        end[2] + label_offset,
        "End",
        fontsize=9,
        ha="center"
    )


    # ========================================================
    # SAME LIMITS IN EVERY PANEL
    # ========================================================

    ax.set_xlim(
        low[0],
        high[0]
    )

    ax.set_ylim(
        low[1],
        high[1]
    )

    ax.set_zlim(
        low[2],
        high[2]
    )


    ax.set_xlabel(
        "X displacement (m)",
        labelpad=7
    )

    ax.set_ylabel(
        "Y displacement (m)",
        labelpad=7
    )

    ax.set_zlabel(
        "Z displacement (m)",
        labelpad=7
    )


    ax.set_title(
        f"({chr(96 + panel)}) "
        f"{DISPLAY[condition]}",
        color=COLORS[
            condition
        ],
        fontweight="bold",
        pad=15
    )


    ax.view_init(
        elev=INITIAL_ELEV,
        azim=INITIAL_AZIM
    )


    try:
        ax.set_proj_type("ortho")
    except Exception:
        pass


    # --------------------------------------------------------
    # Cleaner panes
    # --------------------------------------------------------

    try:
        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False
    except Exception:
        pass


# ============================================================
# LEGEND
# ============================================================

legend = [

    Line2D(
        [0],
        [0],
        linewidth=1,
        color="#bdbdbd",
        alpha=0.6,
        label="Execution trajectories"
    ),

    Line2D(
        [0],
        [0],
        linewidth=4,
        color="#444444",
        label="Median trajectory"
    ),

    Line2D(
        [0],
        [0],
        marker="o",
        linestyle="None",
        markerfacecolor="white",
        markeredgecolor="black",
        markersize=7,
        label="Start"
    ),

    Line2D(
        [0],
        [0],
        marker="^",
        linestyle="None",
        color="black",
        markersize=7,
        label="End"
    ),
]


fig.legend(
    handles=legend,
    loc="upper center",
    ncol=4,
    frameon=False,
    bbox_to_anchor=(0.5, 1.01)
)


# ============================================================
# SYNCHRONIZE CAMERA VIEW
# ============================================================

syncing = False


def sync_view(event):

    global syncing

    if syncing:
        return

    if event.inaxes not in axes:
        return

    syncing = True

    source = event.inaxes

    for ax in axes:

        if ax is source:
            continue

        ax.view_init(
            elev=source.elev,
            azim=source.azim
        )

    fig.canvas.draw_idle()

    syncing = False


fig.canvas.mpl_connect(
    "button_release_event",
    sync_view
)


# ============================================================
# HOTKEYS
#
# p = print current angle
# s = save final figure
# ============================================================

def key(event):

    if event.key == "p":

        print(
            "\nANGLE:",
            f"ELEV={axes[0].elev:.1f},",
            f"AZIM={axes[0].azim:.1f}"
        )


    elif event.key == "s":

        pdf = os.path.join(
            OUT,
            "H2_object_repeatability_PAPER.pdf"
        )

        png = os.path.join(
            OUT,
            "H2_object_repeatability_PAPER.png"
        )

        plt.savefig(
            pdf,
            bbox_inches="tight",
            pad_inches=0.03
        )

        plt.savefig(
            png,
            dpi=600,
            bbox_inches="tight",
            pad_inches=0.03
        )

        print("\nSAVED:")
        print(pdf)
        print(png)

        print(
            "ANGLE:",
            f"ELEV={axes[0].elev:.1f},",
            f"AZIM={axes[0].azim:.1f}"
        )


fig.canvas.mpl_connect(
    "key_press_event",
    key
)


# ============================================================
# LAYOUT
# ============================================================

fig.subplots_adjust(
    left=0.015,
    right=0.99,
    bottom=0.06,
    top=0.87,
    wspace=0.03
)


print("\nRotate with LEFT MOUSE.")
print("Press p to print the current angle.")
print("Press s when you like the view and it will save the PDF.")
print("\n○ = Start")
print("▲ = End")

plt.show()
