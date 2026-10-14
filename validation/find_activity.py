#!/usr/bin/env python3

import rosbag
import numpy as np
from collections import defaultdict

BAG = "data/P02_REAL/full_session.bag"
BIN_SIZE = 5.0

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

topics = [
    "/joint_states",
    "/mobile_base_controller/odom",
]

for topic, msg, t in bag.read_messages(topics=topics):

    rel = t.to_sec() - bag_start
    b = int(rel // BIN_SIZE)

    if topic == "/joint_states":

        # Arm
        if all(j in msg.name for j in ARM_JOINTS):
            values = []
            for joint in ARM_JOINTS:
                idx = msg.name.index(joint)
                values.append(msg.position[idx])

            arm_bins[b].append(values)

        # Gripper
        gripper_values = []

        for name, pos in zip(msg.name, msg.position):
            if "gripper" in name and "finger" in name:
                gripper_values.append(pos)

        if gripper_values:
            gripper_bins[b].append(gripper_values)

    elif topic == "/mobile_base_controller/odom":

        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y
        base_bins[b].append([x, y])

bag.close()


def total_range(samples):
    if len(samples) < 2:
        return 0.0

    arr = np.array(samples)

    try:
        return float(np.sum(np.ptp(arr, axis=0)))
    except Exception:
        return 0.0


print("")
print("ROBOT ACTIVITY WINDOWS")
print("=" * 75)
print("time          arm_range    gripper_range    base_range")
print("-" * 75)

all_bins = sorted(
    set(arm_bins.keys())
    | set(gripper_bins.keys())
    | set(base_bins.keys())
)

for b in all_bins:

    arm = total_range(arm_bins[b])
    grip = total_range(gripper_bins[b])
    base = total_range(base_bins[b])

    # Show anything with meaningful movement in any subsystem
    if arm > 0.01 or grip > 0.002 or base > 0.01:

        start = b * BIN_SIZE
        end = start + BIN_SIZE

        sm = int(start // 60)
        ss = int(start % 60)

        em = int(end // 60)
        es = int(end % 60)

        print(
            f"{sm:02d}:{ss:02d}-{em:02d}:{es:02d}    "
            f"{arm:10.4f}    "
            f"{grip:13.4f}    "
            f"{base:10.4f}"
        )