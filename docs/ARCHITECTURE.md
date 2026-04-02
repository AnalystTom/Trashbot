# Trashbot — What We're Building

## WHY — THE HACKATHON CHALLENGE

Track: **Agent Runtime Tools** — Skills, tools, and decision layers that
make agents more capable.

The challenge: **improve a coding agent without changing the model.**

We do it by learning from 80,000 real agent runs what works and what
doesn't, then feeding that back as decision rules.

## WHAT — THE IDEA IN 30 SECONDS

AI coding agents fail **83% of the time** on real GitHub issues.
Not because the model is dumb — because the agent makes bad decisions
about what to do next.

We have 80,000 recordings of these attempts. We now have hard numbers
on exactly WHY they fail:

```
WHAT GOES WRONG                    FAILED RUNS    SUCCESSFUL RUNS
────────────────────────────────── ────────────── ─────────────────
Agent gets stuck in loops           68%            38%
Agent writes code with syntax err   56%            32%
Agent hits context window limit     58%            19%
Agent never runs tests              39%            47%  (not tested)
Average steps to finish             75 steps       43 steps
```

The gap is clear. Failed agents loop more, write broken code more,
and burn through their context window. Successful agents are tighter
and more disciplined.

**We extract those disciplines as rules and inject them into the agent.**

## HOW — TWO PARTS

```
PART 1: Extract rules from traces
────────────────────────────────
  80,000 traces ──> Haiku agent swarm ──> 10-20 plain-English rules

  Example rules:
  "If you've edited the same file 3 times and tests still fail, STOP.
   Re-read the test output. The assertion names the exact function."

  "Run the test suite in your first 5 actions. Don't guess — let the
   error tell you where to look."


PART 2: Inject rules into agent
────────────────────────────────
  Rules get formatted as CLAUDE.md / system prompt instructions.
  Agent reads them before starting any task.
  Agent follows rules → makes fewer mistakes → succeeds more.

  Then: new traces from improved agent → extract better rules → repeat.
  SELF-IMPROVING LOOP.
```

---

## THE DATA (what we actually have)

### Full dataset (all models)

```
Source:   nebius/SWE-agent-trajectories (Hugging Face)
Local:    data/swe-agent-trajectories/ (parquet files)

Total traces:         80,036
Successes:            13,389  (16.7%)
Failures:             66,647  (83.3%)
Unique GitHub issues:  3,560

Models:
  swe-agent-llama-70b:   74,792 traces  (16.7% success)
  swe-agent-llama-8b:     4,053 traces  (15.1% success)
  swe-agent-llama-405b:   1,191 traces  (25.9% success)
```

### 8b model deep analysis (NEW — already computed)

Tom's agent has analyzed every single 8b run and extracted boolean
failure signals per run. This is the richest data we have:

```
File: baseline/8b_instance_results.json     (4,053 individual runs)
File: baseline/8b_per_instance.json         (528 unique issues, aggregated)

Per-run fields:
  instance_id, resolved, exit_status, steps,
  looping, edit_syntax_errors, ran_tests,
  hit_context_limit, has_patch

Per-instance fields:
  instance_id, attempts, solved, failed, ever_solved,
  solve_rate, avg_steps_failed, pct_looping,
  pct_edit_syntax_err, pct_context_limit
```

### The numbers that matter (8b model, from real data)

```
                        FAILED RUNS     SUCCESSFUL RUNS     GAP
                        (3,439)         (614)
─────────────────────── ─────────────── ─────────────────── ────
Looping                 68.0%           37.6%               -30%
Edit syntax errors      56.4%           31.9%               -24%
Hit context limit       57.8%           19.2%               -39%
Never ran tests         39.2%           47.2%               +8%
Avg steps               74.8            43.3                -31

Death spiral            55.8%           —
(loop until context
 runs out)
```

**Key findings:**
1. **Context limit is the #1 differentiator.** 58% of failures hit it vs 19% of successes. That's a 39-point gap.
2. **Looping is the #2 killer.** 68% of failures loop vs 38% of successes.
3. **The death spiral** (loop + context limit) catches 56% of all failures. The agent loops, burns tokens, runs out of context, and dies.
4. **Syntax errors** are surprisingly common — 56% of failures have them. The agent can't even write valid code.
5. **Running tests doesn't help much by itself.** Both successes and failures run tests at similar rates. The difference is what the agent DOES with test output.

### What 83.5% of issues look like

```
528 unique issues attempted by 8b model:
  Ever solved:   87 issues (16.5%)
  NEVER solved: 441 issues (83.5%)  ← agent fails every single attempt
```

For the 441 never-solved issues, the agent failed on every single
attempt across all runs. These are truly stuck.

---

## WHAT'S BEEN BUILT SO FAR

```
 WHAT                               STATUS      FILES
──────────────────────────────────── ─────────── ──────────────────────────────
 Dataset loaded (80K traces)         DONE        src/data/load_dataset.py
                                                 src/data/validate_schema.py

 Baseline metrics (all models)       DONE        baseline/baseline.json
                                                 baseline/data_profile.json

 8b model deep analysis              DONE        baseline/8b_instance_results.*
   (per-run failure flags)                       baseline/8b_per_instance.*
   (per-instance aggregation)

 Failed instance IDs                 DONE        baseline/failed_instance_ids.*

 Failure taxonomy (enum)             DONE        src/classification/failure_taxonomy.py

 Rule extractor (Part 1)             NOT BUILT
 Rule injector (Part 2)              NOT BUILT
 Self-improving loop                 NOT BUILT
```

---

## WHAT WE BUILD NEXT

### The pipeline

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  INPUT: 4,053 analyzed 8b runs (with failure flags)             │
│         + raw trace text from parquet files                      │
│                                                                  │
│         ┌────────────────────┐                                   │
│    [1]  │  SELECT TRACES     │  Pick failed traces that have     │
│         │                    │  clear failure signals:            │
│         │  looping=True      │  - 500 sample to start            │
│         │  syntax_err=True   │  - mix of failure patterns        │
│         │  no_tests=True     │  - include some successes too     │
│         └────────┬───────────┘                                   │
│                  │                                                │
│                  v                                                │
│         ┌────────────────────┐                                   │
│    [2]  │  EXTRACT RULES     │  Send each trace to Haiku:        │
│         │  (Haiku swarm)     │  "This agent [failed/succeeded].  │
│         │                    │   What's the ONE lesson?"          │
│         │  ~500 API calls    │                                    │
│         │  ~$0.50            │  Returns 1-2 sentence rule        │
│         │  ~2 min            │                                    │
│         └────────┬───────────┘                                   │
│                  │                                                │
│                  v                                                │
│         ┌────────────────────┐                                   │
│    [3]  │  CONSOLIDATE       │  Deduplicate raw rules            │
│         │                    │  Cluster similar rules             │
│         │                    │  Rank by frequency + impact        │
│         │                    │  Output: 10-20 final rules         │
│         └────────┬───────────┘                                   │
│                  │                                                │
│                  v                                                │
│         ┌────────────────────┐                                   │
│    [4]  │  FORMAT AS         │  rules/rules_v1.md                │
│         │  CLAUDE.MD RULES   │  Ready to paste into any          │
│         │                    │  agent's system prompt             │
│         └────────┬───────────┘                                   │
│                  │                                                │
│                  v                                                │
│         ┌────────────────────┐                                   │
│    [5]  │  SIMULATE          │  Take failed traces, give Haiku   │
│         │  BEFORE/AFTER      │  the trace + rules, ask:          │
│         │                    │  "How would the agent have acted   │
│         │                    │   differently with these rules?"   │
│         │                    │  → side-by-side comparison         │
│         └────────────────────┘                                   │
│                                                                  │
│  OUTPUT: rules/rules_v1.md                                       │
│          demo/before_after_examples.md                            │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### What the rules might look like (based on the real data)

The numbers already tell us what the rules SHOULD say:

```
DATA SIGNAL                          LIKELY RULE
──────────────────────────────────── ──────────────────────────────────────
68% of failures loop                 "If you've taken the same action 3x,
38% of successes loop                 STOP. State what you've tried. Try a
                                      completely different approach."

56% of failures have syntax errors   "Before submitting any edit, mentally
32% of successes have syntax errors   parse the code. Check indentation,
                                      brackets, and quotes. Syntax errors
                                      waste steps and burn context."

58% of failures hit context limit    "You have limited context. Every step
19% of successes hit context limit    costs tokens. Be surgical: grep first,
                                      open only the file you need, make one
                                      focused edit, test immediately."

56% of failures loop + hit context   "The worst outcome is looping until
(the death spiral)                    context runs out. Set a mental budget:
                                      if you haven't made progress in 10
                                      steps, submit your best attempt."
```

### Files to build

```
 #   FILE                              WHAT IT DOES                    LINES
──── ──────────────────────────────── ────────────────────────────── ──────
 1   src/swarm/__init__.py             Module init                    ~5
 2   src/swarm/haiku_client.py         Async Anthropic API wrapper    ~50
 3   src/swarm/extract_rules.py        Trace → rule (1 Haiku call)   ~80
 4   src/swarm/batch_runner.py         Run extractor over N traces    ~60
 5   src/swarm/consolidate.py          Dedupe → final ruleset         ~50
 6   src/swarm/simulate.py             Before/after comparison        ~60
 7   scripts/extract_rules.py          Entry point: run everything    ~40
 8   rules/rules_v1.md                 OUTPUT: the rules              generated
                                                              TOTAL  ~345 lines
```

---

## COST & TIME

```
WHAT                     TRACES    COST       TIME
──────────────────────── ───────── ────────── ──────
Start here (iterate)        500    ~$0.50     ~2 min
8b model full             4,053    ~$4        ~3 min
All failures             66,647    ~$67       ~8 min
```

**Start with 500. Get the prompt right. Then scale.**

---

## WHAT WE NEED

```
1. ANTHROPIC_API_KEY in .env     ← only thing needed
2. Data is already loaded and analyzed.
```

---

## WHAT WE TELL JUDGES

> "We analyzed 80,000 real SWE-agent runs. 83% failed. We found that
>  68% of failures get stuck in loops, 56% write broken syntax, and
>  56% enter a death spiral — looping until context runs out.
>
>  We built a tool that extracts decision rules from these traces and
>  injects them into the agent's prompt. The agent reads 15 rules
>  learned from 80,000 attempts before it starts working.
>
>  Same model. Better decisions. Higher success rate."

---

## PROJECT STRUCTURE

```
Trashbot/
├── src/
│   ├── data/
│   │   ├── load_dataset.py              DONE  — load + normalize traces
│   │   └── validate_schema.py           DONE  — schema validation
│   ├── analysis/
│   │   └── baseline_metrics.py          DONE  — baseline KPIs
│   ├── classification/
│   │   └── failure_taxonomy.py          DONE  — failure type enum
│   ├── swarm/                           BUILD NEXT
│   │   ├── haiku_client.py              — async Haiku API wrapper
│   │   ├── extract_rules.py             — trace → rule extraction
│   │   ├── batch_runner.py              — run over N traces
│   │   ├── consolidate.py               — dedupe → final ruleset
│   │   └── simulate.py                  — before/after comparison
│   ├── interventions/                   (empty stub)
│   ├── simulation/                      (empty stub)
│   ├── eval/                            (empty stub)
│   └── demo/                            (empty stub)
│
├── scripts/
│   ├── phase1_pipeline.py               DONE
│   ├── phase2_baseline.py               DONE
│   └── extract_rules.py                 BUILD — entry point
│
├── rules/                               OUTPUT
│   └── rules_v1.md                      — generated rules (CLAUDE.md format)
│
├── baseline/                            DONE
│   ├── baseline.json                    — full baseline KPIs (80K)
│   ├── data_profile.json                — dataset stats
│   ├── validation_report.json           — 0 errors
│   ├── failed_instance_ids.txt          — 3,560 unique failed issue IDs
│   ├── failed_instance_ids.json         — same as JSON
│   ├── 8b_instance_results.json         — 4,053 runs with failure flags
│   ├── 8b_instance_results.csv          — same as CSV
│   ├── 8b_per_instance.json             — 528 issues aggregated
│   └── 8b_per_instance.csv              — same as CSV
│
├── docs/
│   └── ARCHITECTURE.md                  THIS FILE
├── AGENTS.md
├── README.md
└── pyproject.toml
```
