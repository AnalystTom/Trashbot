"""
Meta-Harness Demo Loop

Automated pipeline that:
1. Loads each of the 10 failed trace sets
2. Reads intervention rules from agents.md
3. Classifies the failure from the trajectory
4. Feeds the issue + rules + failure analysis to an agent
5. Compares the agent's proposed fix to the known passing patch
6. Reports before/after metrics

Usage:
    python run_demo_loop.py                    # Run all 10
    python run_demo_loop.py --limit 3          # Run first 3 only
    python run_demo_loop.py --dry-run          # Show what would run without calling agent
    python run_demo_loop.py --output results/  # Custom output dir
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from difflib import SequenceMatcher

TRACES_DIR = Path(__file__).parent / "failed_traces" / "10_traces_to_fix"
AGENTS_MD = Path(__file__).parent / "agents.md"
DEFAULT_OUTPUT = Path(__file__).parent / "demo_output"


def load_rules() -> str:
    """Load intervention rules from agents.md."""
    if AGENTS_MD.exists():
        return AGENTS_MD.read_text()
    return "(no rules loaded — agents.md not found)"


def classify_failure(trace: dict) -> dict:
    """Classify a single failed trace using heuristics."""
    traj = trace.get("trajectory", [])
    ai_texts = [s["text"] for s in traj if s["role"] == "ai"]
    user_texts = [s["text"] for s in traj if s["role"] == "user"]
    all_text = " ".join(ai_texts + user_texts).lower()

    # Looping
    commands = []
    for t in ai_texts:
        commands.extend(re.findall(r"`{3}\n?(.*?)\n?`{3}", t, re.DOTALL))
    cmd_counts = Counter(commands)
    is_looping = any(c >= 3 for c in cmd_counts.values())

    # Test usage
    test_kw = ["pytest", "python -m test", "python -m pytest", "test_",
                "unittest", "run_tests", "make test", "tox"]
    ran_tests = any(kw in all_text for kw in test_kw)

    edit_syntax_err = "your proposed edit has introduced new syntax error" in all_text
    has_patch = bool(trace.get("patch", "").strip())

    signals = []
    if is_looping:
        signals.append("LOOPING")
    if edit_syntax_err:
        signals.append("BAD_PATCH")
    if not ran_tests:
        signals.append("NO_TEST_USAGE")
    if not has_patch:
        signals.append("NO_PATCH")

    # Determine primary failure type
    if not has_patch:
        primary = "NO_PATCH"
    elif is_looping:
        primary = "LOOPING"
    elif edit_syntax_err:
        primary = "BAD_PATCH"
    elif not ran_tests:
        primary = "NO_TEST_USAGE"
    else:
        primary = "WRONG_FIX"

    return {
        "primary_failure": primary,
        "signals": signals,
        "is_looping": is_looping,
        "ran_tests": ran_tests,
        "edit_syntax_errors": edit_syntax_err,
        "has_patch": has_patch,
    }


def extract_issue_text(trace: dict) -> str:
    """Extract the issue description from the trajectory."""
    for step in trace.get("trajectory", []):
        if step["role"] == "user" and "ISSUE:" in step["text"]:
            text = step["text"]
            start = text.find("ISSUE:")
            end = text.find("INSTRUCTIONS:", start)
            if end == -1:
                end = start + 3000
            return text[start:end].strip()
    return trace.get("issue_text", "")


def extract_agent_actions(trace: dict) -> list[str]:
    """Extract the sequence of commands the agent tried."""
    actions = []
    for step in trace.get("trajectory", []):
        if step["role"] == "ai":
            cmds = re.findall(r"`{3}\n?(.*?)\n?`{3}", step["text"], re.DOTALL)
            actions.extend(cmds)
    return actions


def patch_similarity(patch_a: str, patch_b: str) -> float:
    """Compute similarity between two patches (0-1)."""
    if not patch_a or not patch_b:
        return 0.0
    return SequenceMatcher(None, patch_a.strip(), patch_b.strip()).ratio()


def build_agent_prompt(issue_text: str, failure_analysis: dict,
                       failed_patch: str, rules: str) -> str:
    """Build the prompt for the agent to generate a corrected fix."""
    return f"""You are a meta-harness that improves coding agent performance.

## Rules and Intervention Guidelines
{rules}

## Task
A coding agent attempted to fix the following issue but FAILED. Analyze what went wrong and produce the CORRECT fix.

## Issue
{issue_text}

## What the agent did wrong
- Primary failure: {failure_analysis['primary_failure']}
- Failure signals: {', '.join(failure_analysis['signals']) or 'WRONG_FIX (submitted incorrect patch)'}

## The agent's INCORRECT patch
```diff
{failed_patch}
```

## Your job
1. Explain what the agent got wrong (1-2 sentences)
2. Produce the CORRECT patch as a diff

Respond in this format:
ANALYSIS: <what went wrong>
CORRECT_PATCH:
```diff
<your corrected patch>
```
"""


def run_demo_loop(limit: int | None = None, dry_run: bool = False,
                  output_dir: Path = DEFAULT_OUTPUT):
    """Run the full demo loop across all 10 questions."""
    output_dir.mkdir(exist_ok=True)

    rules = load_rules()
    print(f"Loaded rules from agents.md ({len(rules)} chars)")
    print()

    trace_files = sorted(TRACES_DIR.glob("*.json"))
    trace_files = [f for f in trace_files if f.name != "_summary.json"]
    if limit:
        trace_files = trace_files[:limit]

    results = []

    for i, trace_file in enumerate(trace_files):
        data = json.load(open(trace_file))
        iid = data["instance_id"]
        failed_traces = data["failed_traces"]
        passing_trace = data.get("passing_trace")
        passing_patch = passing_trace["patch"] if passing_trace else ""

        print(f"{'='*70}")
        print(f"[{i+1}/{len(trace_files)}] {iid}")
        print(f"{'='*70}")

        # Use the first failed trace
        trace = failed_traces[0]
        issue_text = extract_issue_text(trace)
        failure = classify_failure(trace)
        actions = extract_agent_actions(trace)

        print(f"  Issue: {issue_text[:120]}...")
        print(f"  Failure: {failure['primary_failure']} | signals: {failure['signals']}")
        print(f"  Agent actions: {len(actions)} commands")
        print(f"  Failed patch similarity to correct: {patch_similarity(trace['patch'], passing_patch):.1%}")

        # Build prompt
        prompt = build_agent_prompt(issue_text, failure, trace["patch"], rules)

        if dry_run:
            print(f"  [DRY RUN] Would send {len(prompt)} char prompt to agent")
            print(f"  Correct patch available: {bool(passing_patch)}")
            result = {
                "instance_id": iid,
                "failure_type": failure["primary_failure"],
                "signals": failure["signals"],
                "agent_steps": trace["steps"],
                "agent_actions": len(actions),
                "failed_patch_similarity": round(patch_similarity(trace["patch"], passing_patch), 3),
                "status": "dry_run",
            }
        else:
            # Call hermes-agent with the prompt
            import subprocess
            print(f"  Sending to agent...")
            start = time.time()
            try:
                proc = subprocess.run(
                    ["hermes", "chat", "-q", prompt, "-t", "file,terminal",
                     "--max-turns", "3", "-Q"],
                    capture_output=True, text=True, timeout=120,
                    cwd=str(Path(__file__).parent),
                    env={**__import__("os").environ,
                         "PATH": str(Path(__file__).parent / ".venv" / "bin")
                               + ":" + __import__("os").environ.get("PATH", "")},
                )
                agent_response = proc.stdout + proc.stderr
            except subprocess.TimeoutExpired:
                agent_response = "(timed out)"
            except Exception as e:
                agent_response = f"(error: {e})"
            elapsed = time.time() - start

            # Extract corrected patch from response
            corrected_patch = ""
            diff_match = re.search(r"```diff\n(.*?)```", agent_response, re.DOTALL)
            if diff_match:
                corrected_patch = diff_match.group(1).strip()

            corrected_similarity = patch_similarity(corrected_patch, passing_patch)

            print(f"  Agent responded in {elapsed:.1f}s")
            print(f"  Corrected patch similarity to correct: {corrected_similarity:.1%}")
            print(f"  Improvement: {corrected_similarity - patch_similarity(trace['patch'], passing_patch):+.1%}")

            result = {
                "instance_id": iid,
                "failure_type": failure["primary_failure"],
                "signals": failure["signals"],
                "agent_steps": trace["steps"],
                "failed_patch": trace["patch"],
                "failed_patch_similarity": round(patch_similarity(trace["patch"], passing_patch), 3),
                "corrected_patch": corrected_patch,
                "corrected_similarity": round(corrected_similarity, 3),
                "passing_patch": passing_patch,
                "improvement": round(corrected_similarity - patch_similarity(trace["patch"], passing_patch), 3),
                "agent_response": agent_response[:3000],
                "elapsed_seconds": round(elapsed, 1),
                "status": "completed",
            }

        results.append(result)

        # Save individual result
        safe_name = iid.replace("/", "__")
        with open(output_dir / f"{safe_name}.json", "w") as f:
            json.dump(result, f, indent=2)

        print()

    # Summary report
    print(f"\n{'='*70}")
    print("DEMO SUMMARY")
    print(f"{'='*70}")

    completed = [r for r in results if r["status"] == "completed"]
    if completed:
        avg_before = sum(r["failed_patch_similarity"] for r in completed) / len(completed)
        avg_after = sum(r["corrected_similarity"] for r in completed) / len(completed)
        avg_improvement = sum(r["improvement"] for r in completed) / len(completed)
        improved = sum(1 for r in completed if r["improvement"] > 0)

        print(f"  Traces processed: {len(completed)}")
        print(f"  Avg similarity BEFORE: {avg_before:.1%}")
        print(f"  Avg similarity AFTER:  {avg_after:.1%}")
        print(f"  Avg improvement:       {avg_improvement:+.1%}")
        print(f"  Traces improved:       {improved}/{len(completed)}")

        summary = {
            "total": len(completed),
            "avg_similarity_before": round(avg_before, 3),
            "avg_similarity_after": round(avg_after, 3),
            "avg_improvement": round(avg_improvement, 3),
            "traces_improved": improved,
            "failure_types": dict(Counter(r["failure_type"] for r in completed)),
        }
    else:
        summary = {"total": len(results), "status": "dry_run"}
        for r in results:
            print(f"  {r['instance_id']:50s} {r['failure_type']:12s} sim={r['failed_patch_similarity']:.1%}")

    with open(output_dir / "_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nResults saved to {output_dir}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Meta-Harness Demo Loop")
    parser.add_argument("--limit", type=int, help="Max questions to process")
    parser.add_argument("--dry-run", action="store_true", help="Classify only, don't call agent")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT), help="Output directory")
    args = parser.parse_args()

    run_demo_loop(limit=args.limit, dry_run=args.dry_run, output_dir=Path(args.output))
