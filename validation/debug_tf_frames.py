#!/usr/bin/env python3

import rosbag
from collections import Counter

BAG_PATH = "data/P001_VR_trial/full_session_fixed.bag"

parents = Counter()
children = Counter()
pairs = Counter()

bag = rosbag.Bag(BAG_PATH)

for topic, msg, t in bag.read_messages(topics=["/tf"]):
    for tr in msg.transforms:
        parent = tr.header.frame_id
        child = tr.child_frame_id

        parents[parent] += 1
        children[child] += 1
        pairs[(parent, child)] += 1

bag.close()

print("\nTop parent frames:")
for frame, count in parents.most_common(30):
    print(frame, count)

print("\nTop child frames:")
for frame, count in children.most_common(50):
    print(frame, count)

print("\nPairs containing gripper/arm/tool:")
for (parent, child), count in pairs.items():
    text = parent + " -> " + child
    if "gripper" in text or "arm" in text or "tool" in text:
        print(text, count)
