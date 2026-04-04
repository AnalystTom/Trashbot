# Trashbot — Self-Learning Meta-Harness for AI Agent Benchmarks

## Project
Generic self-learning loop that improves AI agents by analyzing failed benchmark traces.
Works with any benchmark platform (SWE-bench, ClawBench, etc.) through adapters.

**Core loop:** Failed traces → Failure classification → Rule extraction → Corrected patches → Improved scores

## Setup
```bash
source .venv/bin/activate
```

## Trace Query Tool
Use `query_traces.py` to look up any trace in the dataset. Always activate the venv first.

```bash
# Look up a specific instance
python query_traces.py --id django__django-11099

# Filter by model
python query_traces.py --id django__django-11099 --model swe-agent-llama-8b

# Search by repo (partial match)
python query_traces.py --repo scikit-learn

# Only failures
python query_traces.py --repo flask --failed-only

# Show full trajectory (step-by-step agent actions)
python query_traces.py --id django__django-11099 --show-trajectory

# Show the generated patch
python query_traces.py --id django__django-11099 --show-patch

# Show eval/test logs
python query_traces.py --id django__django-11099 --show-eval

# Export matches to JSON
python query_traces.py --repo sympy --failed-only --export results.json

# List unique instance IDs
python query_traces.py --repo django --list-instances
```

## Data
- Local parquet files: `data/swe-agent-trajectories/data/*.parquet` (80,036 rows)
- 3 models: swe-agent-llama-70b, swe-agent-llama-8b, swe-agent-llama-405b
- Baseline results: `baseline/`
- Key: `instance_id` (e.g. `django__django-11099`) matches HuggingFace dataset

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      BENCHMARK SOURCES                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ SWE-bench    │  │ ClawBench   │  │ Future benchmarks   │ │
│  │ (parquet)    │  │ (API/local) │  │ (add adapter)       │ │
│  └──────┬───────┘  └──────┬──────┘  └──────────┬──────────┘ │
│         │                 │                     │            │
│  ┌──────▼─────────────────▼─────────────────────▼──────────┐ │
│  │              src/adapters/                               │ │
│  │  swebench.py  |  clawbench.py  |  base.py (interface)   │ │
│  └──────────────────────┬───────────────────────────────────┘ │
└─────────────────────────┼───────────────────────────────────┘
                          ▼
               ┌─────────────────────┐
               │  failed_traces/     │  ← Normalized trace files
               │  ├── 10_traces_*/   │     (one JSON per instance)
               │  └── clawbench/     │
               └─────────┬───────────┘
                         │
          ┌──────────────▼──────────────┐
          │  Self-Learning Loop          │
          │                              │
          │  1. Classify failures        │ ← src/classification/
          │  2. Extract rules            │ ← claude/skills/learn-from-traces/
          │  3. Store rules              │ → CLAUDE.md + .claude/skills/
          │  4. Apply rules to traces    │ ← hermes trace_query(run_harness)
          │  5. Measure improvement      │ → demo_output/
          └──────────────┬──────────────┘
                         │
          ┌──────────────▼──────────────┐
          │  Output                      │
          │  - demo_output/_summary.json │
          │  - Per-instance results      │
          │  - Before/after metrics      │
          └─────────────────────────────┘
```

## Adding a New Benchmark Source

1. Create `src/adapters/<name>.py` implementing:
   - `normalize_run(run) → dict` (convert to internal trace format)
   - `export_for_harness(runs, output_dir) → int` (write trace files)
2. Export traces to `failed_traces/<name>/`
3. Run: `trace_query(action="run_harness", trace_set="<name>")`

## ClawBench Integration

```bash
# From ClawBench API
python -m src.adapters.clawbench --api-url http://localhost:8080 --export failed_traces/clawbench/

# From local artifacts
python -m src.adapters.clawbench --local /Users/tom/Dev/clawbench/artifacts/ --export failed_traces/clawbench/

# Run harness on ClawBench traces
# In hermes: trace_query(action="run_harness", trace_set="clawbench")
```

## Project Structure
- `src/adapters/` — benchmark source adapters (SWE-bench, ClawBench)
- `src/data/` — dataset loading and validation
- `src/analysis/` — baseline metrics
- `src/classification/` — failure taxonomy and classifier
- `src/interventions/` — meta-harness intervention engine
- `src/simulation/` — outcome simulation
- `src/eval/` — delta computation
- `src/demo/` — demo example preparation
- `claude/skills/learn-from-traces/` — rule extraction skill
- `hermes-agent/tools/trace_query_tool.py` — hermes tool (query + run_harness)
- `scripts/` — pipeline runner scripts
- `baseline/` — baseline KPIs and failure analysis outputs

## Learned Rules (extracted from failed trace analysis)

Follow these rules when fixing code. Extracted by LLM agents comparing
failed vs passing attempts on 10 real GitHub issues from SWE-bench.

1. **UNSAFE_VARIABLE_ACCESS**: When a variable depends on loop execution, check if it exists before referencing it rather than pre-initializing it.

2. **INCOMPLETE_FIX**: When changing a method call, update BOTH the method name AND the argument signature. Changing only one silently passes wrong values.

3. **MISSING_ERROR_HANDLING**: Before accessing a dict by key, check if the key exists with a membership test or try/except. Don't assume keys exist.

4. **INDEX_MISMATCH**: When building lists accessed by enumerate position, ensure ALL iterations append an entry (even 0) to maintain length parity.

5. **WRONG_ABSTRACTION_LEVEL**: Implement checks at the public API entry point, BEFORE caching or backend calls. Don't push optimization to lower layers.

6. **WRONG_PLACEMENT**: Place setup operations (like mkdir) BEFORE the code that depends on them, not after.

7. **WRONG_DIAGNOSIS**: Read error messages precisely. "NoneType is not subscriptable" means value is None, not key is missing. Match fix to actual error.

8. **INDEX_MISALIGNMENT**: When creating a boolean Series for DataFrame `.loc`, ensure it has the SAME index as the DataFrame.

9. **SEMANTICS_ERROR**: When data can't be converted (e.g. "N/A" to int), skip silently. Don't substitute misleading defaults like 0.

10. **INCOMPLETE_CLEANUP**: After removing a deprecated constant, search the ENTIRE codebase for usages. Remove definition, usage code, AND tests.
