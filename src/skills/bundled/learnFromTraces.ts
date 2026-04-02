import { registerBundledSkill } from '../bundledSkills.js'

const LEARN_FROM_TRACES_PROMPT = `# Learn From Traces

You are a self-improving agent loop. Your job is to read a batch of 10 failed execution traces, identify recurring failure patterns, and synthesize a single reusable skill that prevents that class of failure in the future.

## Inputs

- **Traces directory**: \`failed_traces/\`
- **Processed log**: \`.claude/processed_traces.txt\` (list of already-analyzed trace filenames, one per line)
- **Skills output**: \`.claude/skills/<pattern-name>/SKILL.md\`
- **Existing skills**: list the current contents of \`.claude/skills/\` before writing anything new

## Step 1: Select the next batch of 10 traces

1. List all \`.json\` files in \`failed_traces/\` (excluding any subdirectories).
2. Read \`.claude/processed_traces.txt\` if it exists. This is your exclusion list.
3. From the unprocessed files, take the next 10 (alphabetically).
4. If fewer than 10 unprocessed traces remain, use however many are left. If zero remain, report that all traces have been processed and stop.

## Step 2: Read and understand the traces

For each of the 10 selected trace files:
- Read the JSON file.
- Extract: \`instance_id\`, \`issue_text\`, \`passed_count\`, \`total_attempts\`, and the \`failed_traces\` array.
- For each failed trace in the \`failed_traces\` array, read the \`trajectory\` (list of \`{role, text}\` steps) and the \`patch\`.
- Understand what the agent tried to do, what it produced, and why it was wrong.

**Focus on failure mode, not the bug itself.** You are not trying to fix the bug — you are trying to understand why the agent's *approach* failed.

## Step 3: Identify the shared failure pattern

Analyze all 10 traces together. Look for recurring behaviors across multiple traces — not isolated one-off mistakes. Ask:

- Did agents make fixes without searching for all related usages?
- Did agents read too little code before editing?
- Did agents submit without any verification?
- Did agents misidentify the root cause or fix the wrong layer?
- Did agents use wrong API signatures or type semantics?
- Did agents apply partial refactors (e.g. deleted a definition but left all callers)?
- Did agents confuse similar-looking but semantically different constructs?
- Was there a pattern of premature confidence — acting on partial information?

Pick the single most impactful, cross-cutting failure pattern. It should explain failures in at least 3 of the 10 traces.

## Step 4: Check for duplicate skills

List all existing \`.claude/skills/*/SKILL.md\` files and read their frontmatter \`description\` fields. If an existing skill already covers the identified pattern, do not create a duplicate — instead note which existing skill applies and skip to Step 6 (update processed log).

## Step 5: Write the skill

Create \`.claude/skills/<descriptive-slug>/SKILL.md\` with this format:

\`\`\`markdown
---
name: <slug>
description: <one-line description of when this skill applies — used for matching>
---

# <Title>

## When This Applies

<Describe the specific situation: what kind of task, what stage, what cues in the environment suggest this skill is relevant.>

## The Problem This Prevents

<Explain concretely what goes wrong without this skill. Include 2–3 specific examples drawn from the actual traces you analyzed — real failure modes, not hypotheticals.>

## What To Do

<Step-by-step behavioral protocol. Be specific and actionable. Include concrete commands or checks where relevant.>

## What To Avoid

<Explicit anti-patterns, with reasons.>

## Example

<Short before/after or right/wrong example showing the skill in action.>

## Summary Heuristic

> <One memorable sentence the agent can apply as a quick mental check.>
\`\`\`

**Quality criteria for the skill:**
- It must be a *behavioral rule*, not a bug fix for one specific issue.
- It must be general enough to apply to future unseen tasks.
- The "What To Do" section must be actionable — concrete steps, not vague advice.
- Draw examples directly from the actual traces you read.

## Step 6: Update the processed log

Append the filenames of all 10 traces you analyzed to \`.claude/processed_traces.txt\` (one filename per line, just the basename e.g. \`foo__bar-123.json\`). Create the file if it doesn't exist.

## Step 7: Report

Output a brief summary:
- How many traces were analyzed
- Which failure pattern was identified
- The skill name and path written (or which existing skill was matched)
- How many traces remain unprocessed
`

export function registerLearnFromTracesSkill(): void {
  registerBundledSkill({
    name: 'learn-from-traces',
    description:
      'Read the next batch of 10 failed execution traces from failed_traces/, identify the shared failure pattern, and synthesize a reusable skill into .claude/skills/.',
    allowedTools: [
      'Read',
      'Write',
      'Edit',
      'Glob',
      'Grep',
      'Bash(ls:*)',
      'Bash(wc:*)',
    ],
    userInvocable: true,
    async getPromptForCommand() {
      return [{ type: 'text', text: LEARN_FROM_TRACES_PROMPT }]
    },
  })
}
