"""Failure taxonomy definitions for SWE-agent trajectory analysis."""

from __future__ import annotations

from enum import Enum


class FailureType(str, Enum):
    WRONG_FILE = "WRONG_FILE"
    LOOPING = "LOOPING"
    BAD_PATCH = "BAD_PATCH"
    NO_TEST_USAGE = "NO_TEST_USAGE"
    EARLY_EXIT = "EARLY_EXIT"
    UNKNOWN = "UNKNOWN"


FAILURE_DESCRIPTIONS = {
    FailureType.WRONG_FILE: "Agent edited or focused on wrong file(s), missing the actual source of the bug.",
    FailureType.LOOPING: "Agent repeated the same or very similar actions without making progress.",
    FailureType.BAD_PATCH: "Agent submitted a patch, but it was incorrect (syntax errors, wrong logic, failed tests).",
    FailureType.NO_TEST_USAGE: "Agent never ran tests or used test feedback to guide edits.",
    FailureType.EARLY_EXIT: "Agent exited prematurely without completing the task (context limit, cost, format error).",
    FailureType.UNKNOWN: "Failure type could not be determined from trajectory heuristics.",
}

# Intervention descriptions for each failure type
INTERVENTION_DESCRIPTIONS = {
    FailureType.WRONG_FILE: "Force file re-search: re-examine issue text, grep for relevant symbols, validate file before editing.",
    FailureType.LOOPING: "Truncate repeated actions and force replan: stop loop, summarize state, try alternative approach.",
    FailureType.BAD_PATCH: "Enforce test-grounded editing: run tests before and after edit, iterate on failures.",
    FailureType.NO_TEST_USAGE: "Inject test feedback: run existing test suite, use failures to guide fix location and correctness.",
    FailureType.EARLY_EXIT: "Extend exploration budget: increase context/cost limits, checkpoint progress before hitting limits.",
}

ALL_FAILURE_TYPES = [ft for ft in FailureType if ft != FailureType.UNKNOWN]
