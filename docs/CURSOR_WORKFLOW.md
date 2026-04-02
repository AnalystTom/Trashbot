# Cursor Workflow — How We Built This

## Tool
Built entirely in **Cursor** (AI-native code editor) using Cursor Agent mode
with Claude as the underlying model.

## Workflow Steps

### Step 1: Project Setup & Data Exploration
- Opened repo in Cursor
- Used Cursor Agent to pull from main and explore the dataset structure
- Agent read `src/data/load_dataset.py`, `baseline/baseline.json`, etc.
- Understood the data: 80,036 traces, 16.7% success, 83.3% failure

### Step 2: Architecture Design
- Asked Cursor Agent to analyze the project and create `docs/ARCHITECTURE.md`
- Agent produced full ASCII architecture diagrams, data flow, and build plan
- Iterated on the doc through conversation until the vision was clear

### Step 3: Baseline Analysis
- Cursor Agent analyzed the 8b model failure data (`baseline/8b_instance_results.json`)
- Ran Python analysis inline to extract failure patterns:
  - 68% of failures loop
  - 56% have syntax errors
  - 56% enter death spiral (loop until context limit)
- Results informed the rule extraction approach

### Step 4: Rule Extraction Tool (Heuristic — v1)
- Asked Cursor Agent to build `scripts/generate_rules.py`
- First version used heuristic pattern matching on trace metadata
- Result: too generic — all 10 traces produced the same rule
- Cursor Agent identified the problem and suggested LLM-based approach

### Step 5: Rule Extraction (LLM Subagents — v2)
- Used Cursor Agent's ability to spawn subagents
- Spawned 10 agents in parallel, one per trace
- Each agent:
  1. Read the full trace JSON (issue text + failed trajectories + passing patch)
  2. Compared what failed agents did wrong vs what the passing agent did right
  3. Produced one specific, actionable rule
- All 10 agents ran simultaneously
- Result: 10 unique, specific rules in ~60 seconds

### Step 6: Close the Loop
- Cursor Agent saved rules to `rules/rules_v1.md`
- Appended compact rules to `CLAUDE.md`
- Rules are now part of the agent's prompt for future runs

## Key Cursor Features Used

| Feature | How We Used It |
|---|---|
| **Agent Mode** | Full autonomous coding — reads files, writes code, runs scripts |
| **Subagent Spawning** | 10 parallel agents analyzing traces simultaneously |
| **Inline Terminal** | Ran Python analysis, git pulls, and pipeline scripts |
| **Multi-file Editing** | Updated CLAUDE.md, rules_v1.md, ARCHITECTURE.md in one flow |
| **Context Awareness** | Agent tracked project state across multiple pulls from main |

## Commands Used in Cursor

```
# Pull latest changes from team
git pull origin main

# Run rule extraction
python scripts/generate_rules.py

# Run with CLAUDE.md injection
python scripts/generate_rules.py --append-to CLAUDE.md

# Analyze baseline data
python3 -c "import json; ..."  (inline analysis)
```

## What Made Cursor the Right Tool

1. **Agent mode handles the full loop** — read traces, write code, run it, evaluate output, iterate
2. **Subagent parallelism** — 10 trace analyses in 60 seconds instead of doing them one by one
3. **Conversation context** — the agent remembered the full project state across a long session
4. **No context switching** — everything happened in one editor: code, terminal, git, docs
5. **Iterative refinement** — when heuristic rules were bad, agent diagnosed why and pivoted to LLM approach in the same session
