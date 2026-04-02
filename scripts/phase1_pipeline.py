#!/usr/bin/env python3
"""Phase 1 Pipeline: Load, validate, and profile SWE-agent trajectory data."""

import json
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from data.load_dataset import load_normalized
from data.validate_schema import validate_dataset, data_profile

OUTPUT_DIR = PROJECT_ROOT / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


def main():
    print("=" * 60)
    print("Phase 1: Load, Validate & Profile SWE-agent Trajectories")
    print("=" * 60)

    # Step 1: Load the full dataset
    print("\n[1/3] Loading normalized dataset (source=local) ...")
    rows = load_normalized(source="local")
    print(f"       Loaded {len(rows):,} rows.")

    # Step 2: Validate schema
    print("\n[2/3] Running schema validation ...")
    validation_report = validate_dataset(rows)
    val_path = OUTPUT_DIR / "validation_report.json"
    val_path.write_text(json.dumps(validation_report, indent=2))
    print(f"       Saved to {val_path}")

    # Step 3: Data profile
    print("\n[3/3] Generating data profile ...")
    profile = data_profile(rows)
    prof_path = OUTPUT_DIR / "data_profile.json"
    prof_path.write_text(json.dumps(profile, indent=2))
    print(f"       Saved to {prof_path}")

    # Print both reports
    print("\n" + "=" * 60)
    print("VALIDATION REPORT")
    print("=" * 60)
    print(json.dumps(validation_report, indent=2))

    print("\n" + "=" * 60)
    print("DATA PROFILE")
    print("=" * 60)
    print(json.dumps(profile, indent=2))

    print("\n" + "=" * 60)
    print("Phase 1 complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
