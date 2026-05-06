# Final Project Report — The Flashcard Quizzer

**Student:** Gour Bera

**Course:** Udacity AI Engineering

**Project:** The Flashcard Quizzer CLI Application

**Date:** May 2026

---

## Introduction

This report documents the development of The Flashcard Quizzer, a
production-ready command-line application for memorising flashcard decks.
The project was built using AI-assisted development with GitHub Copilot as
the primary AI collaborator. The application allows users to quiz themselves
on flashcard decks loaded from JSON files using three distinct quiz modes:
Sequential, Random, and Adaptive.

The goal of this project was not merely to produce a working tool, but to
practise an industry-standard workflow for AI-assisted software engineering:
decompose requirements into clear specifications, generate code with AI,
critically review the output, identify and fix defects, and document the
entire process. The result is a codebase that demonstrates modular
architecture, three design patterns, full type-hint coverage, and a test
suite exceeding 94% code coverage across 116 tests.

---

## How I Used AI Throughout Development

### Phase 1: Planning and Architecture

The first thing I asked the AI was not to write code, but to propose an
architecture. This approach was deliberate — I knew from prior experience
that asking AI to immediately write code for a complex multi-module project
tends to produce monolithic output that is hard to refactor.

I gave the AI a detailed prompt describing all functional and technical
requirements and asked it to propose a file structure and list of classes
before writing a single line of code. The AI suggested a four-file structure
(main.py, data_loader.py, quiz_engine.py, ui.py). I reviewed this against the
rubric requirements and added three additional modules: `stats_tracker.py`
for the Observer Pattern, `exporter.py` for session export, and `config.py`
for configuration management. This up-front planning saved significant
refactoring time later.

### Phase 2: Implementing the Core Logic

With the architecture agreed upon, I used targeted prompts for each module
rather than asking for the entire codebase at once. For `quiz_engine.py`, I
wrote a detailed prompt that specified the exact class names, method
signatures, the requirement for an abstract base class, and the behaviour of
`AdaptiveMode` in precise algorithmic terms.

The AI produced a largely correct implementation on the first attempt. The
Strategy Pattern was well-structured: `QuizMode` as an ABC, three concrete
subclasses, and a `QuizModeFactory` with a `create()` class method. However,
code review revealed two bugs that the AI did not anticipate. First, the
`_requeue_position` counter in `AdaptiveMode` was not reset inside the
`load()` method, meaning that re-initialising a session with new cards would
carry over stale state from a previous session. Second, the `QuizModeFactory`
was initially generated as a simple dictionary rather than as a class with a
`create()` class method as the rubric required. In a professional PR review,
both of these issues would have been caught and flagged before merge.

### Phase 3: The Observer Pattern for Stats Tracking

The Observer Pattern was the stand-out design pattern I added beyond the
rubric's minimum requirement. I prompted the AI to create a `QuizObserver`
abstract base class and a `SessionStats` concrete observer as a dataclass.
The AI's initial implementation was mostly correct, but it did not handle the
case where a card in `AdaptiveMode` could be answered incorrectly multiple
times, potentially appearing multiple times in the `missed` list. I identified
this during code review and added a deduplication check using a set of
`front` strings before appending to `missed`.

This is a good example of a class of AI error that is easy to miss: the
code works correctly for the happy path but has subtle logical issues at edge
cases. A code review that only checks "does the function do what it says it
does?" would miss this; you have to think through all the scenarios.

### Phase 4: Generating the Test Suite

I asked the AI to write tests for each module in separate files. For
`test_flashcard_loader.py`, the prompt listed seven specific scenarios to
cover. The AI generated 23 tests, which was more than the minimum, but three
of them had errors:

1. A test for malformed JSON used a valid JSON string rather than genuinely
   malformed syntax, making the test ineffective.
2. Several tests used `pytest.raises(ValueError)` but the actual code raises
   the custom `FlashCardLoadError` — the AI had assumed a generic exception.
3. A test for missing fields used capitalized key names (`"Front"`, `"Back"`)
   and expected the load to succeed, when the code strictly checks for
   lowercase keys and the load should fail.

This experience reinforced a critical rule: always run AI-generated tests
against the actual implementation immediately. AI can write tests that
confidently assert the wrong thing, giving a false sense of security.

### Phase 5: Code Quality and Linting

After the implementation was complete, I ran `flake8`, `mypy --strict`, and
`black` on the codebase. Several issues emerged from AI-generated code:

- An unused `TYPE_CHECKING` import block in `quiz_engine.py`.
- Inconsistent use of `Optional[T]` versus the modern `T | None` union syntax.
- A missing return type annotation on `_build_parser` in `main.py`.

I fixed all of these and the codebase now passes all quality checks with zero
errors. The experience of systematically applying quality tools to AI output
is itself an important skill — AI assistants do not always produce code that
passes a strict linter, and part of the engineer's job is to enforce
standards.

---

## Reflections on AI-Assisted Development

### What Worked Well

**Scaffolding is AI's strongest suit.** For producing boilerplate structure —
class skeletons, argparse setup, dataclass definitions, standard error
handlers — AI is extremely fast and accurate. Tasks that would take a
developer 30-60 minutes of typing were generated in seconds.

**Explicit prompts produce better output.** The quality of AI output is
directly proportional to the specificity of the prompt. Prompts that listed
exact method names, parameter types, and edge cases to handle produced
correct code far more reliably than vague high-level prompts.

**AI accelerates test writing.** Generating the initial structure of a test
file with 20+ tests is tedious. The AI produced all the test scaffolding
quickly, and I only needed to correct a small fraction of the assertions.

### What Required Human Oversight

**State management bugs.** The stale `_requeue_position` counter in
`AdaptiveMode` is a class of bug that AI frequently misses: code that is
correct in isolation but breaks when methods are called in sequence. Careful
reading of the code — and, crucially, writing tests that exercise multiple
calls — is necessary to catch these.

**Custom exception types.** AI tends to use generic `Exception` or `ValueError`
unless explicitly instructed to use a custom exception class. For a production
tool where callers may need to distinguish error types, this matters.

**Design pattern correctness.** AI knows design patterns but sometimes
implements a superficially similar but incorrect version (e.g. a dict instead
of a Factory class). When a design pattern is a requirement, you must verify
the implementation against the actual pattern definition.

### What I Learned

The most important lesson from this project is that AI-assisted development
is not a replacement for engineering judgment — it is a powerful accelerator
that requires the engineer to exercise judgment more frequently, not less.
The volume of code produced per hour increases dramatically, which means the
volume of code that needs to be reviewed increases proportionally.

I also learned to trust the testing pipeline over the code review alone. The
test suite found the `_requeue_position` bug in `AdaptiveMode` more reliably
than reading the code, because the test simulated a multi-call scenario that
is difficult to reason about from static analysis alone.

Finally, I learned that decomposing a project into small, well-specified
prompts produces dramatically better results than asking AI to "build the
whole application." Each module, each class, and each test suite should be
a separate AI interaction with a focused, detailed specification.

---

## Architecture Summary

The application is structured across six utility modules and one entry point:

- **`utils/data_loader.py`** — The `FlashCard` dataclass and `load_flashcards()`
  function handle JSON ingestion and validation. A custom `FlashCardLoadError`
  exception provides user-friendly error messages without exposing raw tracebacks.

- **`utils/quiz_engine.py`** — Implements the Strategy Pattern via the `QuizMode`
  ABC and three concrete strategies. The `QuizModeFactory` implements the Factory
  Pattern. `QuizSession` orchestrates the quiz loop and dispatches events to
  observers.

- **`utils/stats_tracker.py`** — Implements the Observer Pattern via the
  `QuizObserver` ABC and `SessionStats` concrete observer. Fully decoupled from
  the quiz loop.

- **`utils/ui.py`** — All terminal output, colour formatting, and the stats
  summary table. Color can be disabled for non-TTY environments.

- **`utils/config.py`** — `AppConfig` dataclass loaded from an optional JSON
  file with safe fallback defaults.

- **`utils/exporter.py`** — Session result export to JSON or CSV.

- **`main.py`** — `argparse`-based CLI entry point that wires all modules
  together.

---

## Conclusion

The Flashcard Quizzer demonstrates that AI-assisted development, when applied
with discipline — careful prompting, systematic code review, comprehensive
testing, and rigorous linting — can produce code that meets professional
quality standards. The project implements three design patterns, achieves 94%
test coverage across 101 tests, passes `flake8` and `mypy --strict` with zero
errors, and delivers features beyond the minimum rubric requirements including
session export, configuration management, and the Observer Pattern for stats
tracking. The AI interaction log documents the iterative process of generating,
reviewing, correcting, and refining AI output that is central to modern
software engineering practice.
