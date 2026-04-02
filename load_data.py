"""Quick script to load and explore SWE-agent trajectory data."""

import json
from pathlib import Path

from datasets import load_dataset


DATA_DIR = Path(__file__).parent / "data" / "swe-agent-trajectories"


def load_local_parquet():
    """Load the local parquet files into a dataset."""
    parquet_files = sorted(str(p) for p in (DATA_DIR / "data").glob("*.parquet"))
    if not parquet_files:
        raise FileNotFoundError(f"No parquet files found in {DATA_DIR / 'data'}")
    ds = load_dataset("parquet", data_files=parquet_files, split="train")
    return ds


def summarize(ds):
    """Print a summary of the dataset."""
    print(f"Total rows: {len(ds)}")
    print(f"Columns: {ds.column_names}")
    print(f"Features: {ds.features}")
    print()

    # Show first row keys and a preview
    row = ds[0]
    print("=== First row preview ===")
    for key, val in row.items():
        if isinstance(val, str) and len(val) > 200:
            print(f"  {key}: ({len(val)} chars) {val[:200]}...")
        elif isinstance(val, list) and len(val) > 3:
            print(f"  {key}: ({len(val)} items) {val[:2]}...")
        else:
            print(f"  {key}: {val}")

    # Basic stats
    print()
    if "target" in ds.column_names:
        targets = ds["target"]
        print(f"Pass rate (target=True): {sum(targets)}/{len(targets)} ({sum(targets)/len(targets)*100:.1f}%)")

    if "model_name" in ds.column_names:
        from collections import Counter
        model_counts = Counter(ds["model_name"])
        print(f"\nModels ({len(model_counts)} unique):")
        for model, count in model_counts.most_common(10):
            print(f"  {model}: {count}")

    if "exit_status" in ds.column_names:
        from collections import Counter
        status_counts = Counter(ds["exit_status"])
        print(f"\nExit statuses:")
        for status, count in status_counts.most_common():
            print(f"  {status}: {count}")


if __name__ == "__main__":
    print("Loading local parquet data...")
    ds = load_local_parquet()
    summarize(ds)
