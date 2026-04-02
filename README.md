# Trashbot

Self-improvement coach scaffold for ClawBench agents.

This repository now contains an MVP loop that combines:
- Claude Code style harnessing (structured, repeatable workflow)
- Hermes-style self-improvement primitives (pattern detection -> recommendation -> learning artifacts)

## What is implemented
- Trace ingestion from:
  - local JSON file, or
  - remote HTTP endpoint returning JSON
- Basic signal extraction
- Pattern detection:
  - recurring failures by benchmark/task
  - score regression by benchmark
- Action recommendation generation
- Markdown report output

## Quick start

1) Run against a local trace file

PYTHONPATH=src python3 -m trashbot.main --input-file sample_traces.json --report-out report.md

2) Run against an API endpoint

PYTHONPATH=src python3 -m trashbot.main --input-url https://clawbench.com/api/v1/traces --report-out report.md

3) Pull and normalize nebius/SWE-agent-trajectories from Hugging Face

python3 -m pip install -e '.[connectors]'
PYTHONPATH=src python3 -m trashbot.hf_dataset_connector --out swe_agent_traces.json --limit 5000
PYTHONPATH=src python3 -m trashbot.main --input-file swe_agent_traces.json --report-out report.md

Optional install (newer pip/setuptools environments):

python3 -m pip install -e .
python3 -m trashbot.main --input-file sample_traces.json --report-out report.md

Optional env vars for API:
- CLAWBENCH_API_TOKEN
- CLAWBENCH_API_HEADER (default: Authorization)
- CLAWBENCH_API_PREFIX (default: Bearer)

## Project layout
- docs/architecture/clawbench-self-improvement-agent.md
- src/trashbot/
  - ingestion.py
  - analysis.py
  - recommendations.py
  - report.py
  - main.py

## Notes
- This is intentionally dependency-light (stdlib only).
- The analyzer is schema-tolerant and works with mixed trace payload shapes.
- Next step is wiring directly to ClawBench production endpoints and adding automated rerun orchestration.
