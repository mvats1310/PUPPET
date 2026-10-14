#!/usr/bin/env python3

import sys
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # Needed for 3D plotting


def load_trial(trial_dir):
    trial_dir = Path(trial_dir)
    csv_path = trial_dir / "telemetry.csv"

    if not csv_path.exists():
        raise FileNotFoundError(f"Missing telemetry.csv in {trial_dir}")

    df = pd.read_csv(csv_path)

    numeric_cols = [
        "time",
        "object_x", "object_y", "object_z",
        "base_x", "base_y", "base_yaw",
        "gripper_state",
        "joint_1", "joint_2", "joint_3", "joint_4",
        "joint_5", "joint_6", "joint_7",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["time"]).copy()
    df["time_zeroed"] = df["time"] - df["time"].iloc[0]

    return df


def plot_object_3d(df, trial_dir):
    required = ["object_x", "object_y", "object_z"]

    if not all(col in df.columns for col in required):
        print("Skipping object 3D plot: object columns missing.")
        return

    obj = df.dropna(subset=required)

    if len(obj) < 2:
        print("Skipping object 3D plot: not enough object data.")
        return

    x = obj["object_x"].to_numpy()
    y = obj["object_y"].to_numpy()
    z = obj["object_z"].to_numpy()

    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")

    ax.plot(x, y, z)
    ax.scatter(x[0], y[0], z[0], label="Start")
    ax.scatter(x[-1], y[-1], z[-1], label="End")

    ax.set_title("Object trajectory in 3D")
    ax.set_xlabel("Object X")
    ax.set_ylabel("Object Y")
    ax.set_zlabel("Object Z")
    ax.legend()

    output = Path(trial_dir) / "object_trajectory_3d.png"
    plt.savefig(output, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Saved {output}")


def plot_object_height(df, trial_dir):
    if "object_z" not in df.columns:
        print("Skipping object height plot: object_z missing.")
        return

    obj = df.dropna(subset=["object_z"])

    if len(obj) < 2:
        print("Skipping object height plot: not enough object_z data.")
        return

    t = obj["time_zeroed"].to_numpy()
    z = obj["object_z"].to_numpy()

    plt.figure()
    plt.plot(t, z)
    plt.title("Object height over time")
    plt.xlabel("Time within trial (s)")
    plt.ylabel("Object Z height")
    plt.grid(True)

    output = Path(trial_dir) / "object_height_over_time.png"
    plt.savefig(output, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Saved {output}")


def plot_object_xy(df, trial_dir):
    required = ["object_x", "object_y"]

    if not all(col in df.columns for col in required):
        print("Skipping object XY plot: object_x/object_y missing.")
        return

    obj = df.dropna(subset=required)

    if len(obj) < 2:
        print("Skipping object XY plot: not enough object data.")
        return

    x = obj["object_x"].to_numpy()
    y = obj["object_y"].to_numpy()

    plt.figure()
    plt.plot(x, y)
    plt.scatter(x[0], y[0], label="Start")
    plt.scatter(x[-1], y[-1], label="End")

    plt.title("Object path from start to shelf")
    plt.xlabel("Object X")
    plt.ylabel("Object Y")
    plt.axis("equal")
    plt.grid(True)
    plt.legend()

    output = Path(trial_dir) / "object_path_xy.png"
    plt.savefig(output, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Saved {output}")


def plot_base_path(df, trial_dir):
    required = ["base_x", "base_y"]

    if not all(col in df.columns for col in required):
        print("Skipping base path plot: base columns missing.")
        return

    base = df.dropna(subset=required)

    if len(base) < 2:
        print("Skipping base path plot: not enough base data.")
        return

    x = base["base_x"].to_numpy()
    y = base["base_y"].to_numpy()

    plt.figure()
    plt.plot(x, y)
    plt.scatter(x[0], y[0], label="Start")
    plt.scatter(x[-1], y[-1], label="End")

    plt.title("Robot base path")
    plt.xlabel("Base X")
    plt.ylabel("Base Y")
    plt.axis("equal")
    plt.grid(True)
    plt.legend()

    output = Path(trial_dir) / "base_path_xy.png"
    plt.savefig(output, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Saved {output}")


def plot_joints(df, trial_dir):
    joint_cols = [
        f"joint_{i}" for i in range(1, 8)
        if f"joint_{i}" in df.columns
    ]

    if not joint_cols:
        print("Skipping joint plot: no joint columns.")
        return

    plt.figure()

    t = df["time_zeroed"].to_numpy()

    for col in joint_cols:
        y = df[col].to_numpy()
        plt.plot(t, y, label=col)

    plt.title("Arm joint positions over time")
    plt.xlabel("Time within trial (s)")
    plt.ylabel("Joint position")
    plt.grid(True)
    plt.legend()

    output = Path(trial_dir) / "arm_joints_over_time.png"
    plt.savefig(output, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Saved {output}")


def plot_gripper(df, trial_dir):
    if "gripper_state" not in df.columns:
        print("Skipping gripper plot: gripper_state missing.")
        return

    grip = df.dropna(subset=["gripper_state"])

    if len(grip) < 2:
        print("Skipping gripper plot: not enough gripper data.")
        return

    t = grip["time_zeroed"].to_numpy()
    g = grip["gripper_state"].to_numpy()

    plt.figure()
    plt.plot(t, g)

    plt.title("Gripper opening over time")
    plt.xlabel("Time within trial (s)")
    plt.ylabel("Average finger joint position")
    plt.grid(True)

    output = Path(trial_dir) / "gripper_state_over_time.png"
    plt.savefig(output, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Saved {output}")


def plot_summary_object_and_gripper(df, trial_dir):
    required = ["object_z", "gripper_state"]

    if not all(col in df.columns for col in required):
        print("Skipping summary plot: object_z or gripper_state missing.")
        return

    clean = df.dropna(subset=["object_z", "gripper_state"])

    if len(clean) < 2:
        print("Skipping summary plot: not enough data.")
        return

    t = clean["time_zeroed"].to_numpy()
    z = clean["object_z"].to_numpy()
    g = clean["gripper_state"].to_numpy()

    fig, ax1 = plt.subplots()

    ax1.plot(t, z, label="Object height")
    ax1.set_xlabel("Time within trial (s)")
    ax1.set_ylabel("Object Z height")
    ax1.grid(True)

    ax2 = ax1.twinx()
    ax2.plot(t, g, linestyle="--", label="Gripper opening")
    ax2.set_ylabel("Gripper opening")

    plt.title("Object height and gripper state over time")

    output = Path(trial_dir) / "object_height_and_gripper.png"
    plt.savefig(output, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Saved {output}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python visualize_trial.py data/P001_VR_T01")
        sys.exit(1)

    trial_dir = Path(sys.argv[1])
    df = load_trial(trial_dir)

    plot_object_3d(df, trial_dir)
    plot_object_height(df, trial_dir)
    plot_object_xy(df, trial_dir)
    plot_base_path(df, trial_dir)
    plot_joints(df, trial_dir)
    plot_gripper(df, trial_dir)
    plot_summary_object_and_gripper(df, trial_dir)

    print("Done.")


if __name__ == "__main__":
    main()
