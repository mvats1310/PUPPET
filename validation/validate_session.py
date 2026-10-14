#!/usr/bin/env python3

import argparse
import csv
import json
from pathlib import Path

import rosbag


REQUIRED_TOPICS_COMMON = [
    "/joint_states",
    "/tf",
    "/tf_static",
    "/mobile_base_controller/cmd_vel",
    "/mobile_base_controller/odom",
    "/natnet_ros/umh_tiago_base/pose",
    "/natnet_ros/umh_object_mahika/pose",
    "/xtion/rgb/image_raw/compressed",
]

OPTIONAL_TOPICS = [
    "/xtion/rgb/camera_info",
    "/xtion/depth_registered/image_raw/compressedDepth",
    "/xtion/depth_registered/camera_info",
]
REQUIRED_TRIALS = [
    "T01",
    "T02",
    "T03",
]

CONDITION_VIDEO_REQUIREMENTS = {
    "VR": [
        "external_camera",
        "vr_pov",
    ],
    "2D": [
        "camera_1_side",
        "camera_2_top",
        "camera_3_shelf",
    ],
    "REAL": [
        "external_camera",
    ],
}


def save_json(data, path):
    path = Path(path)

    with path.open("w") as f:
        json.dump(
            data,
            f,
            indent=2,
        )


def find_bag(session_dir):
    session_dir = Path(session_dir)

    preferred_names = [
        "full_session_fixed.bag",
        "full_session.bag",
    ]

    for name in preferred_names:
        candidate = (
            session_dir
            / name
        )

        if candidate.exists():
            return candidate

    bags = sorted(
        session_dir.glob("*.bag")
    )

    if len(bags) > 0:
        return bags[0]

    return None


def inspect_bag(bag_path):
    info = {
        "bag_path": str(
            bag_path
        ),
        "exists": bag_path.exists(),
        "duration_seconds": None,
        "start_time": None,
        "end_time": None,
        "size_mb": None,
        "topics": {},
        "total_messages": 0,
    }

    if not bag_path.exists():
        return info

    info["size_mb"] = (
        bag_path.stat().st_size
        / (1024 * 1024)
    )

    bag = rosbag.Bag(
        str(bag_path)
    )

    info["start_time"] = (
        bag.get_start_time()
    )

    info["end_time"] = (
        bag.get_end_time()
    )

    info["duration_seconds"] = (
        info["end_time"]
        - info["start_time"]
    )

    topic_info = (
        bag
        .get_type_and_topic_info()
        .topics
    )

    for (
        topic_name,
        topic_data,
    ) in topic_info.items():

        info[
            "topics"
        ][
            topic_name
        ] = {
            "message_type": (
                topic_data.msg_type
            ),
            "message_count": (
                topic_data.message_count
            ),
            "frequency": (
                topic_data.frequency
            ),
        }

        info[
            "total_messages"
        ] += (
            topic_data.message_count
        )

    bag.close()

    return info


# ============================================================
# TOPIC VALIDATION
# ============================================================

def validate_topics(
    bag_info,
):
    present_topics = set(
        bag_info
        .get(
            "topics",
            {},
        )
        .keys()
    )

    results = []
    issues = []
    review_reasons = []

    for topic in REQUIRED_TOPICS_COMMON:

        exists = (
            topic
            in present_topics
        )

        count = (
            bag_info
            .get(
                "topics",
                {},
            )
            .get(
                topic,
                {},
            )
            .get(
                "message_count",
                0,
            )
        )

        if (
            exists
            and count > 0
        ):
            status = "pass"

        else:

            if topic == "/tf_static":

                status = "review"

                review_reasons.append(
                    "Missing /tf_static; "
                    "end-effector Cartesian pose extraction "
                    "may be incomplete."
                )

            else:

                status = "fail"

                issues.append(
                    f"Missing required ROS topic: "
                    f"{topic}"
                )

        results.append({
            "topic": topic,
            "required": True,
            "exists": exists,
            "message_count": count,
            "status": status,
        })

    for topic in OPTIONAL_TOPICS:

        exists = (
            topic
            in present_topics
        )

        count = (
            bag_info
            .get(
                "topics",
                {},
            )
            .get(
                topic,
                {},
            )
            .get(
                "message_count",
                0,
            )
        )

        results.append({
            "topic": topic,
            "required": False,
            "exists": exists,
            "message_count": count,
            "status": (
                "pass"
                if (
                    exists
                    and count > 0
                )
                else "missing_optional"
            ),
        })

    return (
        results,
        issues,
        review_reasons,
    )


# ============================================================
# EVENTS
# ============================================================

def load_events(
    events_path,
):
    rows = []

    with events_path.open(
        "r"
    ) as f:

        reader = csv.DictReader(
            f
        )

        for row in reader:
            rows.append(
                row
            )

    return rows


def validate_events(
    session_dir,
    bag_info,
):
    events_path = (
        Path(
            session_dir
        )
        / "events.csv"
    )

    result = {
        "events_path": str(
            events_path
        ),
        "exists": (
            events_path.exists()
        ),
        "status": "pass",
        "trials": [],
        "issues": [],
        "review_reasons": [],
        "informational_notes": [],
    }

    if not events_path.exists():

        result[
            "status"
        ] = "fail"

        result[
            "issues"
        ].append(
            "Missing events.csv."
        )

        return result

    rows = load_events(
        events_path
    )

    if len(
        rows
    ) == 0:

        result[
            "status"
        ] = "fail"

        result[
            "issues"
        ].append(
            "events.csv is empty."
        )

        return result

    required_columns = [
        "trial_id",
        "start_time",
        "end_time",
        "task_success",
        "technician_intervention",
        "intervention_severity",
        "intervention_count",
        "notes",
    ]

    for col in required_columns:

        if col not in rows[0]:

            result[
                "status"
            ] = "fail"

            result[
                "issues"
            ].append(
                f"Missing column in "
                f"events.csv: {col}"
            )

    if (
        result[
            "status"
        ]
        == "fail"
    ):
        return result

    bag_start = (
        bag_info.get(
            "start_time"
        )
    )

    bag_end = (
        bag_info.get(
            "end_time"
        )
    )

    bag_duration = (
        bag_info.get(
            "duration_seconds"
        )
    )

    intervals = []

    for row in rows:

        trial_id = (
            row[
                "trial_id"
            ]
            .strip()
        )

        try:

            start_time = float(
                row[
                    "start_time"
                ]
            )

            end_time = float(
                row[
                    "end_time"
                ]
            )

        except Exception:

            result[
                "issues"
            ].append(
                f"{trial_id}: "
                "start_time/end_time are not numeric."
            )

            continue

        duration = (
            end_time
            - start_time
        )

        trial_status = "pass"

        trial_issues = []
        trial_reviews = []
        trial_info = []

        timestamps_are_absolute = (
            bag_start is not None
            and start_time
            >= bag_start - 1.0
        )

        # ----------------------------------------------------
        # Trial time checks
        # ----------------------------------------------------

        if (
            end_time
            <= start_time
        ):

            trial_status = "fail"

            trial_issues.append(
                "end_time must be greater "
                "than start_time."
            )

        if timestamps_are_absolute:

            if (
                bag_start is not None
                and start_time
                < bag_start - 1.0
            ):

                trial_status = "fail"

                trial_issues.append(
                    "start_time is before "
                    "the beginning of the bag."
                )

            if (
                bag_end is not None
                and end_time
                > bag_end + 1.0
            ):

                trial_status = "fail"

                trial_issues.append(
                    "end_time is beyond "
                    "the end of the bag."
                )

            relative_start = (
                start_time
                - bag_start
                if bag_start is not None
                else None
            )

            relative_end = (
                end_time
                - bag_start
                if bag_start is not None
                else None
            )

        else:

            relative_start = (
                start_time
            )

            relative_end = (
                end_time
            )

            if start_time < 0:

                trial_status = "fail"

                trial_issues.append(
                    "start_time is below 0."
                )

            if (
                bag_duration is not None
                and end_time
                > bag_duration + 1.0
            ):

                trial_status = "fail"

                trial_issues.append(
                    "end_time is beyond "
                    "bag duration."
                )

        if duration < 3:

            if (
                trial_status
                != "fail"
            ):
                trial_status = "review"

            trial_reviews.append(
                "Trial duration is very short."
            )

        # ----------------------------------------------------
        # Task result
        # ----------------------------------------------------

        task_success = (
            row[
                "task_success"
            ]
            .strip()
            .lower()
        )

        if task_success not in [
            "true",
            "false",
        ]:

            if (
                trial_status
                != "fail"
            ):
                trial_status = "review"

            trial_reviews.append(
                "task_success is not "
                "a valid true/false value."
            )

        # ----------------------------------------------------
        # Intervention parsing
        # ----------------------------------------------------

        technician_intervention = (
            row[
                "technician_intervention"
            ]
            .strip()
            .lower()
        )

        intervention_severity = (
            row[
                "intervention_severity"
            ]
            .strip()
            .lower()
        )

        try:

            intervention_count = int(
                row[
                    "intervention_count"
                ]
            )

        except (
            TypeError,
            ValueError,
        ):

            intervention_count = -1

            if (
                trial_status
                != "fail"
            ):
                trial_status = "review"

            trial_reviews.append(
                "intervention_count is not "
                "a valid integer."
            )

        if technician_intervention not in [
            "true",
            "false",
        ]:

            if (
                trial_status
                != "fail"
            ):
                trial_status = "review"

            trial_reviews.append(
                "technician_intervention "
                "is not a valid true/false value."
            )

        valid_severities = [
            "none",
            "minor",
            "major",
        ]

        if intervention_severity not in (
            valid_severities
        ):

            if (
                trial_status
                != "fail"
            ):
                trial_status = "review"

            trial_reviews.append(
                "intervention_severity must "
                "be none, minor, or major."
            )

        # ====================================================
        # INTERVENTION POLICY
        # ====================================================
        #
        # 0 interventions
        #     -> PASS
        #
        # 1-2 minor interventions
        #     -> PASS
        #     -> informational note retained
        #
        # >2 minor interventions
        #     -> REVIEW
        #
        # major intervention
        #     -> REVIEW
        #
        # Examples of major:
        #     - emergency stop
        #     - experiment stopped
        #     - substantial technician guidance
        #     - major robot/object readjustment
        #     - trial restart
        #
        # Missing/corrupt experimental data is handled
        # separately as FAIL.
        # ====================================================

        if (
            technician_intervention
            == "false"
        ):

            if (
                intervention_severity
                != "none"
            ):

                if (
                    trial_status
                    != "fail"
                ):
                    trial_status = "review"

                trial_reviews.append(
                    "technician_intervention=false "
                    "but intervention_severity "
                    "is not 'none'."
                )

            elif (
                intervention_count
                != 0
            ):

                if (
                    trial_status
                    != "fail"
                ):
                    trial_status = "review"

                trial_reviews.append(
                    "technician_intervention=false "
                    f"but intervention_count="
                    f"{intervention_count}."
                )

            else:

                trial_info.append(
                    "No technician/researcher "
                    "intervention recorded."
                )

        elif (
            technician_intervention
            == "true"
        ):

            if (
                intervention_count
                <= 0
            ):

                if (
                    trial_status
                    != "fail"
                ):
                    trial_status = "review"

                trial_reviews.append(
                    "technician_intervention=true "
                    "but intervention_count is not "
                    "greater than zero."
                )

            elif (
                intervention_severity
                == "none"
            ):

                if (
                    trial_status
                    != "fail"
                ):
                    trial_status = "review"

                trial_reviews.append(
                    "technician_intervention=true "
                    "but intervention_severity "
                    "is 'none'."
                )

            elif (
                intervention_severity
                == "minor"
            ):

                if (
                    intervention_count
                    > 2
                ):

                    if (
                        trial_status
                        != "fail"
                    ):
                        trial_status = "review"

                    trial_reviews.append(
                        "More than two minor "
                        "technician/researcher "
                        "interventions occurred "
                        f"({intervention_count} "
                        "recorded)."
                    )

                else:

                    trial_info.append(
                        f"{intervention_count} minor "
                        "technician/researcher "
                        "intervention(s) recorded; "
                        "trial remains valid."
                    )

            elif (
                intervention_severity
                == "major"
            ):

                if (
                    trial_status
                    != "fail"
                ):
                    trial_status = "review"

                trial_reviews.append(
                    "Major technician/researcher "
                    "intervention occurred "
                    f"({intervention_count} "
                    "intervention(s) recorded)."
                )

        intervals.append(
            (
                trial_id,
                start_time,
                end_time,
            )
        )

        result[
            "trials"
        ].append({
            "trial_id": trial_id,
            "start_time": start_time,
            "end_time": end_time,
            "relative_start_time": (
                relative_start
            ),
            "relative_end_time": (
                relative_end
            ),
            "duration_seconds": (
                duration
            ),
            "task_success": (
                task_success
            ),
            "technician_intervention": (
                technician_intervention
            ),
            "intervention_severity": (
                intervention_severity
            ),
            "intervention_count": (
                intervention_count
            ),
            "notes": (
                row[
                    "notes"
                ]
            ),
            "status": (
                trial_status
            ),
            "issues": (
                trial_issues
            ),
            "review_reasons": (
                trial_reviews
            ),
            "informational_notes": (
                trial_info
            ),
        })

    # --------------------------------------------------------
    # Required trial IDs
    # --------------------------------------------------------

    found_trials = {
        trial[
            "trial_id"
        ]
        for trial
        in result[
            "trials"
        ]
    }

    for required_trial in REQUIRED_TRIALS:

        if (
            required_trial
            not in found_trials
        ):

            result[
                "issues"
            ].append(
                f"Missing required trial "
                f"segment: {required_trial}"
            )

    # --------------------------------------------------------
    # Overlap check
    # --------------------------------------------------------

    sorted_intervals = sorted(
        intervals,
        key=lambda x: x[1],
    )

    for i in range(
        len(
            sorted_intervals
        ) - 1
    ):

        (
            trial_a,
            start_a,
            end_a,
        ) = (
            sorted_intervals[
                i
            ]
        )

        (
            trial_b,
            start_b,
            end_b,
        ) = (
            sorted_intervals[
                i + 1
            ]
        )

        if (
            end_a
            > start_b
        ):

            result[
                "issues"
            ].append(
                f"Trial times overlap: "
                f"{trial_a} and {trial_b}"
            )

    # --------------------------------------------------------
    # Aggregate event-level info
    # --------------------------------------------------------

    for trial in result[
        "trials"
    ]:

        for note in trial.get(
            "informational_notes",
            [],
        ):

            result[
                "informational_notes"
            ].append(
                f"{trial['trial_id']}: "
                f"{note}"
            )

    # --------------------------------------------------------
    # Final events.csv status
    # --------------------------------------------------------

    if len(
        result[
            "issues"
        ]
    ) > 0:

        result[
            "status"
        ] = "fail"

    elif any(
        trial[
            "status"
        ]
        == "review"
        for trial
        in result[
            "trials"
        ]
    ):

        result[
            "status"
        ] = "review"

        for trial in result[
            "trials"
        ]:

            if (
                trial[
                    "status"
                ]
                == "review"
            ):

                for reason in trial[
                    "review_reasons"
                ]:

                    result[
                        "review_reasons"
                    ].append(
                        f"{trial['trial_id']}: "
                        f"{reason}"
                    )

    else:

        result[
            "status"
        ] = "pass"

    return result


# ============================================================
# VIDEO VALIDATION
# ============================================================

def load_video_validation(
    validation_path,
):
    rows = []

    with validation_path.open(
        "r"
    ) as f:

        reader = csv.DictReader(
            f
        )

        for row in reader:

            rows.append(
                row
            )

    return rows


def validate_videos(
    session_dir,
    condition,
):
    session_dir = Path(
        session_dir
    )

    validation_path = (
        session_dir
        / "video_validation.csv"
    )

    result = {
        "condition": (
            condition
        ),
        "status": "pass",
        "validation_path": str(
            validation_path
        ),
        "exists": (
            validation_path.exists()
        ),
        "files": [],
        "issues": [],
        "review_reasons": [],
    }

    expected_videos = (
        CONDITION_VIDEO_REQUIREMENTS
        .get(
            condition
        )
    )

    if expected_videos is None:

        result[
            "status"
        ] = "fail"

        result[
            "issues"
        ].append(
            f"Unknown condition: "
            f"{condition}"
        )

        return result

    if not validation_path.exists():

        result[
            "status"
        ] = "fail"

        result[
            "issues"
        ].append(
            "Missing video_validation.csv."
        )

        return result

    rows = (
        load_video_validation(
            validation_path
        )
    )

    if len(
        rows
    ) == 0:

        result[
            "status"
        ] = "fail"

        result[
            "issues"
        ].append(
            "video_validation.csv is empty."
        )

        return result

    required_columns = [
        "video_name",
        "recorded",
        "notes",
    ]

    for col in required_columns:

        if (
            col
            not in rows[0]
        ):

            result[
                "status"
            ] = "fail"

            result[
                "issues"
            ].append(
                f"Missing column in "
                f"video_validation.csv: "
                f"{col}"
            )

    if (
        result[
            "status"
        ]
        == "fail"
    ):
        return result

    recorded_lookup = {}

    for row in rows:

        video_name = (
            row[
                "video_name"
            ]
            .strip()
        )

        recorded = (
            row[
                "recorded"
            ]
            .strip()
            .lower()
        )

        notes = (
            row[
                "notes"
            ]
            .strip()
        )

        if recorded not in [
            "true",
            "false",
        ]:

            result[
                "issues"
            ].append(
                f"{video_name}: "
                "recorded must be "
                "true or false."
            )

        recorded_lookup[
            video_name
        ] = {
            "recorded": (
                recorded
            ),
            "notes": (
                notes
            ),
        }

    for expected_video in (
        expected_videos
    ):

        if (
            expected_video
            not in recorded_lookup
        ):

            result[
                "issues"
            ].append(
                f"Missing video audit entry: "
                f"{expected_video}"
            )

            result[
                "files"
            ].append({
                "video_name": (
                    expected_video
                ),
                "recorded": None,
                "notes": "",
                "status": "fail",
            })

            continue

        entry = (
            recorded_lookup[
                expected_video
            ]
        )

        recorded = (
            entry[
                "recorded"
            ]
        )

        if recorded == "true":

            status = "pass"

        elif recorded == "false":

            status = "fail"

            result[
                "issues"
            ].append(
                f"Required video was "
                f"not recorded: "
                f"{expected_video}"
            )

        else:

            status = "fail"

        result[
            "files"
        ].append({
            "video_name": (
                expected_video
            ),
            "recorded": (
                recorded
            ),
            "notes": (
                entry[
                    "notes"
                ]
            ),
            "status": (
                status
            ),
        })

    if len(
        result[
            "issues"
        ]
    ) > 0:

        result[
            "status"
        ] = "fail"

    else:

        result[
            "status"
        ] = "pass"

    return result


# ============================================================
# OVERALL STATUS
# ============================================================

def decide_overall_status(
    topic_issues,
    topic_reviews,
    event_result,
    video_result,
):
    issues = []
    review_reasons = []
    informational_notes = []

    issues.extend(
        topic_issues
    )

    review_reasons.extend(
        topic_reviews
    )

    issues.extend(
        event_result.get(
            "issues",
            [],
        )
    )

    review_reasons.extend(
        event_result.get(
            "review_reasons",
            [],
        )
    )

    informational_notes.extend(
        event_result.get(
            "informational_notes",
            [],
        )
    )

    issues.extend(
        video_result.get(
            "issues",
            [],
        )
    )

    review_reasons.extend(
        video_result.get(
            "review_reasons",
            [],
        )
    )

    if (
        event_result.get(
            "status"
        )
        == "review"
        and len(
            event_result.get(
                "review_reasons",
                [],
            )
        ) == 0
    ):

        review_reasons.append(
            "events.csv contains one "
            "or more trial segments "
            "needing review."
        )

    if len(
        issues
    ) > 0:

        return (
            "fail",
            issues,
            review_reasons,
            informational_notes,
        )

    if len(
        review_reasons
    ) > 0:

        return (
            "review",
            issues,
            review_reasons,
            informational_notes,
        )

    return (
        "pass",
        issues,
        review_reasons,
        informational_notes,
    )


# ============================================================
# MAIN
# ============================================================

def main():
    parser = (
        argparse.ArgumentParser()
    )

    parser.add_argument(
        "session_dir",
        help=(
            "Example: "
            "data/P01_VR"
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

    args = (
        parser.parse_args()
    )

    session_dir = Path(
        args.session_dir
    )

    report = {
        "session_dir": str(
            session_dir
        ),
        "condition": (
            args.condition
        ),
        "overall_status": None,
        "bag": None,
        "topics": [],
        "events": None,
        "videos": None,
        "issues": [],
        "review_reasons": [],
        "informational_notes": [],
    }

    # --------------------------------------------------------
    # Find bag
    # --------------------------------------------------------

    bag_path = find_bag(
        session_dir
    )

    if bag_path is None:

        report[
            "overall_status"
        ] = "fail"

        report[
            "issues"
        ].append(
            "No bag file found "
            "in session folder."
        )

        output_path = (
            session_dir
            / "session_validation_report.json"
        )

        save_json(
            report,
            output_path,
        )

        print(
            f"Saved session validation report: "
            f"{output_path}"
        )

        print(
            "Overall status: fail"
        )

        print(
            "Issue: No bag file found "
            "in session folder."
        )

        return

    # --------------------------------------------------------
    # Inspect bag
    # --------------------------------------------------------

    bag_info = inspect_bag(
        bag_path
    )

    report[
        "bag"
    ] = (
        bag_info
    )

    # --------------------------------------------------------
    # Topics
    # --------------------------------------------------------

    (
        topic_results,
        topic_issues,
        topic_reviews,
    ) = validate_topics(
        bag_info
    )

    report[
        "topics"
    ] = (
        topic_results
    )

    # --------------------------------------------------------
    # Events
    # --------------------------------------------------------

    event_result = (
        validate_events(
            session_dir,
            bag_info,
        )
    )

    report[
        "events"
    ] = (
        event_result
    )

    # --------------------------------------------------------
    # Video
    # --------------------------------------------------------

    video_result = (
        validate_videos(
            session_dir,
            args.condition,
        )
    )

    report[
        "videos"
    ] = (
        video_result
    )

    # --------------------------------------------------------
    # Overall
    # --------------------------------------------------------

    (
        overall_status,
        issues,
        review_reasons,
        informational_notes,
    ) = decide_overall_status(
        topic_issues,
        topic_reviews,
        event_result,
        video_result,
    )

    report[
        "overall_status"
    ] = (
        overall_status
    )

    report[
        "issues"
    ] = (
        issues
    )

    report[
        "review_reasons"
    ] = (
        review_reasons
    )

    report[
        "informational_notes"
    ] = (
        informational_notes
    )

    # --------------------------------------------------------
    # Save report
    # --------------------------------------------------------

    output_path = (
        session_dir
        / "session_validation_report.json"
    )

    save_json(
        report,
        output_path,
    )

    # ========================================================
    # TERMINAL OUTPUT
    # ========================================================

    print(
        f"Saved session validation report: "
        f"{output_path}"
    )

    print(
        f"Overall status: "
        f"{overall_status}"
    )

    if issues:

        print("")
        print(
            "Issues:"
        )

        for issue in issues:

            print(
                f"  - {issue}"
            )

    if review_reasons:

        print("")
        print(
            "Review reasons:"
        )

        for reason in (
            review_reasons
        ):

            print(
                f"  - {reason}"
            )

    if informational_notes:

        print("")
        print(
            "Informational notes:"
        )

        for note in (
            informational_notes
        ):

            print(
                f"  - {note}"
            )

    print("")
    print(
        "Topic summary:"
    )

    for topic in (
        topic_results
    ):

        print(
            f"  {topic['status']}: "
            f"{topic['topic']} "
            f"({topic['message_count']} msgs)"
        )

    print("")
    print(
        "Event summary:"
    )

    print(
        f"  events.csv status: "
        f"{event_result['status']}"
    )

    for trial in (
        event_result.get(
            "trials",
            [],
        )
    ):

        print(
            f"  {trial['trial_id']}: "
            f"{trial['duration_seconds']:.2f}s, "
            f"status={trial['status']}, "
            f"success={trial['task_success']}, "
            f"intervention="
            f"{trial['technician_intervention']}, "
            f"severity="
            f"{trial['intervention_severity']}, "
            f"count="
            f"{trial['intervention_count']}"
        )

    print("")
    print(
        "Video summary:"
    )

    print(
        f"  video status: "
        f"{video_result['status']}"
    )

    for item in (
        video_result.get(
            "files",
            [],
        )
    ):

        print(
            f"  {item['status']}: "
            f"{item['video_name']} "
            f"(recorded="
            f"{item['recorded']})"
        )


if __name__ == "__main__":
    main()