#!/usr/bin/env python3

import argparse
import csv
import math
from collections import deque
from pathlib import Path

import numpy as np
import rosbag
import yaml

from tf.transformations import (
    quaternion_from_matrix,
    quaternion_matrix,
)


ARM_JOINTS = [
    "arm_1_joint",
    "arm_2_joint",
    "arm_3_joint",
    "arm_4_joint",
    "arm_5_joint",
    "arm_6_joint",
    "arm_7_joint",
]

LEFT_GRIPPER = "gripper_left_finger_joint"
RIGHT_GRIPPER = "gripper_right_finger_joint"
TORSO_JOINT = "torso_lift_joint"

DEFAULT_BAG_NAMES = [
    "full_session_fixed.bag",
    "full_session.bag",
]

EE_FRAME_CANDIDATES = [
    "gripper_grasping_frame",
    "gripper_tool_link",
    "gripper_link",
    "wrist_ft_tool_link",
    "arm_tool_link",
    "arm_7_link",
]

ROOT_FRAME_CANDIDATES = [
    "odom",
    "base_footprint",
    "base_link",
]


def clean_frame(frame):
    if frame is None:
        return ""

    return frame.lstrip("/")


def find_bag(session_dir):
    session_dir = Path(session_dir)

    for name in DEFAULT_BAG_NAMES:
        candidate = session_dir / name

        if candidate.exists():
            return candidate

    bags = sorted(session_dir.glob("*.bag"))

    if bags:
        return bags[0]

    raise FileNotFoundError(
        f"No .bag file found in {session_dir}"
    )


def parse_bool(value):
    if isinstance(value, bool):
        return value

    if value is None:
        return False

    text = str(value).strip().lower()

    if text in ["true", "1", "yes", "y"]:
        return True

    if text in ["false", "0", "no", "n", ""]:
        return False

    return False


def load_events(events_path):
    events = {}

    with events_path.open("r") as f:
        reader = csv.DictReader(f)

        for row in reader:
            trial_id = row["trial_id"].strip()

            events[trial_id] = {
                "start": float(row["start_time"]),
                "end": float(row["end_time"]),

                "task_success": row.get(
                    "task_success",
                    "",
                ),

                "technician_intervention": row.get(
                    "technician_intervention",
                    "",
                ),

                "intervention_count": int(
                    row.get(
                        "intervention_count",
                        "0",
                    )
                    or 0
                ),

                "intervention_severity": row.get(
                    "intervention_severity",
                    "none",
                ),

                "notes": row.get(
                    "notes",
                    "",
                ),
            }

    return events


def normalize_events_to_bag_time(
    events,
    bag_start,
):
    normalized = {}

    for trial_id, interval in events.items():
        start = interval["start"]
        end = interval["end"]

        timestamps_are_absolute = (
            start >= bag_start - 1.0
        )

        if timestamps_are_absolute:
            rel_start = start - bag_start
            rel_end = end - bag_start
        else:
            rel_start = start
            rel_end = end

        normalized[trial_id] = {
            **interval,

            "original_start": start,
            "original_end": end,

            "start": rel_start,
            "end": rel_end,
        }

    return normalized


def get_joint_position(
    msg,
    joint_name,
):
    if joint_name not in msg.name:
        return None

    idx = msg.name.index(
        joint_name
    )

    if len(msg.position) <= idx:
        return None

    return msg.position[idx]


def get_joint_effort(
    msg,
    joint_name,
):
    if joint_name not in msg.name:
        return None

    idx = msg.name.index(
        joint_name
    )

    if len(msg.effort) <= idx:
        return None

    return msg.effort[idx]


def find_active_trial(
    rel_time,
    events,
):
    for trial_id, interval in events.items():

        if (
            interval["start"]
            <= rel_time
            <= interval["end"]
        ):
            return trial_id

    return None


def quaternion_to_yaw(q):
    x = q.x
    y = q.y
    z = q.z
    w = q.w

    siny_cosp = (
        2.0
        * (w * z + x * y)
    )

    cosy_cosp = (
        1.0
        - 2.0
        * (y * y + z * z)
    )

    return math.atan2(
        siny_cosp,
        cosy_cosp,
    )


# ============================================================
# TF HANDLING
# ============================================================

def transform_to_matrix(transform):
    q = [
        transform.rotation.x,
        transform.rotation.y,
        transform.rotation.z,
        transform.rotation.w,
    ]

    matrix = quaternion_matrix(q)

    matrix[0, 3] = transform.translation.x
    matrix[1, 3] = transform.translation.y
    matrix[2, 3] = transform.translation.z

    return matrix


class TFGraph:

    def __init__(self):
        self.transforms = {}

    def update_tf_message(self, msg):
        for stamped in msg.transforms:

            parent = clean_frame(
                stamped.header.frame_id
            )

            child = clean_frame(
                stamped.child_frame_id
            )

            if not parent or not child:
                continue

            matrix = transform_to_matrix(
                stamped.transform
            )

            self.transforms[
                (parent, child)
            ] = matrix

    def available_frames(self):
        frames = set()

        for parent, child in self.transforms:
            frames.add(parent)
            frames.add(child)

        return frames

    def lookup(self, root, target):
        root = clean_frame(root)
        target = clean_frame(target)

        if root == target:
            return np.eye(4)

        adjacency = {}

        for (
            parent,
            child,
        ), matrix in self.transforms.items():

            adjacency.setdefault(
                parent,
                []
            ).append(
                (
                    child,
                    matrix,
                )
            )

            try:
                inverse = np.linalg.inv(
                    matrix
                )

            except np.linalg.LinAlgError:
                continue

            adjacency.setdefault(
                child,
                []
            ).append(
                (
                    parent,
                    inverse,
                )
            )

        if root not in adjacency:
            return None

        queue = deque()

        queue.append(
            (
                root,
                np.eye(4),
            )
        )

        visited = {
            root
        }

        while queue:

            frame, root_to_frame = (
                queue.popleft()
            )

            if frame == target:
                return root_to_frame

            for (
                neighbor,
                frame_to_neighbor,
            ) in adjacency.get(
                frame,
                [],
            ):

                if neighbor in visited:
                    continue

                visited.add(
                    neighbor
                )

                root_to_neighbor = (
                    root_to_frame
                    @ frame_to_neighbor
                )

                queue.append(
                    (
                        neighbor,
                        root_to_neighbor,
                    )
                )

        return None


def find_ee_transform(tf_graph):
    available = (
        tf_graph.available_frames()
    )

    for root in ROOT_FRAME_CANDIDATES:

        if root not in available:
            continue

        for ee_frame in EE_FRAME_CANDIDATES:

            if ee_frame not in available:
                continue

            matrix = tf_graph.lookup(
                root,
                ee_frame,
            )

            if matrix is not None:
                return (
                    matrix,
                    root,
                    ee_frame,
                )

    return (
        None,
        None,
        None,
    )


def matrix_to_pose(matrix):
    position = matrix[
        0:3,
        3
    ]

    quaternion = (
        quaternion_from_matrix(
            matrix
        )
    )

    return {
        "ee_x": float(position[0]),
        "ee_y": float(position[1]),
        "ee_z": float(position[2]),

        "quat_x": float(quaternion[0]),
        "quat_y": float(quaternion[1]),
        "quat_z": float(quaternion[2]),
        "quat_w": float(quaternion[3]),
    }


# ============================================================
# OUTPUT / METADATA
# ============================================================

def make_trial_outputs(
    participant,
    condition,
    events,
):
    outputs = {}

    for trial_id in events.keys():

        trial_dir = (
            Path("data")
            / f"{participant}_{condition}_{trial_id}"
        )

        trial_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        outputs[trial_id] = {
            "dir": trial_dir,

            "telemetry": (
                trial_dir
                / "telemetry.csv"
            ),

            "metadata": (
                trial_dir
                / "metadata.yaml"
            ),
        }

    return outputs


def load_existing_metadata(path):
    if not path.exists():
        return {}

    try:
        with path.open("r") as f:
            data = yaml.safe_load(f)

        if isinstance(data, dict):
            return data

    except Exception:
        pass

    return {}


def write_metadata(
    metadata_path,
    participant,
    condition,
    trial_id,
    event,
    session_dir,
    bag_path,
):
    existing = load_existing_metadata(
        metadata_path
    )

    task_success = parse_bool(
        event.get(
            "task_success",
            False,
        )
    )

    technician_intervention = parse_bool(
        event.get(
            "technician_intervention",
            False,
        )
    )

    # --------------------------------------------------------
    # Intervention count
    # --------------------------------------------------------

    intervention_count = int(
        event.get(
            "intervention_count",
            0,
        )
        or 0
    )

    intervention_severity = (
        str(
            event.get(
                "intervention_severity",
                "none",
            )
        )
        .strip()
        .lower()
    )

    notes = str(
        event.get(
            "notes",
            "",
        )
    ).strip()

    metadata = {
        "participant_id": participant,
        "condition": condition,
        "trial_id": trial_id,

        "training_group": "standard",

        "task_name": (
            "table_to_shelf_pick_place"
        ),

        "task_success": (
            task_success
        ),

        "technician_intervention": (
            technician_intervention
        ),

        # This was previously missing.
        "intervention_count": (
            intervention_count
        ),

        "intervention_severity": (
            intervention_severity
        ),

        "notes": notes,

        "session": {
            "rosbag": str(
                bag_path
            ),

            "events_csv": str(
                session_dir
                / "events.csv"
            ),

            "trial_start_time": (
                event.get(
                    "original_start"
                )
            ),

            "trial_end_time": (
                event.get(
                    "original_end"
                )
            ),

            "relative_start_time": (
                event.get(
                    "start"
                )
            ),

            "relative_end_time": (
                event.get(
                    "end"
                )
            ),

            "duration_seconds": (
                event.get(
                    "end",
                    0,
                )
                -
                event.get(
                    "start",
                    0,
                )
            ),
        },

        "manual_validation": (
            existing.get(
                "manual_validation",
                {
                    "object_picked": None,
                    "object_placed_on_shelf": None,
                    "object_dropped": None,
                    "unsafe_robot_motion": None,
                    "reset_required": None,
                    "researcher_helped_task": None,
                },
            )
        ),

        "video_validation": (
            existing.get(
                "video_validation",
                {
                    "video_covers_full_trial": None,
                    "camera_freeze_or_dropout": None,
                },
            )
        ),
    }

    with metadata_path.open(
        "w"
    ) as f:

        yaml.safe_dump(
            metadata,
            f,
            sort_keys=False,
            default_flow_style=False,
        )


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--session",
        required=True,
        help=(
            "Session folder, "
            "e.g. data/P03_2D"
        ),
    )

    parser.add_argument(
        "--participant",
        required=True,
        help=(
            "Participant ID, "
            "e.g. P03"
        ),
    )

    parser.add_argument(
        "--condition",
        required=True,
        choices=[
            "VR",
            "2D",
            "REAL",
        ],
    )

    args = parser.parse_args()

    session_dir = Path(
        args.session
    )

    events_path = (
        session_dir
        / "events.csv"
    )

    bag_path = find_bag(
        session_dir
    )

    if not events_path.exists():
        raise FileNotFoundError(
            f"Missing events.csv "
            f"in {session_dir}"
        )

    raw_events = load_events(
        events_path
    )

    bag = rosbag.Bag(
        str(bag_path)
    )

    bag_start = (
        bag.get_start_time()
    )

    bag_end = (
        bag.get_end_time()
    )

    bag_duration = (
        bag_end
        - bag_start
    )

    events = (
        normalize_events_to_bag_time(
            raw_events,
            bag_start,
        )
    )

    trial_outputs = (
        make_trial_outputs(
            args.participant,
            args.condition,
            events,
        )
    )

    rows_by_trial = {
        trial_id: []
        for trial_id
        in events.keys()
    }

    latest_base = {
        "base_x": "",
        "base_y": "",
        "base_yaw": "",
    }

    latest_object = {
        "object_x": "",
        "object_y": "",
        "object_z": "",
    }

    latest_robot_marker = {
        "robot_marker_x": "",
        "robot_marker_y": "",
        "robot_marker_z": "",
    }

    tf_graph = TFGraph()

    # --------------------------------------------------------
    # Load /tf_static first
    # --------------------------------------------------------

    static_count = 0

    for _, msg, _ in bag.read_messages(
        topics=[
            "/tf_static"
        ]
    ):
        tf_graph.update_tf_message(
            msg
        )

        static_count += len(
            msg.transforms
        )

    # --------------------------------------------------------
    # Fallback static TF snapshot for older bags
    # --------------------------------------------------------

    if static_count == 0:

        fallback_static_bag = Path(
            "tiago_tf_static.bag"
        )

        if fallback_static_bag.exists():

            print(
                "No /tf_static found in session bag."
            )

            print(
                f"Loading static TF fallback: "
                f"{fallback_static_bag}"
            )

            with rosbag.Bag(
                str(fallback_static_bag),
                "r",
            ) as static_bag:

                for _, msg, _ in static_bag.read_messages(
                    topics=[
                        "/tf_static"
                    ]
                ):

                    tf_graph.update_tf_message(
                        msg
                    )

                    static_count += len(
                        msg.transforms
                    )

            print(
                f"Loaded {static_count} fallback "
                f"static TF transforms."
            )

        else:

            print(
                "WARNING: Session contains no /tf_static "
                "and no tiago_tf_static.bag fallback exists."
            )

    print(
        f"Reading bag: {bag_path}"
    )

    print(
        f"Bag start time: "
        f"{bag_start}"
    )

    print(
        f"Bag duration: "
        f"{bag_duration:.2f}s"
    )

    print(
        f"Loaded "
        f"{static_count} "
        f"static TF transforms."
    )

    print("")
    print(
        "Normalized trial windows:"
    )

    for (
        trial_id,
        interval,
    ) in events.items():

        print(
            f"  {trial_id}: "
            f"{interval['start']:.2f}s "
            f"-> "
            f"{interval['end']:.2f}s "
            f"("
            f"{interval['end'] - interval['start']:.2f}s"
            f")"
        )

    topics = [
        "/joint_states",

        "/mobile_base_controller/odom",

        "/natnet_ros/umh_object_mahika/pose",

        "/natnet_ros/umh_tiago_base/pose",

        "/tf",
    ]

    detected_root = None
    detected_ee = None

    ee_success_count = 0
    ee_failure_count = 0

    # --------------------------------------------------------
    # Main chronological bag pass
    # --------------------------------------------------------

    for topic, msg, t in bag.read_messages(
        topics=topics
    ):

        current_time = (
            t.to_sec()
        )

        rel_time = (
            current_time
            - bag_start
        )

        # Dynamic TF
        if topic == "/tf":

            tf_graph.update_tf_message(
                msg
            )

            continue

        # Base odometry
        if (
            topic
            == "/mobile_base_controller/odom"
        ):

            latest_base[
                "base_x"
            ] = (
                msg.pose.pose.position.x
            )

            latest_base[
                "base_y"
            ] = (
                msg.pose.pose.position.y
            )

            latest_base[
                "base_yaw"
            ] = (
                quaternion_to_yaw(
                    msg.pose.pose.orientation
                )
            )

            continue

        # Object OptiTrack
        if (
            topic
            == "/natnet_ros/umh_object_mahika/pose"
        ):

            latest_object[
                "object_x"
            ] = (
                msg.pose.position.x
            )

            latest_object[
                "object_y"
            ] = (
                msg.pose.position.y
            )

            latest_object[
                "object_z"
            ] = (
                msg.pose.position.z
            )

            continue

        # TIAGo OptiTrack
        if (
            topic
            == "/natnet_ros/umh_tiago_base/pose"
        ):

            latest_robot_marker[
                "robot_marker_x"
            ] = (
                msg.pose.position.x
            )

            latest_robot_marker[
                "robot_marker_y"
            ] = (
                msg.pose.position.y
            )

            latest_robot_marker[
                "robot_marker_z"
            ] = (
                msg.pose.position.z
            )

            continue

        # Joint states = telemetry sampling clock
        if topic != "/joint_states":
            continue

        active_trial = (
            find_active_trial(
                rel_time,
                events,
            )
        )

        if active_trial is None:
            continue

        arm_positions = []
        arm_efforts = []

        for joint in ARM_JOINTS:

            arm_positions.append(
                get_joint_position(
                    msg,
                    joint,
                )
            )

            arm_efforts.append(
                get_joint_effort(
                    msg,
                    joint,
                )
            )

        if any(
            value is None
            for value
            in arm_positions
        ):
            continue

        left_grip = (
            get_joint_position(
                msg,
                LEFT_GRIPPER,
            )
        )

        right_grip = (
            get_joint_position(
                msg,
                RIGHT_GRIPPER,
            )
        )

        if (
            left_grip is not None
            and right_grip is not None
        ):

            gripper_state = (
                left_grip
                + right_grip
            ) / 2.0

        else:
            gripper_state = ""

        torso = (
            get_joint_position(
                msg,
                TORSO_JOINT,
            )
        )

        if torso is None:
            torso = ""

        # End-effector pose from TF
        ee_matrix = None

        if (
            detected_root is not None
            and detected_ee is not None
        ):

            ee_matrix = (
                tf_graph.lookup(
                    detected_root,
                    detected_ee,
                )
            )

        if ee_matrix is None:

            (
                ee_matrix,
                root_candidate,
                ee_candidate,
            ) = find_ee_transform(
                tf_graph
            )

            if ee_matrix is not None:

                if detected_root is None:

                    detected_root = (
                        root_candidate
                    )

                    detected_ee = (
                        ee_candidate
                    )

                    print("")
                    print(
                        "Detected EE TF chain:"
                    )

                    print(
                        f"  root frame: "
                        f"{detected_root}"
                    )

                    print(
                        f"  EE frame: "
                        f"{detected_ee}"
                    )

        if ee_matrix is not None:

            ee_pose = (
                matrix_to_pose(
                    ee_matrix
                )
            )

            ee_success_count += 1

        else:

            ee_pose = {
                "ee_x": "",
                "ee_y": "",
                "ee_z": "",
                "quat_x": "",
                "quat_y": "",
                "quat_z": "",
                "quat_w": "",
            }

            ee_failure_count += 1

        row = {
            "time": rel_time,

            "ee_x": ee_pose["ee_x"],
            "ee_y": ee_pose["ee_y"],
            "ee_z": ee_pose["ee_z"],

            "quat_x": ee_pose["quat_x"],
            "quat_y": ee_pose["quat_y"],
            "quat_z": ee_pose["quat_z"],
            "quat_w": ee_pose["quat_w"],

            "gripper_state": gripper_state,

            "torso_lift_joint": torso,

            "base_x": latest_base[
                "base_x"
            ],

            "base_y": latest_base[
                "base_y"
            ],

            "base_yaw": latest_base[
                "base_yaw"
            ],

            "object_x": latest_object[
                "object_x"
            ],

            "object_y": latest_object[
                "object_y"
            ],

            "object_z": latest_object[
                "object_z"
            ],

            "robot_marker_x": latest_robot_marker[
                "robot_marker_x"
            ],

            "robot_marker_y": latest_robot_marker[
                "robot_marker_y"
            ],

            "robot_marker_z": latest_robot_marker[
                "robot_marker_z"
            ],
        }

        for i, value in enumerate(
            arm_positions,
            start=1,
        ):

            row[
                f"joint_{i}"
            ] = value

        for i, value in enumerate(
            arm_efforts,
            start=1,
        ):

            row[
                f"effort_{i}"
            ] = (
                ""
                if value is None
                else value
            )

        rows_by_trial[
            active_trial
        ].append(
            row
        )

    bag.close()

    fieldnames = [
        "time",

        "ee_x",
        "ee_y",
        "ee_z",

        "quat_x",
        "quat_y",
        "quat_z",
        "quat_w",

        "joint_1",
        "joint_2",
        "joint_3",
        "joint_4",
        "joint_5",
        "joint_6",
        "joint_7",

        "effort_1",
        "effort_2",
        "effort_3",
        "effort_4",
        "effort_5",
        "effort_6",
        "effort_7",

        "gripper_state",
        "torso_lift_joint",

        "base_x",
        "base_y",
        "base_yaw",

        "object_x",
        "object_y",
        "object_z",

        "robot_marker_x",
        "robot_marker_y",
        "robot_marker_z",
    ]

    print("")

    for (
        trial_id,
        rows,
    ) in rows_by_trial.items():

        telemetry_path = (
            trial_outputs[
                trial_id
            ]["telemetry"]
        )

        metadata_path = (
            trial_outputs[
                trial_id
            ]["metadata"]
        )

        with telemetry_path.open(
            "w",
            newline="",
        ) as f:

            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames,
            )

            writer.writeheader()

            writer.writerows(
                rows
            )

        write_metadata(
            metadata_path=metadata_path,

            participant=(
                args.participant
            ),

            condition=(
                args.condition
            ),

            trial_id=(
                trial_id
            ),

            event=(
                events[
                    trial_id
                ]
            ),

            session_dir=(
                session_dir
            ),

            bag_path=(
                bag_path
            ),
        )

        print(
            f"Saved "
            f"{len(rows)} rows "
            f"to {telemetry_path}"
        )

        print(
            f"Saved metadata to "
            f"{metadata_path}"
        )

    print("")
    print(
        "TF / end-effector extraction summary:"
    )

    print(
        f"  successful EE samples: "
        f"{ee_success_count}"
    )

    print(
        f"  missing EE samples: "
        f"{ee_failure_count}"
    )

    if detected_root is not None:

        print(
            f"  root frame: "
            f"{detected_root}"
        )

        print(
            f"  end-effector frame: "
            f"{detected_ee}"
        )

    else:

        print(
            "  WARNING: No usable "
            "end-effector TF chain was found."
        )

        print(
            "  Available candidate frames "
            "may need to be checked."
        )

    print("")
    print("Done.")


if __name__ == "__main__":
    main()