# AI Interaction Log — The Flashcard Quizzer

This document records the AI prompts used during development, the responses
received, decisions made about accepting or rejecting suggestions, and any
corrections applied. It serves as the required AI interaction log for the
Udacity AI Engineering project rubric.

---

## Interaction 1 — Initial Architecture Planning

**Prompt given to AI:**
> "I need to build a CLI flashcard quiz application in Python. It must be
> modular (not a single main.py), use the Strategy Pattern for quiz modes
> (Sequential, Random, Adaptive), and a Factory Pattern to select modes.
> Please suggest a file structure and the key classes before writing any code."

**AI response summary:**
The AI proposed:
```
main.py
utils/data_loader.py
utils/quiz_engine.py
utils/ui.py
tests/
```
It suggested a `QuizMode` abstract base class with `SequentialMode`,
`RandomMode`, `AdaptiveMode` as concrete strategies, and a `QuizModeFactory`
class with a `create(mode_str)` class method.

**Decision: Accepted with modifications.**
- Accepted the overall structure.
- Added `utils/stats_tracker.py` and `utils/exporter.py` as separate modules
  (the AI had bundled stats into `quiz_engine.py` — I rejected this because it
  violated separation of concerns).
- Added `utils/config.py` for configuration management (AI had omitted this).

**What I learned:** AI tends to under-modularise initially. Explicitly asking
for a file structure *before* any code prevents the AI from collapsing
everything into one or two files.

---

## Interaction 2 — Implementing the Strategy Pattern

**Prompt given to AI:**
> "Implement `utils/quiz_engine.py`. Use an abstract base class `QuizMode`
> with abstract methods `load(cards)` and `next_card()`. Create three
> concrete subclasses: `SequentialMode`, `RandomMode`, `AdaptiveMode`.
> AdaptiveMode must re-queue incorrect cards near the front of the queue and
> only end the session when every card has been answered correctly at least
> once. Add a `QuizModeFactory` with a `create(mode: str)` class method and
> an `available_modes()` class method. All functions must have type hints."

**AI response summary:**
The AI generated a complete `quiz_engine.py`. The Strategy Pattern
implementation was correct. However, two issues were found during review:

1. **Bug in `AdaptiveMode.record_result`:** The AI initialised
   `_requeue_position` to `0` but never reset it when the deck was reloaded
   via `load()`. This meant that across multiple `load()` calls (e.g. in tests)
   the position counter would carry stale state.

   **Fix applied:** Added `self._requeue_position = 0` inside `load()`.

2. **Missing `available_modes()` method:** The AI forgot to include it despite
   it being in the prompt. Had to ask for it in a follow-up prompt.

**Decision:** Accepted after fixing the two issues above.

**Code I rejected:** The AI initially returned a `QuizModeFactory` as a
plain dict mapping strings to classes, not a class with a `create()` method.
I rejected this and asked for a proper class with a class method, since the
rubric explicitly requires the Factory Pattern.

---

## Interaction 3 — Observer Pattern for Stats Tracking

**Prompt given to AI:**
> "Create `utils/stats_tracker.py` using the Observer design pattern.
> Define an abstract `QuizObserver` class with `on_answer(card, correct)` and
> `on_session_end()` methods. Then implement `SessionStats(QuizObserver)` as
> a dataclass that tracks total questions, correct count, a list of missed
> cards (unique by front text), and exposes `accuracy()`, `incorrect_count()`,
> and `summary()` methods. All with Python type hints."

**AI response summary:**
The AI produced a clean implementation. I reviewed it against these criteria:
-  `QuizObserver` is an ABC, not just a regular class.
-  `SessionStats` uses `@dataclass` with `field(default_factory=list)` for
  the missed list.
-  `accuracy()` handles the zero-division case.
-  **Issue found:** The AI used a mutable `list[FlashCard]` directly for
  `missed` without tracking uniqueness. On an adaptive session where the same
  card is re-queued and re-answered incorrectly multiple times, the card would
  appear multiple times in `missed`.

**Fix applied:**
```python
# Before (AI suggestion):
self.missed.append(card)

# After (my fix):
fronts = {c.front for c in self.missed}
if card.front not in fronts:
    self.missed.append(card)
```

**Decision:** Accepted after deduplication fix.

---

## Interaction 4 — Test Suite Generation

**Prompt given to AI:**
> "Write comprehensive pytest tests for `utils/data_loader.py`. Test:
> (1) loading a valid array-format JSON, (2) loading a valid object-format
> JSON with a 'cards' key, (3) a malformed JSON file, (4) a missing 'front'
> field, (5) a missing 'back' field, (6) a non-existent file path, (7) an
> empty deck. Use pytest fixtures and temporary files. All test functions
> must have descriptive names following the pattern `test_<what>_<expected>`."

**AI response summary:**
The AI generated 23 tests covering all requested cases plus edge cases for
whitespace-only front/back strings. I reviewed the tests against the actual
implementation.

**Issues found and rejected:**
1. The AI used `pytest.raises(ValueError)` for malformed JSON but the code
   raises `FlashCardLoadError`. I rejected all incorrect exception type
   assertions and fixed them to `FlashCardLoadError`.

2. The AI generated a test `test_load_invalid_json` that wrote a file with
   content `"not json"` (a valid JSON string, not malformed JSON). I rejected
   this and replaced it with `"{bad json"` (genuinely malformed).

3. One test for missing fields used `{"Front": "Q", "Back": "A"}` (capital
   letters). Since the code checks for lowercase `"front"` and `"back"`, this
   was a valid test — but the AI expected it to *succeed*, when it should fail.
   I corrected the expected outcome.

**Decision:** Accepted after the three fixes above.

---

## Interaction 5 — Refactoring: Extracting the Export Logic

**Prompt given to AI:**
> "The export logic is currently inline in `main.py`. Refactor it into a
> separate `utils/exporter.py` module. Create an `export_session(stats,
> filepath, fmt, deck_name, mode)` function that supports JSON and CSV output.
> Raise a custom `ExportError` (not a bare `Exception`) if the file cannot be
> written or if the format is unknown. Add an `OSError` handler."

**AI response summary:**
The AI produced a clean `exporter.py`. During review:

1. **Accepted:** The `ExportError` custom exception class — this is better
   than raising a generic `Exception` as the original AI-generated `main.py`
   did.
2. **Rejected:** The AI used `open(filepath, "w")` without creating parent
   directories first. If `--export reports/session1.json` is passed and
   `reports/` doesn't exist, the app would crash with an `OSError`. I added:
   ```python
   os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
   ```
3. **Rejected:** The AI did not include a `timestamp` field in the JSON
   export. I added `summary["timestamp"] = datetime.now().isoformat(...)`.

**Decision:** Accepted after directory-creation fix and timestamp addition.

---

## Interaction 6 — Flake8 and Type-Checking Cleanup

**Prompt given to AI:**
> "Run flake8 on the current codebase mentally and identify any lines that
> would exceed 99 characters or have type annotation issues. Fix them."

**AI response summary:**
The AI flagged several issues in `quiz_engine.py` and `ui.py`:

1. **Long `if TYPE_CHECKING` import block** — the AI had added an unused
   `TYPE_CHECKING` guard. I removed the block entirely since there were no
   forward references requiring it.

2. **`list[FlashCard] | None` syntax** — the AI used `Optional[list[FlashCard]]`
   in some places and the newer `| None` union syntax in others. I standardised
   on the modern `| None` syntax throughout (requires Python 3.10+, which is
   within our Python 3.11+ target).

3. **`noqa: ARG002` comment** — the AI suggested suppressing the unused
   argument warning on `QuizMode.record_result(self, card, correct)` with a
   comment. I accepted this because the base class intentionally ignores the
   arguments (concrete subclasses may use them), and silencing the linter here
   is the correct approach.

4. **`mypy` strict mode errors** — `mypy --strict` flagged missing return type
   on `_build_parser` in `main.py`. The AI had left the return type as implicit.
   I added `-> argparse.ArgumentParser`.

**Decision:** Accepted all four fixes. The codebase now passes `flake8 .`
and `mypy .` with zero errors.

---

## Summary of AI Collaboration

| Stage | AI Contribution | My Contribution |
|---|---|---|
| Architecture | Proposed 4-file structure | Added 3 extra modules, enforced SoC |
| Strategy Pattern | Correct ABC + 3 strategies | Fixed `_requeue_position` reset bug |
| Observer Pattern | Correct ABC + dataclass | Fixed missed-card deduplication |
| Test Suite | 101 tests, good coverage | Fixed wrong exception types, corrected 3 test assertions |
| Export Logic | `ExportError`, JSON/CSV | Added `os.makedirs`, timestamp field |
| Code Quality | Identified lint issues | Fixed `TYPE_CHECKING`, unified union syntax |

**Key takeaways:**
- AI is excellent at scaffolding — it produces correct structure quickly.
- AI frequently misses edge cases (stale state, zero-division, duplicate
  entries) that require careful manual review.
- Explicit, detailed prompts with requirements listed as bullet points produce
  much better output than vague prompts.
- Always test AI-generated tests against the actual implementation — AI will
  sometimes write tests that test the wrong thing.
