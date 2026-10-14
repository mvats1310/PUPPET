#!/usr/bin/env python3

import argparse
import subprocess
from pathlib import Path


CONDITIONS = ["VR", "2D", "REAL"]
TRIALS = ["T01", "T02", "T03"]


def run_command(cmd, allow_fail=False):
    print("")
    print("=" * 80)
    print("Running:", " ".join(cmd))
    print("=" * 80)

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.stdout.strip():
        print(result.stdout.strip())

    if result.stderr.strip():
        print(result.stderr.strip())

    if result.returncode != 0 and not allow_fail:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")

    return result.returncode


def session_dir(data_dir, participant, condition):
    return data_dir / f"{participant}_{condition}"


def session_dir_exists(data_dir, participant, condition):
    return session_dir(data_dir, participant, condition).exists()


def bag_exists(session_path):
    possible_bags = [
        session_path / "full_session_fixed.bag",
        session_path / "full_session.bag",
    ]

    if any(path.exists() for path in possible_bags):
        return True

    return len(list(session_path.glob("*.bag"))) > 0


def events_csv_valid_enough(session_path):
    events_path = session_path / "events.csv"

    if not events_path.exists():
        return False

    text = events_path.read_text()

    if "START" in text or "END" in text:
        return False

    return True


def trial_dir(data_dir, participant, condition, trial):
    return data_dir / f"{participant}_{condition}_{trial}"


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--data",
        default="data",
        help="Data directory"
    )

    parser.add_argument(
        "--participant",
        required=True,
        help="Participant ID, e.g. P03"
    )

    args = parser.parse_args()

    data_dir = Path(args.data)
    participant = args.participant

    print("")
    print("PUPPET Validation Pipeline")
    print(f"Data directory: {data_dir}")
    print(f"Participant: {participant}")

    # ============================================================
    # 1. INDIVIDUAL SESSION VALIDATION
    # ============================================================

    for condition in CONDITIONS:
        sd = session_dir(
            data_dir,
            participant,
            condition
        )

        if not sd.exists():
            print(
                f"Skipping session validation for {condition}: "
                "session folder missing."
            )
            continue

        run_command(
            [
                "python",
                "validate_session.py",
                str(sd),
                "--condition",
                condition,
            ],
            allow_fail=True
        )

    # ============================================================
    # 1B. BATCH SESSION SUMMARY
    # ============================================================

    run_command(
        [
            "python",
            "validate_all_sessions.py",
            str(data_dir),
            "--participant",
            participant,
        ],
        allow_fail=True
    )

    # ============================================================
    # 2. TELEMETRY EXTRACTION
    # ============================================================

    for condition in CONDITIONS:
        sd = session_dir(
            data_dir,
            participant,
            condition
        )

        if not sd.exists():
            print(
                f"Skipping extraction for {condition}: "
                "session folder missing."
            )
            continue

        if not bag_exists(sd):
            print(
                f"Skipping extraction for {condition}: "
                "no bag found."
            )
            continue

        if not events_csv_valid_enough(sd):
            print(
                f"Skipping extraction for {condition}: "
                "events.csv missing or still has "
                "START/END placeholders."
            )
            continue

        run_command(
            [
                "python",
                "extract_telemetry_from_bag.py",
                "--session",
                str(sd),
                "--participant",
                participant,
                "--condition",
                condition,
            ],
            allow_fail=True
        )

    # ============================================================
    # 3. TRIAL VALIDATION
    # ============================================================

    run_command(
        [
            "python",
            "validate_all_trials.py",
            str(data_dir),
        ],
        allow_fail=True
    )

    # ============================================================
    # 4. TRIAL QUALITY METRICS
    # ============================================================

    for condition in CONDITIONS:
        for trial in TRIALS:

            td = trial_dir(
                data_dir,
                participant,
                condition,
                trial
            )

            if not td.exists():
                print(
                    f"Skipping quality analysis: "
                    f"{td} missing."
                )
                continue

            if not (td / "telemetry.csv").exists():
                print(
                    f"Skipping quality analysis: "
                    f"{td}/telemetry.csv missing."
                )
                continue

            if not (td / "metadata.yaml").exists():
                print(
                    f"Skipping quality analysis: "
                    f"{td}/metadata.yaml missing."
                )
                continue

            run_command(
                [
                    "python",
                    "analyze_trial.py",
                    str(td),
                ],
                allow_fail=True
            )

    # ============================================================
    # 5. RE-RUN TRIAL VALIDATION
    #    AFTER QUALITY REPORTS EXIST
    # ============================================================

    run_command(
        [
            "python",
            "validate_all_trials.py",
            str(data_dir),
        ],
        allow_fail=True
    )

    # ============================================================
    # 6. CONDITION SUMMARY
    # ============================================================

    run_command(
        [
            "python",
            "summarize_conditions.py",
            str(data_dir),
        ],
        allow_fail=True
    )

    # ============================================================
    # 7. PARTICIPANT SUMMARY
    # ============================================================

    run_command(
        [
            "python",
            "summarize_participants.py",
            str(data_dir),
        ],
        allow_fail=True
    )

    # ============================================================
    # 8. DATASET CONSISTENCY / RANGE REPORT
    # ============================================================

    run_command(
        [
            "python",
            "analyze_dataset_consistency.py",
            str(data_dir),
        ],
        allow_fail=True
    )

    # ============================================================
    # 9. FINAL CURATION REPORT
    # ============================================================

    run_command(
        [
            "python",
            "final_curation_report.py",
            str(data_dir),
        ],
        allow_fail=True
    )

    # ============================================================
    # 10. MERGE SESSION VALIDATION INTO CURATION
    # ============================================================

    run_command(
        [
            "python",
            "merge_session_into_curation.py",
            str(data_dir),
        ],
        allow_fail=True
    )

    # ============================================================
    # 11. GENERATE READABLE MASTER REPORT
    # ============================================================

    run_command(
        [
            "python",
            "generate_master_report.py",
            "--data",
            str(data_dir),
            "--participant",
            participant,
        ],
        allow_fail=True
    )

    # ============================================================
    # DONE
    # ============================================================

    print("")
    print("=" * 80)
    print("Pipeline finished.")
    print("=" * 80)

    print("")
    print("Main outputs:")
    print(
        f"  {data_dir}/trial_validation_summary.csv"
    )
    print(
        f"  {data_dir}/condition_validation_summary.csv"
    )
    print(
        f"  {data_dir}/participant_validation_summary.csv"
    )
    print(
        f"  {data_dir}/dataset_range_report.csv"
    )
    print(
        f"  {data_dir}/final_trial_curation_report.csv"
    )
    print(
        f"  {data_dir}/final_condition_curation_report.csv"
    )
    print(
        f"  {data_dir}/final_participant_curation_report.csv"
    )
    print(
        f"  {data_dir}/session_validation_summary.csv"
    )
    print(
        f"  {data_dir}/{participant}_master_validation_report.md"
    )


if __name__ == "__main__":
    main()