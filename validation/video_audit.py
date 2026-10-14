#!/usr/bin/env python3

import argparse
from pathlib import Path

import yaml


def load_yaml(path):
    with path.open("r") as f:
        return yaml.safe_load(f)


def save_yaml(data, path):
    with path.open("w") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def ask_bool(question, default=None):
    if default is True:
        suffix = " [Y/n]: "
    elif default is False:
        suffix = " [y/N]: "
    else:
        suffix = " [y/n]: "

    while True:
        answer = input(question + suffix).strip().lower()

        if answer == "" and default is not None:
            return default

        if answer in ["y", "yes", "true", "1"]:
            return True

        if answer in ["n", "no", "false", "0"]:
            return False

        print("Please answer y or n.")


def ask_text(question, default=""):
    if default:
        answer = input(f"{question} [{default}]: ").strip()
        return answer if answer else default

    return input(question + ": ").strip()


def get_default(section, key, fallback=None):
    if not isinstance(section, dict):
        return fallback
    return section.get(key, fallback)


def audit_vr_or_real(metadata):
    existing = metadata.get("video_validation", {})

    return {
        "tiago_pov_available": ask_bool(
            "TIAGo POV available/recorded?",
            get_default(existing, "tiago_pov_available", True)
        ),
        "video_covers_full_trial": ask_bool(
            "Does video cover the full trial?",
            get_default(existing, "video_covers_full_trial", True)
        ),
        "object_visible": ask_bool(
            "Is the object visible?",
            get_default(existing, "object_visible", True)
        ),
        "robot_visible": ask_bool(
            "Is the robot visible?",
            get_default(existing, "robot_visible", True)
        ),
        "shelf_visible": ask_bool(
            "Is the shelf/target visible?",
            get_default(existing, "shelf_visible", True)
        ),
        "camera_freeze_or_dropout": ask_bool(
            "Any camera freeze/dropout?",
            get_default(existing, "camera_freeze_or_dropout", False)
        ),
        "intervention_visible": ask_bool(
            "Is any intervention visible?",
            get_default(existing, "intervention_visible", False)
        ),
        "notes": ask_text(
            "Video audit notes",
            get_default(existing, "notes", "")
        ),
    }


def audit_2d(metadata):
    existing = metadata.get("video_validation", {})

    return {
        "tiago_pov_available": ask_bool(
            "TIAGo POV available/recorded?",
            get_default(existing, "tiago_pov_available", True)
        ),
        "camera_1_available": ask_bool(
            "Camera 1 available?",
            get_default(existing, "camera_1_available", True)
        ),
        "camera_2_available": ask_bool(
            "Camera 2 available?",
            get_default(existing, "camera_2_available", True)
        ),
        "camera_3_available": ask_bool(
            "Camera 3 available?",
            get_default(existing, "camera_3_available", True)
        ),
        "video_covers_full_trial": ask_bool(
            "Do the videos cover the full trial?",
            get_default(existing, "video_covers_full_trial", True)
        ),
        "object_visible_in_at_least_one_view": ask_bool(
            "Is object visible in at least one view?",
            get_default(existing, "object_visible_in_at_least_one_view", True)
        ),
        "robot_visible_in_at_least_one_view": ask_bool(
            "Is robot visible in at least one view?",
            get_default(existing, "robot_visible_in_at_least_one_view", True)
        ),
        "shelf_visible_in_at_least_one_view": ask_bool(
            "Is shelf/target visible in at least one view?",
            get_default(existing, "shelf_visible_in_at_least_one_view", True)
        ),
        "camera_freeze_or_dropout": ask_bool(
            "Any camera freeze/dropout?",
            get_default(existing, "camera_freeze_or_dropout", False)
        ),
        "intervention_visible": ask_bool(
            "Is any intervention visible?",
            get_default(existing, "intervention_visible", False)
        ),
        "notes": ask_text(
            "Video audit notes",
            get_default(existing, "notes", "")
        ),
    }


def update_curation_from_video(metadata):
    video_validation = metadata.get("video_validation", {})
    curation = metadata.get("curation", {})

    review_reasons = []

    if video_validation.get("video_covers_full_trial") is False:
        review_reasons.append("video does not cover full trial")

    if video_validation.get("camera_freeze_or_dropout") is True:
        review_reasons.append("camera freeze/dropout")

    condition = metadata.get("condition")

    if condition == "2D":
        if video_validation.get("object_visible_in_at_least_one_view") is False:
            review_reasons.append("object not visible in 2D camera views")
        if video_validation.get("robot_visible_in_at_least_one_view") is False:
            review_reasons.append("robot not visible in 2D camera views")
        if video_validation.get("shelf_visible_in_at_least_one_view") is False:
            review_reasons.append("shelf not visible in 2D camera views")
    else:
        if video_validation.get("object_visible") is False:
            review_reasons.append("object not visible")
        if video_validation.get("robot_visible") is False:
            review_reasons.append("robot not visible")
        if video_validation.get("shelf_visible") is False:
            review_reasons.append("shelf not visible")

    if review_reasons:
        curation["trial_level_decision"] = "review"
        existing_reason = curation.get("review_reason")

        new_reason = "; ".join(review_reasons)

        if existing_reason and existing_reason != "null":
            curation["review_reason"] = str(existing_reason) + "; " + new_reason
        else:
            curation["review_reason"] = new_reason
    else:
        if curation.get("trial_level_decision") in [None, "null", ""]:
            curation["trial_level_decision"] = "keep"
        if curation.get("review_reason") in [None, ""]:
            curation["review_reason"] = None

    metadata["curation"] = curation
    return metadata


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("trial_dir", help="Trial folder, e.g. data/P001_VR_T01")
    args = parser.parse_args()

    trial_dir = Path(args.trial_dir)
    metadata_path = trial_dir / "metadata.yaml"

    if not metadata_path.exists():
        raise FileNotFoundError(f"Missing metadata.yaml in {trial_dir}")

    metadata = load_yaml(metadata_path)

    condition = metadata.get("condition")

    print("")
    print(f"Video audit for: {trial_dir}")
    print(f"Condition: {condition}")
    print("")

    if condition == "2D":
        metadata["video_validation"] = audit_2d(metadata)
    elif condition in ["VR", "REAL"]:
        metadata["video_validation"] = audit_vr_or_real(metadata)
    else:
        raise ValueError(f"Unknown condition: {condition}")

    metadata = update_curation_from_video(metadata)

    save_yaml(metadata, metadata_path)

    print("")
    print(f"Updated video_validation in: {metadata_path}")
    print("Run validation again with:")
    print(f"python validate_trial.py {trial_dir}")


if __name__ == "__main__":
    main()
