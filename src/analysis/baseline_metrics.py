"""Baseline KPI computation for SWE-agent trajectories."""

from __future__ import annotations

from collections import Counter
from typing import Any


def compute_baseline(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute baseline (BEFORE) KPIs from normalized rows."""
    total = len(rows)
    if total == 0:
        return {"error": "no data"}

    successes = [r for r in rows if r["success_label"]]
    failures = [r for r in rows if not r["success_label"]]

    success_rate = len(successes) / total
    avg_steps = sum(r["step_count"] for r in rows) / total
    avg_steps_success = (
        sum(r["step_count"] for r in successes) / len(successes)
        if successes else 0.0
    )
    avg_steps_failure = (
        sum(r["step_count"] for r in failures) / len(failures)
        if failures else 0.0
    )

    # Failure distribution (placeholder UNKNOWN before classifier runs)
    failure_distribution = {
        "UNKNOWN": len(failures),
    }

    # Per-model breakdown
    model_stats = {}
    by_model: dict[str, list] = {}
    for r in rows:
        by_model.setdefault(r.get("model", "unknown"), []).append(r)
    for model, model_rows in by_model.items():
        s = sum(1 for r in model_rows if r["success_label"])
        model_stats[model] = {
            "total": len(model_rows),
            "success": s,
            "success_rate": s / len(model_rows),
        }

    # Exit status breakdown
    exit_status_counts = dict(Counter(r["exit_status"] for r in rows))

    return {
        "total_traces": total,
        "success_count": len(successes),
        "failure_count": len(failures),
        "success_rate": round(success_rate, 4),
        "avg_steps": round(avg_steps, 2),
        "avg_steps_success": round(avg_steps_success, 2),
        "avg_steps_failure": round(avg_steps_failure, 2),
        "failure_distribution": failure_distribution,
        "model_stats": model_stats,
        "exit_status_counts": exit_status_counts,
    }
