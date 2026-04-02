#!/usr/bin/env python3
"""Phase 2: Load SWE-agent trajectories and compute baseline (BEFORE) KPIs."""

import json
import sys
import time
from pathlib import Path

# Ensure project root is on sys.path so we can import src.*
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from data.load_dataset import load_normalized
from analysis.baseline_metrics import compute_baseline


def main():
    print("=" * 60)
    print("Phase 2: Baseline KPI Computation")
    print("=" * 60)

    # Step 1 – Load the full dataset
    print("\n[1/3] Loading normalized dataset (source=local) ...")
    t0 = time.time()
    rows = load_normalized(source="local")
    elapsed = time.time() - t0
    print(f"      Loaded {len(rows):,} rows in {elapsed:.1f}s")

    # Step 2 – Compute baseline KPIs
    print("\n[2/3] Computing baseline metrics ...")
    baseline = compute_baseline(rows)

    # Step 3 – Save to outputs/baseline.json
    output_path = PROJECT_ROOT / "outputs" / "baseline.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(baseline, f, indent=2)
    print(f"      Saved to {output_path}")

    # Pretty-print the results
    print("\n[3/3] Baseline KPIs (BEFORE)")
    print("-" * 60)
    print(f"  Total traces:          {baseline['total_traces']:,}")
    print(f"  Successes:             {baseline['success_count']:,}")
    print(f"  Failures:              {baseline['failure_count']:,}")
    print(f"  Success rate:          {baseline['success_rate']:.2%}")
    print(f"  Avg steps (all):       {baseline['avg_steps']:.2f}")
    print(f"  Avg steps (success):   {baseline['avg_steps_success']:.2f}")
    print(f"  Avg steps (failure):   {baseline['avg_steps_failure']:.2f}")

    print("\n  Failure distribution:")
    for category, count in baseline["failure_distribution"].items():
        print(f"    {category}: {count:,}")

    print("\n  Exit status counts:")
    for status, count in sorted(baseline["exit_status_counts"].items(), key=lambda x: -x[1]):
        print(f"    {status or '(empty)'}: {count:,}")

    print("\n  Per-model breakdown:")
    for model, stats in sorted(baseline["model_stats"].items(), key=lambda x: -x[1]["total"]):
        print(
            f"    {model}: {stats['total']:,} traces, "
            f"{stats['success']:,} success, "
            f"{stats['success_rate']:.2%} rate"
        )

    print("\n" + "=" * 60)
    print("Phase 2 complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
