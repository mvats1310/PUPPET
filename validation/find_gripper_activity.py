#!/usr/bin/env python3

import rosbag
import numpy as np
from collections import defaultdict

BAG = "data/P02_REAL/full_session.bag"
BIN_SIZE = 2.0

bins = defaultdict(list)

bag = rosbag.Bag(BAG)
start = bag.get_start_time()

for topic, msg, t in bag.read_messages(topics=["/joint_states"]):

    rel = t.to_sec() - start
    b = int(rel // BIN_SIZE)

    vals = []

    for name, pos in zip(msg.name, msg.position):
        if "gripper" in name and "finger" in name:
            vals.append(pos)

    if vals:
        bins[b].append(vals)

bag.close()

print("GRIPPER ACTIVITY")
print("=" * 50)

for b in sorted(bins):

    samples = np.array(bins[b])

    if len(samples) < 2:
        continue

    movement = float(np.sum(np.ptp(samples, axis=0)))

    # Show even fairly small actual gripper movements
    if movement > 0.001:

        s = b * BIN_SIZE
        e = s + BIN_SIZE

        print(
            f"{int(s//60):02d}:{int(s%60):02d} - "
            f"{int(e//60):02d}:{int(e%60):02d}   "
            f"range={movement:.5f}"
        )