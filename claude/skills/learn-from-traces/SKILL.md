---
name: learn-from-traces
description: Read the next batch of 10 failed execution traces from failed_traces/, identify the shared failure pattern, and write a reusable skill into .claude/skills/.
when_to_use: Use when you want to analyze failed agent traces and extract reusable behavioral skills. Examples: 'learn from traces', 'analyze failures', 'extract skill from traces', 'run the trace learning loop'.
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - Bash(ls:*)
  - Bash(cat:*)
  - Bash(wc:*)
  - Bash(mkdir:*)
---

# Learn From Traces

Analyze the next batch of 10 failed execution traces, identify the shared behavioral failure pattern, and synthesize a single reusable skill that prevents that class of failure in the future.

## Inputs

- **Traces directory**: `failed_traces/` (relative to repo root)
- **Processed log**: `.claude/processed_traces.txt` (tracks already-analyzed files, one basename per line)
- **Existing skills**: `.claude/skills/` (check before writing to avoid duplicates)

## Steps

### 1. Select the next batch

- List all `.json` files directly inside `failed_traces/` (no subdirectories).
- Read `.claude/processed_traces.txt` if it exists; these filenames are already done.
- Take the next 10 unprocessed files, sorted alphabetically.
- If zero unprocessed files remain, report that and stop.
- If fewer than 10 remain, use however many are left.

**Success criteria**: You have a list of 1–10 trace filenames to analyze.

### 2. Read and understand each trace

For each selected file, read the JSON and extract:
- `instance_id`, `issue_text`, `passed_count`, `total_attempts`
- `failed_traces[]` — for each failed trace, read the `trajectory` (steps with `role` + `text`) and the `patch`

Understand what the agent tried to do, what it produced, and why the output was wrong or incomplete.

**Focus on the agent's approach, not the underlying bug.** You are not fixing the bugs — you are diagnosing why the agent's reasoning or process failed.

**Success criteria**: You can describe, for each trace, the specific mistake the agent made.

### 3. Identify the shared failure pattern

Analyze all traces together. Look for behaviors that recur across at least 3 of them:

- Made a fix without searching for all related usages
- Read too few lines of code before editing
- Submitted without running any verification
- Fixed the wrong layer or wrong function
- Applied a partial change (deleted a definition, left all callers)
- Used a wrong API signature or incorrect type semantics
- Expressed premature confidence on incomplete information
- Repeated the same reasoning mistake in different contexts

Pick the **single most impactful cross-cutting pattern**. Name it concisely (e.g. `narrow-fix-without-usage-search`, `submit-without-verification`, `wrong-fix-location`).

**Success criteria**: One named pattern that explains failures in ≥3 of the 10 traces.

### 4. Check for duplicate skills

- List all files matching `.claude/skills/*/SKILL.md`.
- Read the `description` frontmatter field from each.
- If an existing skill already covers the identified pattern well enough, skip Step 5 and go directly to Step 6.

**Success criteria**: You know whether to create a new skill or not.

### 5. Write the skill

Create `.claude/skills/<pattern-slug>/SKILL.md` using this template:

```markdown
---
name: <pattern-slug>
description: <one-line description of when this skill applies>
---

# <Title>

## When This Applies

<Specific situation: task type, stage of work, environmental cues that signal this skill is relevant.>

## The Problem This Prevents

<What goes wrong without this skill. Include 2–3 concrete examples drawn directly from the traces you analyzed — real failure modes, not hypotheticals.>

## What To Do

<Step-by-step behavioral protocol. Be specific and actionable. Include concrete commands or checks.>

## What To Avoid

<Explicit anti-patterns with reasons.>

## Example

<Short right/wrong or before/after example showing the skill applied.>

## Summary Heuristic

> <One memorable sentence the agent can use as a quick mental check.>
```

The skill must be:
- A **behavioral rule**, not a fix for one specific bug
- General enough to apply to future unseen tasks
- Grounded in examples from the actual traces you read

**Success criteria**: `.claude/skills/<slug>/SKILL.md` exists and is well-formed.

### 6. Update the processed log

Append the basenames of all traces you analyzed to `.claude/processed_traces.txt` (one per line, e.g. `foo__bar-123.json`). Create the file if it doesn't exist.

**Success criteria**: `.claude/processed_traces.txt` is updated; these files won't be re-processed next run.

### 7. Report

Output a brief summary:
- Traces analyzed (count + filenames)
- Failure pattern identified
- Skill written (path) or existing skill matched
- Traces remaining unprocessed
