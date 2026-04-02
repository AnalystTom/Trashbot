# Trashbot

> **Built with [Cursor](https://cursor.sh)** — AI-native code editor with Agent mode.
> See [docs/CURSOR_WORKFLOW.md](docs/CURSOR_WORKFLOW.md) for the full build process.

## What is this?

A self-improving agent that learns from 80,000 real coding agent runs.
It reads traces, extracts rules, and feeds them back into the agent's prompt.

**Track:** Agent Runtime Tools — Skills, tools, and decision layers that make agents more capable.

## The Problem

AI coding agents fail **83% of the time** on real GitHub issues. Not because the model
is dumb — because the agent makes bad decisions about what to do next. It opens wrong
files, loops endlessly, writes broken syntax, and ignores test output.

## Our Solution

We analyze 80,000 real SWE-agent trajectories, compare failed vs passing attempts, and
extract plain-English rules that prevent the most common mistakes. These rules get
injected into the agent's prompt. Same model, better decisions, higher success rate.

```
traces (80K) --> rule extractor --> 10 rules --> agent prompt --> agent improves
                                                     ^                    |
                                                     |   new traces       |
                                                     +--------------------+
                                               SELF-IMPROVING LOOP
```

## Build Plan (completed in Cursor)

- [x] Load and validate 80,036 SWE-agent trajectories from HuggingFace
- [x] Compute baseline metrics (16.7% success, 83.3% failure)
- [x] Deep analysis of failure patterns (68% looping, 56% syntax errors, 56% death spiral)
- [x] Export 3,560 failed trace files with full trajectories
- [x] Curate 10 traces with both failed and passing attempts
- [x] Build rule extraction tool (`scripts/generate_rules.py`)
- [x] v1: Heuristic classifier — too generic, all traces got same rule
- [x] v2: Improved heuristics with forced variety — 5 unique rules
- [x] v3: LLM subagents (10 in parallel via Cursor) — 10 unique, specific rules
- [x] Save rules to `rules/rules_v1.md`
- [x] Inject rules into `CLAUDE.md` — self-improving loop closed
- [x] Document architecture (`docs/ARCHITECTURE.md`)
- [x] Document Cursor workflow (`docs/CURSOR_WORKFLOW.md`)

## Generated Rules (sample)

| # | Type | Rule |
|---|---|---|
| 1 | UNSAFE_VARIABLE_ACCESS | Check if variable exists before referencing loop-dependent variables |
| 2 | INCOMPLETE_FIX | When changing a method call, update BOTH name AND argument signature |
| 3 | MISSING_ERROR_HANDLING | Check key exists before dict access — don't assume |
| 4 | INDEX_MISMATCH | Append entries for ALL iterations to maintain list length parity |
| 5 | WRONG_ABSTRACTION_LEVEL | Implement checks at the API entry point, before caching |
| 7 | WRONG_DIAGNOSIS | Read errors precisely — NoneType means value is None, not key missing |
| 10 | INCOMPLETE_CLEANUP | After removing a constant, search entire codebase for usages |

Full rules: [`rules/rules_v1.md`](rules/rules_v1.md)

## Quick Start

```bash
# Generate rules from the 10 curated traces
python scripts/generate_rules.py

# Generate and inject into CLAUDE.md
python scripts/generate_rules.py --append-to CLAUDE.md

# Query any trace in the dataset
python query_traces.py --id django__django-11099 --show-trajectory
```

## Data

- **Source:** `nebius/SWE-agent-trajectories` (HuggingFace)
- **Size:** 80,036 trajectories across 3 models
- **Baseline:** 16.7% success rate, avg 54 steps per trace
- **Models:** swe-agent-llama-70b (93%), llama-8b (5%), llama-405b (2%)

## Project Structure

```
Trashbot/
├── scripts/
│   ├── generate_rules.py          # Rule extraction tool (our main contribution)
│   ├── phase1_pipeline.py         # Data loading + validation
│   └── phase2_baseline.py         # Baseline KPI computation
├── rules/
│   └── rules_v1.md                # 10 generated rules (LLM-extracted)
├── baseline/                      # Baseline metrics + failure analysis
├── failed_traces/
│   └── 10_traces_to_fix/          # Curated traces with passing patches
├── src/
│   ├── data/                      # Dataset loading + validation
│   ├── analysis/                  # Baseline metrics
│   └── classification/            # Failure taxonomy
├── docs/
│   ├── ARCHITECTURE.md            # Full architecture + data flow
│   └── CURSOR_WORKFLOW.md         # How we built this in Cursor
├── CLAUDE.md                      # Agent prompt with injected rules
├── PROGRESS.md                    # Build timeline + contributions
└── README.md                      # This file
```

## Docs

- **[Architecture](docs/ARCHITECTURE.md)** — System design, data flow, failure taxonomy, baseline numbers
- **[Cursor Workflow](docs/CURSOR_WORKFLOW.md)** — Step-by-step how we built this in Cursor
- **[Progress](PROGRESS.md)** — Timeline and contribution tracking
