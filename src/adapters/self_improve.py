"""Self-improvement loop — Trashbot learns from its own ClawBench failures.

Closed loop:
  1. Fetch Trashbot's own failed runs from ClawBench
  2. Normalize traces into failed_traces/self/
  3. Run the meta-harness to classify failures and match rules
  4. Feed unmatched failures to learn-from-traces for new rule extraction
  5. Update CLAUDE.md with new rules
  6. (Optional) Re-submit to ClawBench with improved rules

Usage:
    # Pull own failures and analyze
    python -m src.adapters.self_improve --api-url http://localhost:8080 --agent-id ag_xxx --api-key sk_xxx

    # From local artifacts (offline)
    python -m src.adapters.self_improve --local /path/to/artifacts/

    # Just run the analysis on already-fetched traces
    python -m src.adapters.self_improve --analyze-only
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SELF_TRACES_DIR = PROJECT_ROOT / "failed_traces" / "self"
DEMO_OUTPUT_DIR = PROJECT_ROOT / "demo_output" / "self"
CLAUDE_MD = PROJECT_ROOT / "CLAUDE.md"


def fetch_own_failures(api_url: str, agent_id: str, api_key: str,
                        max_score: float = 80.0, limit: int = 20) -> list[dict]:
    """Fetch this agent's own failed runs from ClawBench."""
    from src.adapters.clawbench import fetch_failed_runs

    import httpx
    headers = {"Authorization": f"Bearer {agent_id}::{api_key}"}

    # Fetch runs filtered to this agent
    url = f"{api_url.rstrip('/')}/api/v1/runs"
    params = {"agent_id": agent_id, "limit": limit * 3}
    resp = httpx.get(url, params=params, headers=headers, timeout=30)
    resp.raise_for_status()
    runs = resp.json()

    if isinstance(runs, dict):
        runs = runs.get("runs", runs.get("data", []))

    # Filter to failures
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


def analyze_self_traces() -> dict:
    """Run the harness on self-traces and identify unmatched failures."""
    sys.path.insert(0, str(PROJECT_ROOT / "hermes-agent"))
    from tools.trace_query_tool import run_harness

    result_text = run_harness(trace_set="self")
    print(result_text)

    # Read the summary
    summary_file = DEMO_OUTPUT_DIR / "_summary.json"
    if summary_file.exists():
        return json.load(open(summary_file))
    return {}


def find_unmatched_failures(summary: dict) -> list[str]:
    """Find instance_ids where no rule matched (candidates for new rules)."""
    unmatched = []
    for r in summary.get("results", []):
        if not r.get("rules_applied"):
            unmatched.append(r["instance_id"])
    return unmatched


def append_rules_to_claude_md(new_rules: list[dict]):
    """Append newly extracted rules to CLAUDE.md."""
    if not new_rules:
        return

    content = CLAUDE_MD.read_text() if CLAUDE_MD.exists() else ""

    # Find the last numbered rule
    import re
    existing_numbers = re.findall(r"^(\d+)\.", content, re.MULTILINE)
    next_num = max(int(n) for n in existing_numbers) + 1 if existing_numbers else 1

    new_lines = []
    for rule in new_rules:
        new_lines.append(
            f"\n{next_num}. **{rule['name']}**: {rule['description']}\n"
        )
        next_num += 1

    content += "\n".join(new_lines)
    CLAUDE_MD.write_text(content)
    print(f"Added {len(new_rules)} new rules to CLAUDE.md")


def main():
    parser = argparse.ArgumentParser(description="Trashbot self-improvement loop")
    parser.add_argument("--api-url", help="ClawBench API URL")
    parser.add_argument("--agent-id", help="Trashbot's agent ID on ClawBench")
    parser.add_argument("--api-key", help="Trashbot's API key")
    parser.add_argument("--local", help="Local artifacts directory")
    parser.add_argument("--analyze-only", action="store_true",
                        help="Skip fetching, just analyze existing self traces")
    parser.add_argument("--max-score", type=float, default=80.0)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    if not args.analyze_only:
        # Step 1: Fetch own failures
        if args.local:
            from src.adapters.clawbench import load_local_outputs, export_for_harness
            runs = load_local_outputs(args.local)
            print(f"Loaded {len(runs)} local outputs")
        elif args.api_url and args.agent_id:
            runs = fetch_own_failures(
                api_url=args.api_url,
                agent_id=args.agent_id,
                api_key=args.api_key or "",
                max_score=args.max_score,
                limit=args.limit,
            )
            print(f"Fetched {len(runs)} failed runs")
        else:
            parser.error("Provide --api-url + --agent-id, --local, or --analyze-only")

        # Step 2: Export to failed_traces/self/
        from src.adapters.clawbench import export_for_harness
        SELF_TRACES_DIR.mkdir(parents=True, exist_ok=True)
        count = export_for_harness(runs, SELF_TRACES_DIR)
        print(f"Exported {count} traces to {SELF_TRACES_DIR}/")

    # Step 3: Run the harness
    print("\n--- Running meta-harness on self traces ---\n")
    summary = analyze_self_traces()

    if not summary:
        print("No results to analyze")
        return

    # Step 4: Identify gaps
    unmatched = find_unmatched_failures(summary)
    fixed = summary.get("fixed", 0)
    total = summary.get("total", 0)

    print(f"\n--- Self-Improvement Summary ---")
    print(f"Fixed by existing rules: {fixed}/{total}")
    print(f"Unmatched (need new rules): {len(unmatched)}")

    if unmatched:
        print(f"\nUnmatched instance_ids:")
        for uid in unmatched:
            print(f"  {uid}")
        print(f"\nNext step: run learn-from-traces on these to extract new rules.")
        print(f"  /learn-from-traces  (in Claude Code)")
        print(f"  Then re-run: python -m src.adapters.self_improve --analyze-only")


if __name__ == "__main__":
    main()
