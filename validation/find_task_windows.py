#!/usr/bin/env python3

import rosbag
import numpy as np
from collections import defaultdict

BAG = "data/P02_REAL/full_session.bag"
BIN_SIZE = 1.0

ARM_JOINTS = [
    "arm_1_joint",
    "arm_2_joint",
    "arm_3_joint",
    "arm_4_joint",
    "arm_5_joint",
    "arm_6_joint",
    "arm_7_joint",
]

arm_bins = defaultdict(list)
gripper_bins = defaultdict(list)
base_bins = defaultdict(list)

bag = rosbag.Bag(BAG)
bag_start = bag.get_start_time()
bag_end = bag.get_end_time()

for topic, msg, t in bag.read_messages(
    topics=[
        "/joint_states",
        "/mobile_base_controller/odom",
    ]
):
    rel = t.to_sec() - bag_start
    b = int(rel // BIN_SIZE)

    if topic == "/joint_states":

        if all(j in msg.name for j in ARM_JOINTS):
            vals = []
            for j in ARM_JOINTS:
                idx = msg.name.index(j)
                vals.append(msg.position[idx])
            arm_bins[b].append(vals)

        grip = []
        for name, pos in zip(msg.name, msg.position):
            if "gripper" in name and "finger" in name:
                grip.append(pos)

        if grip:
            gripper_bins[b].append(grip)

    elif topic == "/mobile_base_controller/odom":
        base_bins[b].append([
            msg.pose.pose.position.x,
            msg.pose.pose.position.y
        ])

bag.close()


def movement(samples):
    if len(samples) < 2:
        return 0.0

    arr = np.asarray(samples)

    try:
        return float(np.sum(np.ptp(arr, axis=0)))
    except Exception:
        return 0.0


# Thresholds for actual movement
ARM_THRESHOLD = 0.004
GRIPPER_THRESHOLD = 0.001
BASE_THRESHOLD = 0.005

max_bin = int((bag_end - bag_start) // BIN_SIZE)

activity = []

for b in range(max_bin + 1):

    arm = movement(arm_bins[b])
    grip = movement(gripper_bins[b])
    base = movement(base_bins[b])

    active = (
        arm > ARM_THRESHOLD
        or grip > GRIPPER_THRESHOLD
        or base > BASE_THRESHOLD
    )

    activity.append((b, active, arm, grip, base))


def fmt(seconds):
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


print("\nDETAILED ACTIVITY")
print("=" * 72)

for b, active, arm, grip, base in activity:

    if active:
        print(
            f"{fmt(b)}   "
            f"arm={arm:.4f}   "
            f"gripper={grip:.4f}   "
            f"base={base:.4f}"
        )


# Merge activity separated by short pauses.
MAX_GAP = 8      # seconds
active_bins = [b for b, active, _, _, _ in activity if active]

print("\n\nCONTINUOUS ACTIVITY CLUSTERS")
print("=" * 72)

if active_bins:

    clusters = []

    start = active_bins[0]
    previous = active_bins[0]

    for b in active_bins[1:]:

        if b - previous <= MAX_GAP:
            previous = b

        else:
            clusters.append((start, previous + 1))
            start = b
            previous = b

    clusters.append((start, previous + 1))

    for i, (start, end) in enumerate(clusters, 1):
        print(
            f"Cluster {i}: "
            f"{fmt(start)} -> {fmt(end)} "
            f"({end-start:.0f}s)"
        )