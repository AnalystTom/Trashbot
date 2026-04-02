#!/usr/bin/env python3
"""
Rule Extractor: Read failed traces → generate rules → save to rules.md + CLAUDE.md

Usage:
    # Generate rules from the 10 curated traces
    python scripts/generate_rules.py

    # Generate from a single trace
    python scripts/generate_rules.py --trace failed_traces/10_traces_to_fix/d3dave__cough-3.json

    # Append rules to CLAUDE.md
    python scripts/generate_rules.py --append-to CLAUDE.md

Each trace has: failed attempts + a passing attempt with the correct patch.
The tool compares what failed agents did wrong vs what the passing agent did right,
and extracts one rule per trace.
"""

import argparse
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRACES_DIR = PROJECT_ROOT / "failed_traces" / "10_traces_to_fix"
DEFAULT_OUTPUT = PROJECT_ROOT / "rules" / "rules_v1.md"


def load_trace(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def extract_agent_actions(trajectory: list) -> list:
    """Pull out what the AI agent actually did and saw."""
    actions = []
    for step in trajectory:
        role = step.get("role", "")
        text = step.get("text", "")
        if role in ("ai", "assistant") and text:
            actions.append(text)
    return actions


def compare_patches(failed_patch: str, passing_patch: str) -> dict:
    """Compare failed vs passing patch to find what was different."""
    if not failed_patch or not passing_patch:
        return {"same_file": False, "description": "missing patch"}

    def extract_files(patch):
        files = set()
        for line in patch.split("\n"):
            if line.startswith("+++ b/") or line.startswith("--- a/"):
                files.add(line.split("/", 1)[-1] if "/" in line else line)
        return files

    failed_files = extract_files(failed_patch)
    passing_files = extract_files(passing_patch)
    same_file = bool(failed_files & passing_files)

    return {
        "same_file": same_file,
        "failed_files": list(failed_files),
        "passing_files": list(passing_files),
        "wrong_file": not same_file and bool(failed_files) and bool(passing_files),
    }


def analyze_trace(trace: dict) -> dict:
    """Compare failed attempts vs the passing attempt."""
    instance_id = trace["instance_id"]
    issue_text = trace.get("issue_text", "")
    failed_traces = trace.get("failed_traces", [])
    passing_trace = trace.get("passing_trace", {})
    passing_patch = passing_trace.get("patch", "") if passing_trace else ""
    passing_steps = passing_trace.get("steps", 0) if passing_trace else 0

    failed_analyses = []
    for ft in failed_traces:
        trajectory = ft.get("trajectory", [])
        patch = ft.get("patch", "")
        ai_actions = extract_agent_actions(trajectory)

        # Compare with passing patch
        patch_comparison = compare_patches(patch, passing_patch)

        # What the agent did
        ran_tests = any("test" in a.lower() and ("run" in a.lower() or "pytest" in a.lower() or "python" in a.lower())
                        for a in ai_actions)

        used_traceback = False
        if "traceback" in issue_text.lower() or "line " in issue_text.lower():
            used_traceback = any("line" in a.lower() and ("open" in a.lower() or "goto" in a.lower())
                                 for a in ai_actions)

        read_code_first = len(ai_actions) > 1 and any(
            kw in ai_actions[0].lower() for kw in ["open", "cat", "find", "search", "look"]
        ) if ai_actions else False

        explored_multiple = sum(1 for a in ai_actions
                                if any(kw in a.lower() for kw in ["open", "find_file", "search"]))

        failed_analyses.append({
            "steps": ft.get("steps", len(trajectory)),
            "exit_status": ft.get("exit_status", ""),
            "patch": patch[:500],
            "patch_comparison": patch_comparison,
            "ran_tests": ran_tests,
            "used_traceback": used_traceback,
            "read_code_first": read_code_first,
            "explored_multiple": explored_multiple,
            "ai_actions": ai_actions,
        })

    return {
        "instance_id": instance_id,
        "issue_preview": issue_text[:300],
        "pass_rate": f"{trace.get('passed_count', 0)}/{trace.get('total_attempts', 0)}",
        "passing_patch": passing_patch[:500],
        "passing_steps": passing_steps,
        "failed_analyses": failed_analyses,
        "issue_has_traceback": "traceback" in issue_text.lower(),
    }


def generate_rule(analysis: dict, rule_number: int) -> dict:
    """Generate a rule by comparing what failed agents did vs what worked."""
    instance_id = analysis["instance_id"]
    fails = analysis["failed_analyses"]
    n = len(fails)

    # Score each failure dimension
    wrong_file_count = sum(1 for f in fails if f["patch_comparison"].get("wrong_file", False))
    no_test_count = sum(1 for f in fails if not f["ran_tests"])
    ignored_tb_count = sum(1 for f in fails if analysis["issue_has_traceback"] and not f["used_traceback"])
    shallow_count = sum(1 for f in fails if f["steps"] < 12)
    no_explore_count = sum(1 for f in fails if f["explored_multiple"] < 2)
    same_file_bad_patch = sum(1 for f in fails
                              if f["patch_comparison"].get("same_file") and f["patch"][:100] != analysis["passing_patch"][:100])

    # Rank
    scores = {
        "WRONG_FILE": wrong_file_count * 3,  # high weight — fundamental mistake
        "NO_TESTS": no_test_count * 2,
        "IGNORED_TRACEBACK": ignored_tb_count * 2.5,
        "TOO_SHALLOW": shallow_count * 1.5,
        "NO_EXPLORATION": no_explore_count * 1,
        "BAD_FIX_LOGIC": same_file_bad_patch * 2,
    }

    rules_text = {
        "WRONG_FILE": (
            "Compare your target file with the error source. If the traceback or "
            "failing test points to file X but you're editing file Y, STOP. "
            "The passing fix was in a different file than what you chose. Always "
            "verify you're in the right file before making any edit."
        ),
        "NO_TESTS": (
            "Run the test suite BEFORE and AFTER every edit. The failing test tells "
            "you what the code should do. The test output after your edit tells you "
            "if you fixed it. Submitting without running tests is guessing."
        ),
        "IGNORED_TRACEBACK": (
            "The issue contains an error traceback with a file path and line number. "
            "Go to that EXACT location first. Do not search or guess. The traceback "
            "is a direct pointer to the bug — follow it."
        ),
        "TOO_SHALLOW": (
            "Read the source code around the bug before editing. Understand what "
            "the function does, what it's supposed to return, and how it's tested. "
            "A 5-minute read saves a failed 30-step attempt."
        ),
        "NO_EXPLORATION": (
            "Explore the codebase before committing to a fix. Check related files, "
            "imports, and tests. The fix might be in a helper function, a config, "
            "or a test fixture — not where you first looked."
        ),
        "BAD_FIX_LOGIC": (
            "You found the right file but your fix was wrong. Before editing, read "
            "the passing test case to understand the EXACT expected behavior. Then "
            "write code that produces that exact output. Don't guess at the logic — "
            "let the test tell you what's correct."
        ),
    }

    # Pick the best rule for this trace (highest score)
    best = max(scores, key=scores.get)

    # If all scores are 0, pick based on trace characteristics
    if scores[best] == 0:
        if analysis["issue_has_traceback"]:
            best = "IGNORED_TRACEBACK"
        elif shallow_count > 0:
            best = "TOO_SHALLOW"
        else:
            best = "BAD_FIX_LOGIC"

    evidence_parts = []
    if wrong_file_count: evidence_parts.append(f"{wrong_file_count}/{n} edited wrong file")
    if no_test_count: evidence_parts.append(f"{no_test_count}/{n} never ran tests")
    if ignored_tb_count: evidence_parts.append(f"{ignored_tb_count}/{n} ignored traceback")
    if shallow_count: evidence_parts.append(f"{shallow_count}/{n} under 12 steps")
    if same_file_bad_patch: evidence_parts.append(f"{same_file_bad_patch}/{n} right file, wrong fix")

    return {
        "number": rule_number,
        "instance_id": instance_id,
        "failure_type": best,
        "rule": rules_text[best],
        "evidence": "; ".join(evidence_parts) if evidence_parts else f"Based on {n} failed attempts vs passing trace",
        "pass_rate": analysis["pass_rate"],
    }


def format_rules_md(rules: list) -> str:
    lines = [
        "# Rules for SWE-Agent (learned from failed traces)",
        "",
        "Extracted by comparing failed vs passing attempts on real GitHub issues.",
        "Each rule addresses a concrete failure pattern observed in the data.",
        "",
        "---",
        "",
    ]
    for r in rules:
        lines.append(f"### Rule {r['number']}: {r['failure_type']}")
        lines.append(f"")
        lines.append(f"{r['rule']}")
        lines.append(f"")
        lines.append(f"_Evidence ({r['pass_rate']} attempts passed): {r['evidence']}_")
        lines.append(f"_Source: `{r['instance_id']}`_")
        lines.append("")

    lines.append("---")
    lines.append(f"Total: {len(rules)} rules from {len(rules)} traces")
    return "\n".join(lines)


def format_for_prompt(rules: list) -> str:
    """Compact format for injecting into CLAUDE.md or agent prompt."""
    seen = {}
    for r in rules:
        if r["failure_type"] not in seen:
            seen[r["failure_type"]] = r

    lines = [
        "",
        "## Learned Rules (extracted from failed trace analysis)",
        "",
        "Follow these rules when fixing code. They come from analyzing real agent",
        "runs — what failed agents did wrong vs what passing agents did right.",
        "",
    ]
    for i, (ftype, r) in enumerate(seen.items(), 1):
        lines.append(f"{i}. **{ftype}**: {r['rule']}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Extract rules from failed traces")
    parser.add_argument("--trace", type=str, help="Single trace JSON path")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT))
    parser.add_argument("--append-to", type=str, help="Append to CLAUDE.md / AGENTS.md")
    args = parser.parse_args()

    if args.trace:
        trace_files = [Path(args.trace)]
    else:
        trace_files = sorted(TRACES_DIR.glob("*.json"))
        trace_files = [f for f in trace_files if f.name != "_summary.json"]

    print(f"Loading {len(trace_files)} trace(s)...\n")

    rules = []
    for i, path in enumerate(trace_files, 1):
        trace = load_trace(path)
        analysis = analyze_trace(trace)
        rule = generate_rule(analysis, i)
        rules.append(rule)
        print(f"[{i:2d}] {path.stem}")
        print(f"     {rule['failure_type']}: {rule['rule'][:65]}...")
        print(f"     Evidence: {rule['evidence']}")
        print()

    # Save rules
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(format_rules_md(rules))
    print(f"Saved to {out}")

    if args.append_to:
        p = Path(args.append_to)
        with open(p, "a") as f:
            f.write(format_for_prompt(rules))
        print(f"Appended to {p}")

    # Summary
    seen = {}
    for r in rules:
        if r["failure_type"] not in seen:
            seen[r["failure_type"]] = r["rule"]

    print(f"\n{'='*60}")
    print(f"  {len(seen)} unique rules from {len(rules)} traces")
    print(f"{'='*60}")
    for ftype, rule in seen.items():
        print(f"\n  [{ftype}]")
        print(f"  {rule}")
    print(f"\n{'='*60}")


if __name__ == "__main__":
    main()
