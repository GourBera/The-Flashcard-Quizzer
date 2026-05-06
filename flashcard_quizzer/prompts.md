# AI Prompt Log — The Flashcard Quizzer

This file documents, in chronological order, the specific prompts given to
the AI assistant (GitHub Copilot) during development of The Flashcard Quizzer.
Each entry includes the prompt, a brief note on what was generated, and any
modifications made before the code was accepted.

---

## Prompt 1 — Architecture Planning

```
I need to build a CLI flashcard quiz application in Python called "The Flashcard
Quizzer". Before writing any code, please propose a project file structure and
list of classes. Requirements:

- Must be modular — no single-file solution
- Load flashcards from JSON (support both array format and {"cards":[...]} format)
- Three quiz modes: Sequential, Random, Adaptive
- Strategy Pattern for quiz modes
- Factory Pattern to select modes by name
- Session stats at the end (accuracy %, missed cards)
- argparse CLI with -f (file), -m (mode), --no-color flags
- Python type hints on all functions
- pytest test suite

Propose the file structure and classes before writing any code.
```

**Result:** AI proposed 4-file structure. I extended it to 7 utils modules.

---

## Prompt 2 — Data Layer

```
Implement utils/data_loader.py for the Flashcard Quizzer. Requirements:

1. A FlashCard dataclass with fields: front (str), back (str), weight (int, default 1)
2. Validate in __post_init__ that front and back are non-empty, non-whitespace strings.
   Raise FlashCardLoadError (a custom Exception subclass) if they are not.
3. A FlashCardLoadError exception class.
4. A load_flashcards(filepath: str) -> list[FlashCard] function that:
   - Reads a JSON file
   - Supports array format: [{"front": "...", "back": "..."}]
   - Supports object format: {"cards": [...]}
   - Raises FlashCardLoadError (with a helpful message, not a traceback) for:
     * File not found
     * Invalid JSON
     * Missing front or back fields
     * Empty deck
5. All functions must have full Python type hints and docstrings.
```

**Result:** Correct implementation. Accepted with minor docstring tweaks.

---

## Prompt 3 — Quiz Engine (Strategy + Factory)

```
Implement utils/quiz_engine.py using the Strategy and Factory design patterns.

Strategy Pattern:
- QuizMode: abstract base class (ABC) with abstract methods:
  * load(cards: list[FlashCard]) -> None
  * next_card() -> FlashCard | None
  And a non-abstract method:
  * record_result(card: FlashCard, correct: bool) -> None  (default: does nothing)

- SequentialMode(QuizMode): presents cards 1..N in original order
- RandomMode(QuizMode): shuffles the deck on load(), then serves in shuffled order
- AdaptiveMode(QuizMode):
  * On load(): copies the deck, resets all weights to 1, shuffles
  * On record_result(card, correct=False): increments card.weight, re-inserts
    the card near the front of the queue (after other pending re-queued cards)
  * Session ends only when every card is answered correctly at least once

Factory Pattern:
- QuizModeFactory class with:
  * create(mode: str) -> QuizMode  (case-insensitive, strips whitespace)
  * available_modes() -> list[str]  (returns ["sequential", "random", "adaptive"])
  * Raises ValueError("Unknown quiz mode: ...") for unrecognised input

QuizSession class:
- __init__(mode, cards, listeners=None)
- add_listener(listener) -> None
- next_card() -> FlashCard | None  (delegates to mode)
- record_answer(card, answer: str) -> bool  (case-insensitive compare, notifies listeners)
- end_session() -> None  (notifies listeners with on_session_end)

All with type hints and docstrings.
```

**Result:** Mostly correct. Fixed `_requeue_position` reset bug and regenerated
`available_modes()` which was missing.

---

## Prompt 4 — Observer Pattern for Stats

```
Create utils/stats_tracker.py using the Observer design pattern.

QuizObserver abstract base class (ABC):
- on_answer(card: FlashCard, correct: bool) -> None  (abstract)
- on_session_end() -> None  (abstract)

SessionStats(QuizObserver) as a @dataclass:
- Fields: total (int=0), correct_count (int=0), missed (list[FlashCard]=field(default_factory=list))
  All with init=False so they are not constructor parameters.
- on_answer(): increments total; if correct increments correct_count; else appends card to missed
- on_session_end(): marks session finished, logs a summary
- accuracy() -> float: returns (correct/total)*100 rounded to 1dp, or 0.0 if total==0
- incorrect_count() -> int
- summary() -> dict[str, object]: returns dict with total, correct, incorrect, accuracy_pct, missed_terms

All with type hints and docstrings.
```

**Result:** Correct. Fixed missed-card deduplication (same card answered
wrong multiple times in Adaptive mode).

---

## Prompt 5 — UI Module

```
Implement utils/ui.py for the Flashcard Quizzer CLI.

Requirements:
- Import colorama (with a try/except fallback if not installed)
- Import tabulate (with a try/except fallback if not installed)
- Color helper functions: _green(text, color), _red(text, color), _yellow(text, color),
  _cyan(text, color) — use colorama if available, else raw ANSI codes, else plain text
  when color=False

Public functions (all with color: bool = True parameter):
- print_welcome(mode: str, total: int, color: bool) -> None
- print_card_prompt(current: int, total: int, front: str, color: bool) -> None
- print_correct(color: bool) -> None
- print_incorrect(correct_answer: str, color: bool) -> None
- print_goodbye(color: bool) -> None
- display_stats_table(stats: SessionStats, color: bool) -> None
  Uses tabulate if available; plain text fallback otherwise.
  Shows: Total Questions, Correct Answers, Incorrect Answers, Accuracy %
  Shows missed cards list (or "Perfect score!" if none missed)

All with type hints and docstrings.
```

**Result:** Correct. Accepted as-is.

---

## Prompt 6 — Config Module

```
Implement utils/config.py for the Flashcard Quizzer.

AppConfig @dataclass with fields:
- color_enabled: bool = True
- export_enabled: bool = False
- export_path: str = "quiz_results.json"
- export_format: str = "json"
- log_level: str = "WARNING"
- default_mode: str = "sequential"

load_config(path: str = "config.json") -> AppConfig function:
- Reads a JSON file at `path`
- Merges with defaults (missing keys use defaults, extra keys are warned about and ignored)
- If file not found, silently returns AppConfig() with defaults
- If file is valid JSON but not a dict, logs a warning and returns defaults
- Uses logging, not print()

All with type hints and docstrings.
```

**Result:** Correct. Accepted with minor style adjustments.

---

## Prompt 7 — Exporter Module

```
Create utils/exporter.py for the Flashcard Quizzer.

ExportError(Exception): custom exception for export failures.

export_session(stats: SessionStats, filepath: str, fmt: str = "json",
               deck_name: str = "", mode: str = "") -> None:
- Creates parent directories if needed (os.makedirs)
- Builds a summary dict from stats.summary() and adds: timestamp (ISO 8601),
  deck (deck_name), mode (mode)
- If fmt == "json": write formatted JSON (indent=2)
- If fmt == "csv": write CSV with headers row and one data row
- If fmt is unknown: raise ExportError
- If OSError occurs: raise ExportError wrapping the original

Separate private functions _export_json and _export_csv.
All with type hints and docstrings.
```

**Result:** Missing `os.makedirs` call and timestamp field. Added both.

---

## Prompt 8 — main.py Entry Point

```
Implement main.py for the Flashcard Quizzer CLI.

Use argparse with these flags:
- -f / --file (required): path to JSON flashcard file
- -m / --mode: choices from QuizModeFactory.available_modes(), default from config
- --export: optional path for session export (infer JSON/CSV from extension)
- --config: path to config file (default: "config.json")
- --no-color: store_true flag to disable colour
- --stats: store_true flag to print deck info and exit without running quiz

Workflow:
1. load_config(args.config) -> AppConfig
2. setup logging from config.log_level
3. load_flashcards(args.file) -> list[FlashCard]
4. If --stats: print deck info and exit
5. QuizModeFactory.create(args.mode) -> mode
6. SessionStats() -> stats observer
7. QuizSession(mode, cards, listeners=[stats])
8. Interactive loop: next_card -> print_card_prompt -> input() -> record_answer
   -> print_correct/incorrect. Handle "exit" input and KeyboardInterrupt gracefully.
9. session.end_session() -> display_stats_table
10. If --export: export_session(...)

Error handling:
- FlashCardLoadError: print message (no traceback) and sys.exit(1)
- KeyboardInterrupt: print_goodbye and sys.exit(0)
- ExportError: print warning but do not crash (export failure is non-fatal)

All functions have type hints.
```

**Result:** Correct. Added missing return type annotation on `_build_parser`.

---

## Prompt 9 — Test Suite for Data Loader

```
Write pytest tests for utils/data_loader.py in tests/test_flashcard_loader.py.

Test classes:
- TestFlashCard: test valid creation, custom weight, empty front raises, whitespace
  front raises, empty back raises, whitespace back raises
- TestLoadFlashcardsArrayFormat: test loading a valid array-format JSON file
- TestLoadFlashcardsObjectFormat: test loading a valid {"cards":[...]} JSON file
- TestLoadFlashcardsErrorCases:
  * test_load_invalid_json: file with "{bad json" content
  * test_load_missing_field_front: card missing "front" key raises FlashCardLoadError
  * test_load_missing_field_back: card missing "back" key raises FlashCardLoadError
  * test_load_nonexistent_file: non-existent path raises FlashCardLoadError
  * test_load_empty_deck: empty list raises FlashCardLoadError
  * test_load_wrong_structure: a raw JSON string raises FlashCardLoadError

Use tempfile for creating test JSON files. Use pytest.raises for exception tests.
All test function names must describe what is being tested.
```

**Result:** 3 assertions wrong (wrong exception type, wrong JSON for "invalid"
test, wrong expectation for capitalised keys). Fixed all 3.

---

## Prompt 10 — Test Suite for Quiz Modes

```
Write pytest tests for utils/quiz_engine.py in tests/test_quiz_modes.py.

Cover:
- QuizModeFactory: returns correct class for each mode string, case-insensitive,
  strips whitespace, raises ValueError for unknown mode
- SequentialMode: cards served in original order
- RandomMode: shuffles (with seeded random for determinism), serves all cards
- AdaptiveMode: 
  * Cards answered incorrectly are re-queued
  * Cards answered correctly are not repeated
  * Session ends only when all cards answered correctly
  * Re-queued card weight is incremented
- QuizSession: record_answer returns True for correct, False for wrong;
  listeners are notified; end_session calls on_session_end

Use a make_cards(n) helper fixture.
```

**Result:** Correct. Accepted as-is.

---

## Prompt 11 — Integration Tests

```
Write integration tests in tests/test_integration.py that simulate complete
quiz sessions end-to-end.

Test scenarios:
1. test_full_session_all_correct: 3 cards, all correct answers, stats = 3/3, 100%
2. test_full_session_all_wrong: with SequentialMode (finite), record wrong answers,
   check accuracy = 0%, missed list populated
3. test_full_session_mixed_answers: some right, some wrong, check accuracy calculation
4. test_full_session_from_json_file: write a temp JSON file, load it, run a session
5. test_adaptive_session_terminates: with AdaptiveMode, answer all correctly
   eventually — verify session ends and stats are correct
6. test_stats_observer_notified: verify on_answer and on_session_end both called

Use real SessionStats and QuizSession — no mocking of the core logic.
```

**Result:** Correct. Accepted with minor fixture naming tweak.

---

## Prompt 12 — Linting and Type-Check Fixes

```
Review the codebase for flake8 and mypy --strict issues. Fix:
1. Any lines over 99 characters
2. Unused imports
3. Missing return type annotations
4. Inconsistent Optional[T] vs T | None usage (standardise on T | None)
5. Any mypy errors in strict mode

Report what you find and apply the fixes.
```

**Result:** Fixed `TYPE_CHECKING` block, union syntax, and `_build_parser`
return type. Codebase now passes all quality checks.
