"""Query SWE-agent trajectory data by instance_id, model, or failure pattern.

Usage:
    # Look up a specific instance
    python query_traces.py --id django__django-11099

    # Look up with a specific model
    python query_traces.py --id django__django-11099 --model swe-agent-llama-8b

    # Search by repo name (partial match)
    python query_traces.py --repo scikit-learn

    # List all failed traces for a repo
    python query_traces.py --repo django --failed-only

    # Show full trajectory for a specific instance+model
    python query_traces.py --id django__django-11099 --model swe-agent-llama-70b --show-trajectory

    # Show the patch
    python query_traces.py --id django__django-11099 --show-patch

    # Export matching traces to JSON
    python query_traces.py --repo flask --failed-only --export results.json

    # Query from HuggingFace hub instead of local parquet
    python query_traces.py --id django__django-11099 --source hf
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from datasets import load_dataset


DATA_DIR = Path(__file__).parent / "data" / "swe-agent-trajectories"
HF_DATASET = "nebius/SWE-agent-trajectories"


def load_ds(source: str = "local"):
    if source == "local":
        parquet_files = sorted(str(p) for p in (DATA_DIR / "data").glob("*.parquet"))
        if not parquet_files:
            raise FileNotFoundError(f"No parquet files in {DATA_DIR / 'data'}")
        return load_dataset("parquet", data_files=parquet_files, split="train")
    else:
        return load_dataset(HF_DATASET, split="train", streaming=False)


def query(ds, instance_id=None, repo=None, model=None, failed_only=False, limit=None):
    """Filter dataset rows matching criteria."""
    results = []
    for row in ds:
        if instance_id and row["instance_id"] != instance_id:
            continue
        if repo and repo.lower() not in row["instance_id"].lower():
            continue
        if model and row["model_name"] != model:
            continue
        if failed_only and row["target"]:
            continue
        results.append(row)
        if limit and len(results) >= limit:
            break
    return results


def print_summary(row):
    """Print a one-line summary of a trace."""
    traj_len = len(row["trajectory"]) if row["trajectory"] else 0
    patch_len = len(row["generated_patch"] or "")
    status = "PASS" if row["target"] else "FAIL"
    print(f"  [{status}] {row['instance_id']:55s} model={row['model_name']:25s} "
          f"steps={traj_len:3d}  exit={row['exit_status']:30s} patch={patch_len}ch")


def print_trajectory(row):
    """Print the full trajectory of a trace."""
    print(f"\n{'='*80}")
    print(f"Instance: {row['instance_id']}")
    print(f"Model:    {row['model_name']}")
    print(f"Target:   {row['target']}")
    print(f"Exit:     {row['exit_status']}")
    print(f"{'='*80}\n")

    for i, step in enumerate(row["trajectory"]):
        role = step.get("role", "?")
        text = step.get("text") or ""
        if role == "system":
            # Skip system prompt (too long)
            print(f"--- Step {i}: [{role}] (system prompt, {len(text)} chars) ---")
            continue
        print(f"--- Step {i}: [{role}] ---")
        # Truncate very long outputs
        if len(text) > 2000:
            print(text[:2000])
            print(f"\n... ({len(text) - 2000} more chars truncated)")
        else:
            print(text)
        print()


def print_patch(row):
    """Print the generated patch."""
    patch = row.get("generated_patch") or ""
    if not patch.strip():
        print("  (no patch generated)")
    else:
        print(patch)


def main():
    parser = argparse.ArgumentParser(description="Query SWE-agent trajectory traces")
    parser.add_argument("--id", dest="instance_id", help="Exact instance_id to look up")
    parser.add_argument("--repo", help="Partial repo name match (e.g. 'django', 'scikit-learn')")
    parser.add_argument("--model", help="Filter by model name (e.g. 'swe-agent-llama-8b')")
    parser.add_argument("--failed-only", action="store_true", help="Only show failed traces")
    parser.add_argument("--passed-only", action="store_true", help="Only show passed traces")
    parser.add_argument("--show-trajectory", action="store_true", help="Print full trajectory")
    parser.add_argument("--show-patch", action="store_true", help="Print generated patch")
    parser.add_argument("--show-eval", action="store_true", help="Print eval logs")
    parser.add_argument("--limit", type=int, default=50, help="Max results (default 50)")
    parser.add_argument("--export", help="Export matches to JSON file")
    parser.add_argument("--source", choices=["local", "hf"], default="local",
                        help="Data source: local parquet or HuggingFace hub")
    parser.add_argument("--list-instances", action="store_true",
                        help="Just list unique instance_ids matching filters")
    args = parser.parse_args()

    if not any([args.instance_id, args.repo, args.list_instances]):
        parser.error("Provide --id, --repo, or --list-instances")

    print(f"Loading dataset ({args.source})...", file=sys.stderr)
    ds = load_ds(args.source)

    if args.passed_only:
        results = query(ds, args.instance_id, args.repo, args.model,
                        failed_only=False, limit=None)
        results = [r for r in results if r["target"]][:args.limit]
    else:
        results = query(ds, args.instance_id, args.repo, args.model,
                        args.failed_only, args.limit)

    if args.list_instances:
        ids = sorted(set(r["instance_id"] for r in
                         query(ds, args.instance_id, args.repo, args.model, args.failed_only, limit=None)))
        print(f"Found {len(ids)} unique instance_ids:")
        for iid in ids:
            print(f"  {iid}")
        return

    print(f"\nFound {len(results)} matching traces:\n")

    for row in results:
        print_summary(row)

        if args.show_trajectory:
            print_trajectory(row)

        if args.show_patch:
            print(f"\n  --- Patch ---")
            print_patch(row)

        if args.show_eval:
            print(f"\n  --- Eval Logs ---")
            logs = row.get("eval_logs") or "(none)"
            print(logs[:3000] if len(logs) > 3000 else logs)

    if args.export:
        export_data = []
        for row in results:
            export_data.append({
                "instance_id": row["instance_id"],
                "model_name": row["model_name"],
                "target": row["target"],
                "exit_status": row["exit_status"],
                "step_count": len(row["trajectory"]),
                "generated_patch": row.get("generated_patch", ""),
                "trajectory": row["trajectory"],
            })
        with open(args.export, "w") as f:
            json.dump(export_data, f, indent=2)
        print(f"\nExported {len(export_data)} traces to {args.export}")


if __name__ == "__main__":
    main()
