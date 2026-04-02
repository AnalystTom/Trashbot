"""Dataset loading and schema normalization for SWE-agent trajectories."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from datasets import load_dataset


DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "swe-agent-trajectories"
DEFAULT_HF_DATASET = "nebius/SWE-agent-trajectories"


def load_local(limit: int | None = None):
    """Load from local parquet files."""
    parquet_files = sorted(str(p) for p in (DATA_DIR / "data").glob("*.parquet"))
    if not parquet_files:
        raise FileNotFoundError(f"No parquet files in {DATA_DIR / 'data'}")
    ds = load_dataset("parquet", data_files=parquet_files, split="train")
    if limit:
        ds = ds.select(range(min(limit, len(ds))))
    return ds


def load_hf(split: str = "train", streaming: bool = True, limit: int | None = None):
    """Load from HuggingFace hub."""
    ds = load_dataset(DEFAULT_HF_DATASET, split=split, streaming=streaming)
    if limit and not streaming:
        ds = ds.select(range(min(limit, len(ds))))
    return ds


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize a raw dataset row into our internal schema.

    Maps:
      target -> success_label
      trajectory -> trace_steps (list of {role, text} dicts)
      generated_patch -> patch_text
    """
    # Extract trace steps from trajectory
    raw_traj = row.get("trajectory", []) or []
    trace_steps = []
    for step in raw_traj:
        trace_steps.append({
            "role": step.get("role", "unknown"),
            "text": step.get("text") or "",
            "mask": step.get("mask", False),
        })

    return {
        "instance_id": row.get("instance_id", ""),
        "model": row.get("model_name", "unknown"),
        "success_label": bool(row.get("target", False)),
        "trace_steps": trace_steps,
        "step_count": len(trace_steps),
        "exit_status": row.get("exit_status", ""),
        "patch_text": row.get("generated_patch", ""),
        "eval_logs": row.get("eval_logs", ""),
    }


def load_normalized(limit: int | None = None, source: str = "local") -> list[dict[str, Any]]:
    """Load and normalize the full dataset into a list of dicts."""
    if source == "local":
        ds = load_local(limit=limit)
    else:
        ds = load_hf(limit=limit, streaming=False)

    return [normalize_row(row) for row in ds]
