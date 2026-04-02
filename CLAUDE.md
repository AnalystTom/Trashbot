# Trashbot — Meta-Harness for SWE-Agent Trajectories

## Project
Offline analysis pipeline over SWE-bench agent trajectories (nebius/SWE-agent-trajectories).
Goal: classify failures, apply interventions, simulate improved outcomes.

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

## Project Structure
- `src/data/` — dataset loading and validation
- `src/analysis/` — baseline metrics
- `src/classification/` — failure taxonomy and classifier
- `src/interventions/` — meta-harness intervention engine
- `src/simulation/` — outcome simulation
- `src/eval/` — delta computation
- `src/demo/` — demo example preparation
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
