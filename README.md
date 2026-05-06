# The Flashcard Quizzer

A production-ready CLI application for memorising flashcards — built as the
capstone project for Udacity's AI Engineering course. The app demonstrates
**Strategy**, **Factory**, and **Observer** design patterns, modular
architecture, full type-hint coverage, and a pytest suite exceeding 90%
code coverage.

---

## Features

| Feature | Details |
|---|---|
| **3 Quiz Modes** | Sequential, Random, Adaptive |
| **Adaptive Mode** | Re-queues wrong cards until mastered |
| **Color Output** | Green ✓ / Red ✗ feedback via `colorama` |
| **Session Stats** | Accuracy %, totals, missed-terms table via `tabulate` |
| **Export Results** | Save session summary to `.json` or `.csv` |
| **Config File** | Optional `config.json` overrides defaults |
| **Both JSON Formats** | Array `[{...}]` or wrapper `{"cards":[...]}` |
| **Graceful Errors** | Friendly messages, no raw tracebacks |
| **Design Patterns** | Strategy + Factory + Observer |
| **Type Safety** | 100% type-annotated, `mypy --strict` clean |
| **>90% Test Coverage** | 101 tests across 5 test files |

---

## Getting Started

### Prerequisites

- Python 3.11 or higher
- pip

### Installation

```bash
# 1. Clone / unzip the project
cd flashcard_quizzer

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Running the App

```bash
# Adaptive quiz on Python basics (recommended for first run)
python main.py -f data/python_basics.json -m adaptive

# Random quiz on server acronyms
python main.py -f data/server_acronyms.json -m random

# Sequential quiz, export results to JSON
python main.py -f data/python_basics.json -m sequential --export results.json

# Export as CSV instead
python main.py -f data/python_basics.json --export results.csv

# Disable colour output (useful for log redirection)
python main.py -f data/python_basics.json --no-color

# Use a custom config file
python main.py -f data/python_basics.json --config myconfig.json

# Show help
python main.py --help
```

### CLI Flags

| Flag | Description |
|---|---|
| `-f / --file FILE` | **(Required)** Path to a JSON flashcard file |
| `-m / --mode MODE` | Quiz mode: `sequential`, `random`, `adaptive` (default: `sequential`) |
| `--export FILE` | Export session summary; format inferred from `.json` / `.csv` extension |
| `--config FILE` | Path to JSON config file (default: `config.json`) |
| `--no-color` | Disable ANSI colour output |
| `--stats` | Print deck stats and exit without running a quiz |

---

## Flashcard JSON Format

The app accepts **both** of these formats:

**Array format** (simple list):
```json
[
  { "front": "What does RAM stand for?", "back": "Random Access Memory" },
  { "front": "What is a NIC?",           "back": "Network Interface Card" }
]
```

**Object format** (wrapper with `cards` key):
```json
{
  "cards": [
    { "front": "What does RAM stand for?", "back": "Random Access Memory" }
  ]
}
```

---

## Configuration (optional)

Create a `config.json` in the project root to override defaults:

```json
{
  "color_enabled": true,
  "export_enabled": false,
  "export_path": "quiz_results.json",
  "export_format": "json",
  "log_level": "WARNING",
  "default_mode": "sequential"
}
```

Unknown keys are warned about and ignored; missing keys fall back to defaults.

---

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage report (HTML output in htmlcov/)
pytest --cov=utils --cov=main --cov-report=html --cov-report=term-missing

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_quiz_modes.py -v
```

### Test Suite Overview

| File | What it covers |
|---|---|
| `tests/test_flashcard_loader.py` | Data loading, validation, both JSON formats, error cases |
| `tests/test_quiz_modes.py` | Strategy Pattern, Factory Pattern, all three modes |
| `tests/test_integration.py` | End-to-end session simulation with stats |
| `tests/test_stats_tracker.py` | Observer Pattern, accuracy calculation |
| `tests/test_ui.py` | Terminal output, color/no-color paths |

---

## Code Quality

```bash
# Format code
black .

# Sort imports
isort .

# Lint
flake8 .

# Type check
mypy .

# Run everything
black . && isort . && flake8 . && mypy . && pytest
```

---

## Project Structure

```
flashcard_quizzer/
├── main.py                    # CLI entry point (argparse)
├── requirements.txt           # Python dependencies
├── setup.cfg                  # flake8 / mypy / pytest / coverage config
├── config.json                # (optional) runtime configuration
├── data/
│   ├── python_basics.json     # Sample deck: Python fundamentals
│   └── server_acronyms.json   # Sample deck: Server/network acronyms
├── utils/
│   ├── __init__.py
│   ├── data_loader.py         # FlashCard dataclass + JSON loader/validator
│   ├── quiz_engine.py         # Strategy + Factory patterns + QuizSession
│   ├── stats_tracker.py       # Observer pattern + SessionStats
│   ├── ui.py                  # Colorized terminal output + stats table
│   ├── config.py              # AppConfig dataclass + config loader
│   └── exporter.py            # JSON / CSV session export
├── tests/
│   ├── __init__.py
│   ├── test_flashcard_loader.py
│   ├── test_quiz_modes.py
│   ├── test_integration.py
│   ├── test_stats_tracker.py
│   └── test_ui.py
└── docs/
    ├── ai_edit_log.md         # AI interaction log (6 documented examples)
    └── report_template.md     # Final project report
```

---

## Design Patterns

### Strategy Pattern (`quiz_engine.py`)
`QuizMode` is the abstract strategy. `SequentialMode`, `RandomMode`, and
`AdaptiveMode` are concrete strategies, each encapsulating a different card
ordering algorithm. Adding a new mode (e.g. Spaced Repetition) requires only
a new subclass — no changes to `QuizSession` or `main.py`.

### Factory Pattern (`quiz_engine.py`)
`QuizModeFactory.create("adaptive")` maps user-supplied strings to the correct
strategy class, centralising construction and hiding instantiation details.

### Observer Pattern (`stats_tracker.py`, `quiz_engine.py`)
`QuizObserver` is the abstract observer. `SessionStats` accumulates per-session
metrics. `QuizSession` notifies all registered observers after each answer and
at session end, keeping stats tracking fully decoupled from the quiz loop.

---

## Dependencies

| Package | Purpose |
|---|---|
| `colorama` | Cross-platform ANSI color output |
| `tabulate` | Formatted stats table |
| `pytest` | Test framework |
| `pytest-cov` | Coverage reporting |
| `flake8` | Linting |
| `black` | Code formatting |
| `isort` | Import sorting |
| `mypy` | Static type checking |

---

## Built With

- [Python 3.11+](https://www.python.org/)
- [pytest](https://docs.pytest.org/) — Testing framework
- [colorama](https://github.com/tartley/colorama) — Terminal colors
- [tabulate](https://github.com/astanin/python-tabulate) — Table formatting
- [black](https://black.readthedocs.io/) — Code formatter
- [flake8](https://flake8.pycqa.org/) — Linter
- [mypy](https://mypy.readthedocs.io/) — Type checker
