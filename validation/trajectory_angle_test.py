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

N_RESAMPLE = 120


# ============================================================
# FIND FILES
# ============================================================

pattern = re.compile(
    r"^(P\d+)_(REAL|2D|VR)_(T0[23])$"
)

records = []

for f in glob.glob(
    os.path.join(DATA_ROOT, "*", "telemetry.csv")
):

    folder = os.path.basename(
        os.path.dirname(f)
    )

    m = pattern.match(folder)

    if not m:
        continue

    participant, condition, trial = m.groups()

    records.append({
        "participant": participant,
        "condition": condition,
        "trial": trial,
        "path": f,
    })

files = pd.DataFrame(records)


# ============================================================
# LOAD OBJECT PATH
# ============================================================

def load_object(path):

    df = pd.read_csv(path)

    cols = [
        "object_x",
        "object_y",
        "object_z"
    ]

    xyz = (
        df[cols]
        .apply(pd.to_numeric, errors="coerce")
        .dropna()
        .to_numpy(dtype=float)
    )

    if len(xyz) < 5:
        return None

    # Remove consecutive duplicates
    d = np.linalg.norm(
        np.diff(xyz, axis=0),
        axis=1
    )

    keep = np.concatenate([
        [True],
        d > 1e-8
    ])

    xyz = xyz[keep]

    if len(xyz) < 5:
        return None

    # Align starting point
    xyz = xyz - xyz[0]

    return xyz


def resample(xyz):

    d = np.linalg.norm(
        np.diff(xyz, axis=0),
        axis=1
    )

    s = np.concatenate([
        [0],
        np.cumsum(d)
    ])

    if s[-1] <= 1e-9:
        return None

    keep = np.concatenate([
        [True],
        np.diff(s) > 1e-10
    ])

    xyz = xyz[keep]
    s = s[keep]

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
# LOAD
# ============================================================

paths = {
    c: []
    for c in CONDITIONS
}

for _, row in files.iterrows():

    xyz = load_object(row["path"])

    if xyz is None:
        continue

    xyz = resample(xyz)

    if xyz is None:
        continue

    paths[row["condition"]].append(
        xyz
    )


# ============================================================
# COMMON LIMITS
# ============================================================

all_xyz = np.concatenate(
    [
        p
        for c in CONDITIONS
        for p in paths[c]
    ],
    axis=0
)

mins = np.nanmin(all_xyz, axis=0)
maxs = np.nanmax(all_xyz, axis=0)

span = maxs - mins
span[span < 1e-6] = 0.1

mins -= span * 0.05
maxs += span * 0.05


# ============================================================
# CANDIDATE ANGLES
# ============================================================

angles = [
    (15, -90),
    (20, -60),
    (25, -45),
    (20, -30),
    (35, -60),
    (45, -45),
]


plt.rcParams.update({
    "font.family": "serif",
    "font.size": 8,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


fig = plt.figure(
    figsize=(11, 7)
)


for i, (elev, azim) in enumerate(
    angles,
    start=1
):

    ax = fig.add_subplot(
        2,
        3,
        i,
        projection="3d"
    )

    # Plot VR for angle testing because it has
    # the widest-looking spread
    condition = "VR"

    for p in paths[condition]:

        ax.plot(
            p[:, 0],
            p[:, 1],
            p[:, 2],
            color=LIGHT[condition],
            linewidth=0.8,
            alpha=0.25
        )

    stack = np.stack(
        paths[condition],
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
        color=COLORS[condition],
        linewidth=2.8
    )

    ax.set_xlim(mins[0], maxs[0])
    ax.set_ylim(mins[1], maxs[1])
    ax.set_zlim(mins[2], maxs[2])

    ax.view_init(
        elev=elev,
        azim=azim
    )

    # Less perspective distortion
    try:
        ax.set_proj_type("ortho")
    except Exception:
        pass

    ax.set_title(
        f"elev={elev}, azim={azim}"
    )

    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")


fig.tight_layout()

out = os.path.join(
    OUTPUT_DIR,
    "trajectory_angle_comparison.pdf"
)

plt.savefig(
    out,
    bbox_inches="tight"
)

plt.close()

print("Saved:")
print(out)
