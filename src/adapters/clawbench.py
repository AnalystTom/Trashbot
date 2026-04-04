"""ClawBench adapter — pulls failed runs and normalizes traces for the self-learning loop.

Connects to ClawBench's API to fetch completed runs with low scores,
converts the clawbench.trace.v1 format into Trashbot's internal trace
format, and exports them for the meta-harness to process.

Usage:
    # Fetch failed runs from ClawBench API
    python -m src.adapters.clawbench --api-url http://localhost:8080 --benchmark-id bm_xxx --export failed_traces/clawbench/

    # Fetch from local output JSON files (offline mode)
    python -m src.adapters.clawbench --local /path/to/clawbench/artifacts/ --export failed_traces/clawbench/

    # Then run the harness:
    # trace_query(action="run_harness", trace_set="clawbench")
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# ClawBench trace.v1 → Trashbot internal format
# ---------------------------------------------------------------------------

def normalize_clawbench_step(step: dict) -> dict:
    """Convert a clawbench.trace.v1 step to Trashbot's {role, text} format."""
    kind = step.get("kind", "trace")
    text = step.get("text", "")
    reasoning = step.get("reasoning", "")
    error = step.get("error", "")
    tool = step.get("tool", "")
    tool_result = step.get("tool_result", "")

    if kind == "reasoning" or reasoning:
        role = "ai"
        content = reasoning or text
    elif kind == "tool":
        role = "ai"
        params = json.dumps(step.get("tool_parameters", {}), indent=2) if step.get("tool_parameters") else ""
        content = f"Tool call: {tool}\n{params}" if tool else text
        if tool_result:
            content += f"\nResult: {tool_result}"
    elif kind == "output":
        role = "user"
        content = text
    elif error:
        role = "user"
        content = f"ERROR: {error}\n{text}" if text else f"ERROR: {error}"
    else:
        role = "user"
        content = text

    return {
        "step": step.get("index", 0),
        "role": role,
        "text": content,
    }


def normalize_clawbench_run(run: dict) -> dict | None:
    """Convert a ClawBench run/output into Trashbot's trace file format.

    Expects the run to have:
      - output.content.trace (clawbench.trace.v1)
      - output.content.summary (scores)
      - output.content.mode (benchmark format)
      - run metadata (benchmark_id, agent_id, etc.)
    """
    output = run.get("output", run)  # Handle both run-wrapping and direct output
    content = output.get("content", {})
    trace = content.get("trace", {})
    summary = content.get("summary", {})
    status = output.get("status", run.get("status", ""))

    if not trace or not trace.get("steps"):
        return None

    # Map clawbench steps to internal format
    steps = trace.get("steps", [])
    trajectory = [normalize_clawbench_step(s) for s in steps]

    # Determine success
    overall_score = summary.get("overall_score", 0)
    is_success = overall_score >= 80 and status == "success"

    # Extract instance_id
    benchmark_id = run.get("benchmark_id", output.get("benchmark_id", "unknown"))
    run_id = run.get("id", run.get("run_id", output.get("id", "unknown")))
    agent_id = run.get("agent_id", output.get("agent_id", "unknown"))
    mode = content.get("mode", "unknown")

    # Build task-level details if available
    tasks = content.get("tasks", [])
    task_patches = {}
    for task in tasks:
        tid = task.get("task_id", task.get("id", ""))
        if tid:
            task_patches[tid] = {
                "patch": task.get("patch", task.get("generated_patch", "")),
                "score": task.get("score", 0),
                "status": task.get("status", ""),
            }

    instance_id = f"{mode}__{benchmark_id}__{run_id}"

    return {
        "instance_id": instance_id,
        "benchmark_id": benchmark_id,
        "run_id": run_id,
        "agent_id": agent_id,
        "mode": mode,
        "success_label": is_success,
        "overall_score": overall_score,
        "trace_steps": trajectory,
        "step_count": len(trajectory),
        "tool_count": trace.get("tool_count", 0),
        "error_count": trace.get("error_step_count", 0),
        "tools_used": trace.get("tools_used", []),
        "summary": summary,
        "tasks": task_patches,
        "status": status,
    }


def to_trashbot_trace_file(normalized: dict, passing_patch: str = "") -> dict:
    """Convert normalized ClawBench run into the trace file format
    expected by failed_traces/*/X.json (same format as SWE-bench traces).
    """
    # Build a "failed_traces" entry compatible with run_harness
    issue_text = f"Benchmark: {normalized['mode']} (ID: {normalized['benchmark_id']})\n"
    issue_text += f"Agent: {normalized['agent_id']}\n"
    issue_text += f"Score: {normalized['overall_score']}\n"
    if normalized.get("summary"):
        for k, v in normalized["summary"].items():
            if isinstance(v, (int, float, str, bool)):
                issue_text += f"  {k}: {v}\n"

    # Extract any patches from tasks
    patch = ""
    for tid, task_data in normalized.get("tasks", {}).items():
        if task_data.get("patch"):
            patch += f"--- Task: {tid} ---\n{task_data['patch']}\n"

    return {
        "instance_id": normalized["instance_id"],
        "total_attempts": 1,
        "passed_count": 1 if normalized["success_label"] else 0,
        "failed_count": 0 if normalized["success_label"] else 1,
        "issue_text": issue_text,
        "failed_traces": [{
            "instance_id": normalized["instance_id"],
            "model": normalized["agent_id"],
            "steps": normalized["step_count"],
            "exit_status": normalized["status"],
            "patch": patch,
            "issue_text": issue_text,
            "trajectory": normalized["trace_steps"],
        }],
        "passing_trace": {
            "model": "reference",
            "steps": 0,
            "patch": passing_patch,
        } if passing_patch else None,
    }


# ---------------------------------------------------------------------------
# API fetching
# ---------------------------------------------------------------------------

def fetch_failed_runs(api_url: str, benchmark_id: str = "",
                       api_key: str = "", max_score: float = 80.0,
                       limit: int = 10) -> list[dict]:
    """Fetch failed/low-scoring runs from ClawBench API."""
    import httpx

    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    url = f"{api_url.rstrip('/')}/api/v1/runs"
    params = {"limit": limit * 3}  # Fetch more, filter locally
    if benchmark_id:
        params["benchmark_id"] = benchmark_id

    resp = httpx.get(url, params=params, headers=headers, timeout=30)
    resp.raise_for_status()
    runs = resp.json()

    if isinstance(runs, dict):
        runs = runs.get("runs", runs.get("data", []))

    # Filter to failed/low-scoring
    failed = []
    for run in runs:
        output = run.get("output", {})
        content = output.get("content", {}) if output else {}
        summary = content.get("summary", {}) if content else {}
        score = summary.get("overall_score", 0) if summary else 0
        status = run.get("status", output.get("status", ""))

        if score < max_score or status in ("error", "failed"):
            failed.append(run)
            if len(failed) >= limit:
                break

    return failed


def load_local_outputs(artifacts_dir: str) -> list[dict]:
    """Load output JSON files from a local ClawBench artifacts directory."""
    p = Path(artifacts_dir)
    outputs = []
    for f in sorted(p.rglob("*.json")):
        try:
            data = json.load(open(f))
            # Could be a run, output, or evidence file
            if isinstance(data, dict) and ("content" in data or "output" in data):
                outputs.append(data)
        except (json.JSONDecodeError, KeyError):
            continue
    return outputs


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_for_harness(runs: list[dict], output_dir: Path) -> int:
    """Normalize ClawBench runs and export as Trashbot trace files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    for run in runs:
        normalized = normalize_clawbench_run(run)
        if not normalized:
            continue

        trace_file = to_trashbot_trace_file(normalized)
        safe_name = normalized["instance_id"].replace("/", "__")[:200]
        with open(output_dir / f"{safe_name}.json", "w") as f:
            json.dump(trace_file, f, indent=2)
        count += 1

    return count


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="ClawBench → Trashbot trace adapter")
    parser.add_argument("--api-url", help="ClawBench API base URL")
    parser.add_argument("--benchmark-id", default="", help="Filter by benchmark ID")
    parser.add_argument("--api-key", default="", help="API key for auth")
    parser.add_argument("--local", help="Local artifacts directory (offline mode)")
    parser.add_argument("--max-score", type=float, default=80.0, help="Max score to consider as failure")
    parser.add_argument("--limit", type=int, default=10, help="Max runs to fetch")
    parser.add_argument("--export", required=True, help="Output directory for trace files")
    args = parser.parse_args()

    if args.local:
        print(f"Loading local outputs from {args.local}...")
        runs = load_local_outputs(args.local)
    elif args.api_url:
        print(f"Fetching failed runs from {args.api_url}...")
        runs = fetch_failed_runs(
            api_url=args.api_url,
            benchmark_id=args.benchmark_id,
            api_key=args.api_key,
            max_score=args.max_score,
            limit=args.limit,
        )
    else:
        parser.error("Provide --api-url or --local")

    print(f"Found {len(runs)} runs")
    output_dir = Path(args.export)
    count = export_for_harness(runs, output_dir)
    print(f"Exported {count} trace files to {output_dir}/")
    print(f"\nRun the harness with:")
    print(f"  trace_query(action='run_harness', trace_set='{output_dir.name}')")


if __name__ == "__main__":
    main()
