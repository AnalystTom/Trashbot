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
