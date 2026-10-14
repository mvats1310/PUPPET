from pathlib import Path
import argparse
from quality_metrics import analyze_trial, save_json

def main():
    parser = argparse.ArgumentParser(description="Analyze one PUPPET trial folder.")
    parser.add_argument("trial_dir", type=str)
    args = parser.parse_args()
    trial_dir = Path(args.trial_dir)
    report = analyze_trial(trial_dir)
    output_path = trial_dir / "quality_report.json"
    save_json(report, output_path)
    print(f"Saved trial quality report: {output_path}")
    print("Metrics:")
    for k, v in report["metrics"].items(): print(f"  {k}: {v}")
if __name__ == "__main__": main()
