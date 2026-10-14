#!/usr/bin/env python3

import rosbag

BAG = "data/P02_REAL/full_session.bag"

bag = rosbag.Bag(BAG)
start = bag.get_start_time()

last_vals = None

print("time      left_finger      right_finger      delta")
print("=" * 65)

for topic, msg, t in bag.read_messages(topics=["/joint_states"]):

    names = msg.name

    gripper_indices = [
        i for i, name in enumerate(names)
        if "gripper" in name and "finger" in name
    ]

    if len(gripper_indices) < 2:
        continue

    vals = [msg.position[i] for i in gripper_indices[:2]]

    if last_vals is None:
        last_vals = vals
        continue

    delta = sum(abs(a - b) for a, b in zip(vals, last_vals))

    # Very sensitive threshold
    if delta > 1e-5:

        rel = t.to_sec() - start

        m = int(rel // 60)
        s = rel % 60

        print(
            f"{m:02d}:{s:05.2f}   "
            f"{vals[0]:.8f}   "
            f"{vals[1]:.8f}   "
            f"{delta:.8f}"
        )

    last_vals = vals

bag.close()