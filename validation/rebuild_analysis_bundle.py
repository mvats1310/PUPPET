#!/usr/bin/env python3

from pathlib import Path
import pandas as pd
import numpy as np
import json
import shutil
import yaml

DATA = Path("data")
BUNDLE = Path("/home/mahika/PUPPET_analysis_bundle")
TEL_OUT = BUNDLE / "telemetry"
REPORT_OUT = BUNDLE / "source_reports"

MASTER_COLS = [
    "participant_id","condition","trial_id","trial_number","trial_phase","trial_dir",
    "task_success","technician_intervention","intervention_count","intervention_severity",
    "object_picked","object_placed_on_shelf","object_dropped","unsafe_robot_motion",
    "reset_required","researcher_helped_task","video_covers_full_trial",
    "camera_freeze_or_dropout","validation_status","validation_issues",
    "validation_review_reasons","completion_time","num_rows","mean_time_gap",
    "max_time_gap","duplicate_timestamp_count","joint_path_length","joint_jerk",
    "joint_jerk_rms","joint_jerk_peak","joint_effort","total_joint_range",
    "ee_missing_ratio","cartesian_path_length","cartesian_path_length_clean",
    "cartesian_jerk","ee_jump_count","ee_max_speed","base_path_length",
    "base_path_length_clean","base_jump_count","base_max_speed","base_stale_ratio",
    "object_path_length","object_path_length_clean","object_jump_count",
    "object_max_speed","object_stale_ratio","range_object_x","range_object_y",
    "range_object_z","gripper_range","gripper_reversal_count",
    "gripper_open_close_cycles","gripper_chatter","health_flags",
]

TEL_COLS = [
    "time","ee_x","ee_y","ee_z",
    "joint_1","joint_2","joint_3","joint_4","joint_5","joint_6","joint_7",
    "gripper_state","base_x","base_y","base_yaw",
    "object_x","object_y","object_z",
    "robot_marker_x","robot_marker_y","robot_marker_z",
    "trial_time","participant_id","condition","trial_id",
]

SUMMARY_METRICS = [
    "completion_time",
    "joint_path_length",
    "joint_jerk",
    "joint_effort",
    "cartesian_path_length_clean",
    "base_path_length_clean",
    "object_path_length_clean",
    "gripper_chatter",
]

def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}

def load_yaml(path):
    try:
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}

def textify(x):
    if x is None or x == []:
        return np.nan
    if isinstance(x, list):
        return " | ".join(str(v) for v in x)
    return str(x)

def first_value(*values):
    for x in values:
        if x is not None:
            return x
    return np.nan

# ------------------------------------------------------------
# Canonical trial list = current final curation report
# ------------------------------------------------------------

curation_path = DATA / "final_trial_curation_report.csv"

if not curation_path.exists():
    raise FileNotFoundError(
        "data/final_trial_curation_report.csv missing. "
        "Run final_curation_report.py first."
    )

curation = pd.read_csv(curation_path)

print("Curation rows:", len(curation))
print(
    "Participants:",
    ", ".join(
        sorted(
            curation["participant_id"].dropna().unique(),
            key=lambda x: int(str(x)[1:])
        )
    )
)

# ------------------------------------------------------------
# Clean generated bundle directories
# ------------------------------------------------------------

TEL_OUT.mkdir(parents=True, exist_ok=True)
REPORT_OUT.mkdir(parents=True, exist_ok=True)

for p in TEL_OUT.glob("*.csv"):
    p.unlink()

for p in REPORT_OUT.iterdir():
    if p.is_dir():
        shutil.rmtree(p)

master_rows = []
all_tel = []

# ------------------------------------------------------------
# Rebuild every canonical trial
# ------------------------------------------------------------

for _, c in curation.iterrows():

    participant = str(c["participant_id"])
    condition = str(c["condition"])
    trial_id = str(c["trial_id"])

    trial_dir = DATA / f"{participant}_{condition}_{trial_id}"

    if not trial_dir.exists():
        print("WARNING missing trial directory:", trial_dir)
        continue

    metadata = load_yaml(trial_dir / "metadata.yaml")
    quality = load_json(trial_dir / "quality_report.json")
    validation = load_json(trial_dir / "validation_report.json")

    metrics = quality.get("metrics", {}) or {}

    trial_number = int(trial_id.replace("T", ""))
    trial_phase = "learning" if trial_id == "T01" else "execution"

    row = {
        "participant_id": participant,
        "condition": condition,
        "trial_id": trial_id,
        "trial_number": trial_number,
        "trial_phase": trial_phase,
        "trial_dir": f"data/{trial_dir.name}",

        "task_success": first_value(
            metadata.get("task_success"),
            quality.get("task_success"),
            c.get("task_success"),
        ),

        "technician_intervention": first_value(
            metadata.get("technician_intervention"),
            quality.get("technician_intervention"),
            c.get("technician_intervention"),
        ),

        "intervention_count": first_value(
            metadata.get("intervention_count"),
            quality.get("intervention_count"),
        ),

        "intervention_severity": first_value(
            metadata.get("intervention_severity"),
            quality.get("intervention_severity"),
        ),

        "object_picked": metadata.get("object_picked"),
        "object_placed_on_shelf": metadata.get("object_placed_on_shelf"),
        "object_dropped": metadata.get("object_dropped"),
        "unsafe_robot_motion": metadata.get("unsafe_robot_motion"),
        "reset_required": metadata.get("reset_required"),
        "researcher_helped_task": metadata.get("researcher_helped_task"),
        "video_covers_full_trial": metadata.get("video_covers_full_trial"),
        "camera_freeze_or_dropout": metadata.get("camera_freeze_or_dropout"),

        "validation_status": validation.get("status", c.get("status")),
        "validation_issues": textify(validation.get("issues", [])),
        "validation_review_reasons": textify(
            validation.get("review_reasons", [])
        ),
    }

    for metric in [
        "completion_time","num_rows","mean_time_gap","max_time_gap",
        "duplicate_timestamp_count","joint_path_length","joint_jerk",
        "joint_jerk_rms","joint_jerk_peak","joint_effort",
        "total_joint_range","ee_missing_ratio","cartesian_path_length",
        "cartesian_path_length_clean","cartesian_jerk","ee_jump_count",
        "ee_max_speed","base_path_length","base_path_length_clean",
        "base_jump_count","base_max_speed","base_stale_ratio",
        "object_path_length","object_path_length_clean",
        "object_jump_count","object_max_speed","object_stale_ratio",
        "range_object_x","range_object_y","range_object_z",
        "gripper_range","gripper_reversal_count",
        "gripper_open_close_cycles","gripper_chatter",
    ]:
        row[metric] = metrics.get(metric)

    row["health_flags"] = textify(metrics.get("health_flags", []))

    master_rows.append(row)

    # Source reports
    dst = REPORT_OUT / trial_dir.name
    dst.mkdir(parents=True, exist_ok=True)

    for name in [
        "quality_report.json",
        "validation_report.json",
        "metadata.yaml",
    ]:
        src = trial_dir / name
        if src.exists():
            shutil.copyfile(src, dst / name)

    # Telemetry
    telemetry_path = trial_dir / "telemetry.csv"

    if telemetry_path.exists():
        tel = pd.read_csv(telemetry_path)

        if not tel.empty and "time" in tel.columns:
            tel = tel.sort_values("time").reset_index(drop=True)

            # Original telemetry is ~50 Hz -> approximate 10 Hz.
            tel10 = tel.iloc[::5].copy().reset_index(drop=True)

            numeric_time = pd.to_numeric(
                tel10["time"], errors="coerce"
            )

            if numeric_time.notna().any():
                first_t = numeric_time.dropna().iloc[0]
                tel10["trial_time"] = numeric_time - first_t
            else:
                tel10["trial_time"] = np.nan

            tel10["participant_id"] = participant
            tel10["condition"] = condition
            tel10["trial_id"] = trial_id

            for col in TEL_COLS:
                if col not in tel10.columns:
                    tel10[col] = np.nan

            tel10 = tel10[TEL_COLS]

            tel10.to_csv(
                TEL_OUT / f"{trial_dir.name}.csv",
                index=False
            )

            all_tel.append(tel10)

# ------------------------------------------------------------
# Master trial dataset
# ------------------------------------------------------------

master = pd.DataFrame(master_rows)

for col in MASTER_COLS:
    if col not in master.columns:
        master[col] = np.nan

master = master[MASTER_COLS]

master["_participant_num"] = (
    master["participant_id"]
    .str.extract(r"(\d+)")[0]
    .astype(int)
)

master["_condition_order"] = master["condition"].map(
    {"REAL": 0, "2D": 1, "VR": 2}
)

master = (
    master
    .sort_values(
        ["_participant_num", "_condition_order", "trial_number"]
    )
    .drop(columns=["_participant_num", "_condition_order"])
)

master.to_csv(
    BUNDLE / "master_trial_dataset.csv",
    index=False
)

# ------------------------------------------------------------
# Combined 10 Hz telemetry
# ------------------------------------------------------------

if all_tel:
    combined = pd.concat(all_tel, ignore_index=True)
else:
    combined = pd.DataFrame(columns=TEL_COLS)

combined.to_csv(
    BUNDLE / "all_telemetry_10hz.csv",
    index=False
)

# ------------------------------------------------------------
# Participant-condition summary
# ------------------------------------------------------------

summary_rows = []

for (participant, condition), g in master.groupby(
    ["participant_id", "condition"]
):

    success = g["task_success"].astype(str).str.lower().eq("true")
    intervention = (
        g["technician_intervention"]
        .astype(str)
        .str.lower()
        .eq("true")
    )

    intervention_counts = pd.to_numeric(
        g["intervention_count"],
        errors="coerce"
    ).fillna(0)

    row = {
        "participant_id": participant,
        "condition": condition,
        "n_trials": len(g),
        "n_success": int(success.sum()),
        "intervention_trials": int(intervention.sum()),
        "total_interventions": int(intervention_counts.sum()),
        "n_pass": int(
            g["validation_status"]
            .astype(str)
            .str.lower()
            .eq("pass")
            .sum()
        ),
        "n_review": int(
            g["validation_status"]
            .astype(str)
            .str.lower()
            .eq("review")
            .sum()
        ),
        "n_fail": int(
            g["validation_status"]
            .astype(str)
            .str.lower()
            .eq("fail")
            .sum()
        ),
    }

    execution = g[g["trial_phase"] == "execution"]

    for metric in SUMMARY_METRICS:
        vals = pd.to_numeric(g[metric], errors="coerce")
        row[f"{metric}_mean"] = vals.mean()
        row[f"{metric}_sd"] = vals.std(ddof=1)

    for metric in SUMMARY_METRICS:
        vals = pd.to_numeric(
            execution[metric],
            errors="coerce"
        )
        row[f"{metric}_execution_mean"] = vals.mean()
        row[f"{metric}_execution_sd"] = vals.std(ddof=1)

    summary_rows.append(row)

summary = pd.DataFrame(summary_rows)

summary_cols = [
    "participant_id","condition","n_trials","n_success",
    "intervention_trials","total_interventions",
    "n_pass","n_review","n_fail",
]

for metric in SUMMARY_METRICS:
    summary_cols += [
        f"{metric}_mean",
        f"{metric}_sd",
    ]

for metric in SUMMARY_METRICS:
    summary_cols += [
        f"{metric}_execution_mean",
        f"{metric}_execution_sd",
    ]

summary = summary[summary_cols]

summary.to_csv(
    BUNDLE / "participant_condition_summary.csv",
    index=False
)

# ------------------------------------------------------------
# Copy global current reports
# ------------------------------------------------------------

for name in [
    "trial_validation_summary.csv",
    "condition_validation_summary.csv",
    "participant_validation_summary.csv",
    "session_validation_summary.csv",
    "validation_summary.csv",
    "final_trial_curation_report.csv",
    "final_condition_curation_report.csv",
    "final_participant_curation_report.csv",
    "dataset_range_report.csv",
    "dataset_consistency_report.csv",
]:
    src = DATA / name

    if src.exists():
        shutil.copyfile(src, BUNDLE / name)

# ------------------------------------------------------------
# Compact condition summary
# ------------------------------------------------------------

condition_rows = []

for condition, g in master.groupby("condition"):

    statuses = g["validation_status"].astype(str).str.lower()

    condition_rows.append({
        "condition": condition,
        "n_trials": len(g),
        "n_participants": g["participant_id"].nunique(),
        "n_success": int(
            g["task_success"]
            .astype(str)
            .str.lower()
            .eq("true")
            .sum()
        ),
        "n_pass": int(statuses.eq("pass").sum()),
        "n_review": int(statuses.eq("review").sum()),
        "n_fail": int(statuses.eq("fail").sum()),
    })

pd.DataFrame(condition_rows).to_csv(
    BUNDLE / "condition_summary.csv",
    index=False
)

print("\n============================================")
print("PUPPET ANALYSIS BUNDLE REBUILT")
print("============================================")

print("Master:", master.shape)
print("Summary:", summary.shape)
print("Telemetry:", combined.shape)

print("\nParticipants:")
print(
    ", ".join(
        sorted(
            master["participant_id"].unique(),
            key=lambda x: int(x[1:])
        )
    )
)

print("\nTrials per participant:")
print(master.groupby("participant_id").size().to_string())

print("\nValidation:")
print(
    master["validation_status"]
    .value_counts(dropna=False)
    .to_string()
)

print("\nIndividual telemetry files:", len(list(TEL_OUT.glob("P*.csv"))))
print(
    "Source report folders:",
    len([p for p in REPORT_OUT.iterdir() if p.is_dir()])
)
