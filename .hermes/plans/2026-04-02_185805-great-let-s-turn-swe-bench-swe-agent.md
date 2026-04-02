# Meta-Harness for SWE-Agent Trajectories (Hackathon Spec)

## Goal
Build a Meta-Harness that improves a coding agent by learning from failed SWE-agent trajectories (same model, smarter execution layer), and demonstrate measurable before/after gains.

## Current context and assumptions
- Dataset: `nebius/swe-agent-trajectories` from Hugging Face.
- Core unit: trajectory for one issue resolution attempt with step-level execution traces.
- Available fields to use (normalized in project code):
  - `instance_id`
  - `trajectory`
  - `resolved` (or equivalent success label; validate exact key on load)
  - `patch` / `generated_patch` (optional for analysis)
  - eval/test logs if present
- Hackathon constraint: we can simulate intervention outcomes (no full end-to-end live rerun infra required).
- KPI requirement from spec is fixed and must not be changed.

## Proposed approach
1. Build a reproducible offline analysis pipeline over trajectories.
2. Classify failed traces into a required taxonomy.
3. Apply deterministic intervention policies by failure type.
4. Simulate corrected outcomes for failed traces under explicit assumptions.
5. Report baseline vs after metrics + one concrete, visualizable example.

## Step-by-step plan

### Phase 1: Data ingestion and schema validation
1. Load dataset split(s) with `datasets.load_dataset("nebius/swe-agent-trajectories")`.
2. Inspect a sample to confirm field names and normalize into internal schema:
   - `success_label` (mapped from `resolved` or equivalent)
   - `trace_steps` (mapped from `trajectory`)
   - `patch_text`
   - `instance_id`
3. Create a lightweight validator:
   - non-empty trajectory
   - boolean success label
   - step count extraction robust to step format differences
4. Produce a data profile artifact (counts, missing fields, split sizes).

### Phase 2: Baseline metrics (BEFORE)
1. Compute baseline KPIs on dataset-as-is:
   - `success_rate = mean(success_label)`
   - `avg_steps = mean(len(trace_steps))`
2. Compute failure distribution using required taxonomy placeholders initially (UNKNOWN bucket allowed before classifier fill).
3. Save baseline output JSON in required structure.

### Phase 3: Failure classifier
1. Define taxonomy (minimum required):
   - `WRONG_FILE`
   - `LOOPING`
   - `BAD_PATCH`
   - `NO_TEST_USAGE`
   - `EARLY_EXIT`
2. Implement classifier v1 (hackathon-safe heuristic + optional LLM mode):
   - Heuristics first for deterministic reproducibility.
   - Optional LLM prompt classifier for richer semantics.
3. Add confidence and evidence extraction per classification:
   - key step indices
   - matching indicators (e.g., repeated actions, no test-feedback references)
4. Evaluate classifier sanity on random sample with manual spot checks.

### Phase 4: Meta-Harness interventions
1. Implement `apply_meta_harness(trace, failure_type)` with required mapping:
   - WRONG_FILE -> force file re-search
   - LOOPING -> truncate + replan
   - BAD_PATCH -> enforce test-grounded edit
   - NO_TEST_USAGE -> inject test feedback
   - EARLY_EXIT -> extend exploration
2. Represent intervention as:
   - modified trace steps OR
   - explicit intervention action plan (for demo readability)
3. Log intervention decisions for each failed trace (auditability).

### Phase 5: Simulated AFTER outcomes
1. Apply harness only to failed examples.
2. Define transparent simulation rule set (documented assumptions):
   - if intervention addresses detected failure_type -> mark success in simulation
   - optionally include conservative probability per failure type for realism
3. Compute AFTER KPIs:
   - `after_success_rate`
   - `after_avg_steps`
   - `% failures fixed`
   - failure-type deltas
4. Compute required deltas:
   - `delta.success_rate = after_success_rate - baseline_success_rate`
   - `delta.steps = baseline_avg_steps - after_avg_steps`

### Phase 6: Demo package (mandatory)
1. Select one concrete SWE-style example (preferably scikit-learn-like wrong-file failure pattern).
2. Prepare BEFORE narrative from trajectory:
   - wrong file selection
   - irrelevant edit
   - failed tests
3. Prepare AFTER narrative:
   - harness detects `WRONG_FILE`
   - enforces re-search
   - corrected file path/edit sequence
   - simulated pass
4. Produce judge-facing outputs:
   - concise KPI card (e.g., `22% -> 37% (+15%)`)
   - causal chain: failure -> intervention -> outcome

### Phase 7: Final artifacts and handoff
1. Export required final JSON format:
   - `baseline`, `after`, `delta`
2. Export per-failure breakdown tables.
3. Create a short README/demo script for live presentation flow (3-5 min).

## Suggested project structure / files likely to change
- `src/data/load_dataset.py` — dataset loading and schema normalization
- `src/data/validate_schema.py` — validation/profile utilities
- `src/analysis/baseline_metrics.py` — baseline KPI computation
- `src/classification/failure_taxonomy.py` — taxonomy definitions
- `src/classification/classifier.py` — failure classification logic
- `src/interventions/meta_harness.py` — intervention engine
- `src/simulation/simulate_outcomes.py` — AFTER outcome simulation
- `src/eval/compute_deltas.py` — before/after KPI and deltas
- `src/demo/example_trace_story.py` — concrete before/after example prep
- `outputs/baseline.json`
- `outputs/after.json`
- `outputs/final_report.json`
- `README.md` / `demo.md`

## Tests and validation plan
- Unit tests:
  - schema normalization for multiple field variants (`resolved` vs alternative)
  - classifier returns only valid taxonomy labels
  - intervention mapping completeness for all required failure types
  - delta calculations correctness
- Integration tests:
  - end-to-end run on small sample subset (e.g., 200 examples)
  - deterministic outputs in heuristic-only mode
- Demo validation:
  - one selected trace renders clearly in before/after view
  - final JSON matches required output schema exactly

## KPI definitions (strict)
- Primary:
  - `Δ Success Rate = after_success_rate - baseline_success_rate`
- Secondary:
  - `Δ Avg steps to success`
  - `Δ Failure rate by type`
  - `% failures fixed`

## Risks and tradeoffs
- Schema mismatch risk (field naming differences across splits):
  - Mitigation: explicit mapping + validation layer.
- Over-optimistic simulation risk:
  - Mitigation: document assumptions and provide conservative mode.
- Classifier quality variance:
  - Mitigation: heuristic baseline + optional LLM classifier with manual spot checks.
- Causality skepticism from judges:
  - Mitigation: provide per-example evidence and explicit intervention rationale.

## Open questions
1. Should final demo use purely deterministic heuristics, or include optional LLM classifier mode?
2. Should simulation use binary “fixed => success” or per-failure probabilistic correction rates?
3. Which exact subset/split should be used for the headline KPI (train full vs held-out subset)?
4. Do we need a minimal UI (Streamlit) for the demo, or notebook/CLI output is sufficient?

## Deliverable checklist
- [ ] Dataset loaded and normalized
- [ ] Baseline KPIs computed
- [ ] Failures classified into required taxonomy
- [ ] Meta-Harness interventions applied
- [ ] AFTER simulation complete
- [ ] Delta metrics computed in required format
- [ ] One concrete before/after trajectory demo prepared
- [ ] Final report + demo script ready
