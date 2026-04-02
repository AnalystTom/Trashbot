"""Schema validation and data profiling for normalized traces."""

from __future__ import annotations

from collections import Counter
from typing import Any


REQUIRED_FIELDS = ["instance_id", "success_label", "trace_steps", "step_count", "exit_status"]


def validate_row(row: dict[str, Any]) -> list[str]:
    """Return list of validation errors for a normalized row. Empty = valid."""
    errors = []
    for field in REQUIRED_FIELDS:
        if field not in row:
            errors.append(f"missing field: {field}")

    if not isinstance(row.get("success_label"), bool):
        errors.append("success_label is not bool")

    steps = row.get("trace_steps", [])
    if not steps or len(steps) == 0:
        errors.append("empty trajectory")

    if row.get("step_count", 0) != len(steps):
        errors.append("step_count mismatch")

    return errors


def validate_dataset(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate all rows and return summary."""
    total = len(rows)
    valid = 0
    invalid = 0
    error_counts: Counter = Counter()

    for row in rows:
        errs = validate_row(row)
        if errs:
            invalid += 1
            for e in errs:
                error_counts[e] += 1
        else:
            valid += 1

    return {
        "total_rows": total,
        "valid": valid,
        "invalid": invalid,
        "error_counts": dict(error_counts),
    }


def data_profile(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Produce a data profile artifact."""
    total = len(rows)
    if total == 0:
        return {"total": 0}

    success_count = sum(1 for r in rows if r["success_label"])
    fail_count = total - success_count
    step_counts = [r["step_count"] for r in rows]
    models = Counter(r.get("model", "unknown") for r in rows)
    exit_statuses = Counter(r["exit_status"] for r in rows)

    missing_patch = sum(1 for r in rows if not r.get("patch_text"))
    missing_eval = sum(1 for r in rows if not r.get("eval_logs"))

    return {
        "total_rows": total,
        "success_count": success_count,
        "fail_count": fail_count,
        "success_rate": success_count / total,
        "avg_steps": sum(step_counts) / total,
        "min_steps": min(step_counts),
        "max_steps": max(step_counts),
        "models": dict(models.most_common()),
        "exit_statuses": dict(exit_statuses.most_common()),
        "missing_patch_count": missing_patch,
        "missing_eval_logs_count": missing_eval,
    }
