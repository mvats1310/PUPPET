#!/usr/bin/env python3

import argparse
import json
import subprocess
from pathlib import Path

import pandas as pd


CONDITIONS = ["VR", "2D", "REAL"]


def load_json(path):
    with Path(path).open("r") as f:
        return json.load(f)


def save_json(data, path):
    with Path(path).open("w") as f:
        json.dump(data, f, indent=2)


def run_validate_session(session_dir, condition):
    cmd = [
        "python",
        "validate_session.py",
        str(session_dir),
        "--condition",
        condition,
    ]

    print("")
    print("=" * 80)
    print("Running:", " ".join(cmd))
    print("=" * 80)

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.stdout.strip():
        print(result.stdout.strip())

    if result.stderr.strip():
        print(result.stderr.strip())

    return result.returncode


def parse_session_name(session_dir):
    """
    Expected folder format:
    P01_VR
    P01_2D
    P01_REAL
    """

    name = session_dir.name
    parts = name.split("_")

    if len(parts) != 2:
        return None, None

    participant_id = parts[0]
    condition = parts[1]

    if condition not in CONDITIONS:
        return None, None

    return participant_id, condition


def summarize_report(session_dir, report):
    participant_id, condition_from_name = parse_session_name(session_dir)

    condition = report.get("condition", condition_from_name)

    bag = report.get("bag") or {}
    events = report.get("events") or {}
    videos = report.get("videos") or {}

    topics = report.get("topics") or []

    required_topics = [t for t in topics if t.get("required") is True]

    required_topics_present = [
        t
        for t in required_topics
        if t.get("exists") is True and t.get("message_count", 0) > 0
    ]

    missing_required_topics = [
        t.get("topic")
        for t in required_topics
        if not (
            t.get("exists") is True
            and t.get("message_count", 0) > 0
        )
    ]

    event_trials = events.get("trials") or []

    trial_ids_found = [
        trial.get("trial_id")
        for trial in event_trials
        if trial.get("trial_id") is not None
    ]

    required_video_files = videos.get("required_files") or []

    missing_required_videos = [
        item.get("file")
        for item in required_video_files
        if item.get("exists") is False
    ]

    optional_video_files = videos.get("optional_files") or []

    missing_optional_videos = [
        item.get("file")
        for item in optional_video_files
        if item.get("exists") is False
    ]

    row = {
        "session_dir": str(session_dir),
        "participant_id": participant_id,
        "condition": condition,
        "session_status": report.get("overall_status"),
        "bag_exists": bag.get("exists"),
        "bag_path": bag.get("bag_path"),
        "bag_duration_seconds": bag.get("duration_seconds"),
        "bag_size_mb": bag.get("size_mb"),
        "total_messages": bag.get("total_messages"),
        "num_required_topics": len(required_topics),
        "num_required_topics_present": len(required_topics_present),
        "missing_required_topics": ", ".join(missing_required_topics),
        "events_csv_exists": events.get("exists"),
        "events_status": events.get("status"),
        "num_event_trials": len(event_trials),
        "event_trials_found": ", ".join(trial_ids_found),
        "video_status": videos.get("status"),
        "missing_required_videos": ", ".join(missing_required_videos),
        "missing_optional_videos": ", ".join(missing_optional_videos),
        "num_issues": len(report.get("issues", [])),
        "num_review_reasons": len(report.get("review_reasons", [])),
        "issues": " | ".join(report.get("issues", [])),
        "review_reasons": " | ".join(report.get("review_reasons", [])),
    }

    return row


def find_session_dirs(data_dir, participant=None):
    data_dir = Path(data_dir)
    session_dirs = []

    for path in sorted(data_dir.iterdir()):
        if not path.is_dir():
            continue

        participant_id, condition = parse_session_name(path)

        if participant_id is None or condition is None:
            continue

        if participant is not None and participant_id != participant:
            continue

        session_dirs.append(path)

    return session_dirs


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "data_dir",
        help="Data directory, usually: data"
    )

    parser.add_argument(
        "--participant",
        default=None,
        help="Optional participant ID, e.g. P01"
    )

    args = parser.parse_args()

    data_dir = Path(args.data_dir)

    session_dirs = find_session_dirs(
        data_dir,
        participant=args.participant
    )

    if len(session_dirs) == 0:
        raise ValueError(
            "No session folders found. "
            "Expected folders like data/P01_VR, "
            "data/P01_2D or data/P01_REAL."
        )

    print(f"Found {len(session_dirs)} session folders.")

    rows = []

    for session_dir in session_dirs:
        participant_id, condition = parse_session_name(session_dir)

        print("")
        print(f"Validating session: {session_dir}")

        run_validate_session(
            session_dir,
            condition
        )

        report_path = (
            session_dir
            / "session_validation_report.json"
        )

        if not report_path.exists():
            rows.append(
                {
                    "session_dir": str(session_dir),
                    "participant_id": participant_id,
                    "condition": condition,
                    "session_status": "fail",
                    "issues": (
                        "session_validation_report.json "
                        "was not created"
                    ),
                }
            )
            continue

        report = load_json(report_path)

        row = summarize_report(
            session_dir,
            report
        )

        rows.append(row)

    summary_df = pd.DataFrame(rows)

    output_csv = (
        data_dir
        / "session_validation_summary.csv"
    )

    output_json = (
        data_dir
        / "session_validation_summary.json"
    )

    summary_df.to_csv(
        output_csv,
        index=False
    )

    save_json(
        summary_df.to_dict(
            orient="records"
        ),
        output_json
    )

    print("")
    print("=" * 80)
    print("Saved session validation summary:")
    print(f"  {output_csv}")
    print(f"  {output_json}")
    print("=" * 80)

    print("")
    print("Session summary:")

    display_cols = [
        "participant_id",
        "condition",
        "session_status",
        "bag_exists",
        "bag_duration_seconds",
        "num_required_topics_present",
        "num_required_topics",
        "events_status",
        "num_event_trials",
        "video_status",
    ]

    existing_cols = [
        col
        for col in display_cols
        if col in summary_df.columns
    ]

    print(
        summary_df[
            existing_cols
        ].to_string(index=False)
    )

    print("")
    print("Status counts:")

    print(
        summary_df[
            "session_status"
        ].value_counts(
            dropna=False
        ).to_string()
    )


if __name__ == "__main__":
    main()

