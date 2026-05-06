"""Terminal UI utilities for the Flashcard Quizzer.

All output functions accept an optional ``color`` flag so that colour can be
disabled for non-TTY environments or when the user passes ``--no-color``.
This also makes the functions straightforward to test by inspecting captured
output without worrying about ANSI escape codes.
"""

import sys
from typing import Union

try:
    from colorama import Fore, Style, init as colorama_init

    colorama_init(autoreset=True)
    _COLORAMA_AVAILABLE = True
except ImportError:  # pragma: no cover
    _COLORAMA_AVAILABLE = False

try:
    from tabulate import tabulate

    _TABULATE_AVAILABLE = True
except ImportError:  # pragma: no cover
    _TABULATE_AVAILABLE = False

from utils.stats_tracker import SessionStats

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_GREEN = "\033[92m"
_RED = "\033[91m"
_YELLOW = "\033[93m"
_CYAN = "\033[96m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


def _green(text: str, color: bool) -> str:
    if not color:
        return text
    if _COLORAMA_AVAILABLE:
        return f"{Fore.GREEN}{Style.BRIGHT}{text}{Style.RESET_ALL}"
    return f"{_GREEN}{_BOLD}{text}{_RESET}"  # pragma: no cover


def _red(text: str, color: bool) -> str:
    if not color:
        return text
    if _COLORAMA_AVAILABLE:
        return f"{Fore.RED}{Style.BRIGHT}{text}{Style.RESET_ALL}"
    return f"{_RED}{_BOLD}{text}{_RESET}"  # pragma: no cover


def _yellow(text: str, color: bool) -> str:
    if not color:
        return text
    if _COLORAMA_AVAILABLE:
        return f"{Fore.YELLOW}{text}{Style.RESET_ALL}"
    return f"{_YELLOW}{text}{_RESET}"  # pragma: no cover


def _cyan(text: str, color: bool) -> str:
    if not color:
        return text
    if _COLORAMA_AVAILABLE:
        return f"{Fore.CYAN}{text}{Style.RESET_ALL}"
    return f"{_CYAN}{text}{_RESET}"  # pragma: no cover


# ---------------------------------------------------------------------------
# Public UI functions
# ---------------------------------------------------------------------------


def print_welcome(mode: str, total: int, color: bool = True) -> None:
    """Print a welcome banner at the start of a quiz session.

    Args:
        mode: The quiz mode name (e.g. ``"adaptive"``).
        total: Total number of cards in the deck.
        color: Whether to use ANSI colour codes.
    """
    border = "=" * 50
    print(_cyan(border, color))
    print(_cyan("   THE FLASHCARD QUIZZER", color))
    print(_cyan(f"   Mode: {mode.capitalize()}  |  Cards: {total}", color))
    print(_cyan("   Type 'exit' at any time to quit", color))
    print(_cyan(border, color))
    print()


def print_card_prompt(current: int, total: int, front: str, color: bool = True) -> None:
    """Print the card question with a progress indicator.

    Args:
        current: Current question number (1-based).
        total: Total questions in the session (may grow in adaptive mode).
        front: The front text of the card.
        color: Whether to use ANSI colour codes.
    """
    progress = f"[{current}/{total}]"
    print(_yellow(f"\n{progress} {front}", color))


def print_correct(color: bool = True) -> None:
    """Print a 'Correct!' message in green.

    Args:
        color: Whether to use ANSI colour codes.
    """
    print(_green("  ✓  Correct!", color))


def print_incorrect(correct_answer: str, color: bool = True) -> None:
    """Print an 'Incorrect' message in red, revealing the correct answer.

    Args:
        correct_answer: The expected answer to display.
        color: Whether to use ANSI colour codes.
    """
    print(_red(f"  ✗  Incorrect. The answer is: {correct_answer}", color))


def print_goodbye(color: bool = True) -> None:
    """Print a farewell message when the user exits early.

    Args:
        color: Whether to use ANSI colour codes.
    """
    print(_yellow("\n\nQuitting… See you next time!", color))


def display_stats_table(stats: SessionStats, color: bool = True) -> None:
    """Print a formatted summary table at the end of a quiz session.

    Uses *tabulate* if available; falls back to a plain-text table otherwise.

    Args:
        stats: The :class:`~utils.stats_tracker.SessionStats` observer.
        color: Whether to use ANSI colour codes.
    """
    print()
    print(_cyan("=" * 50, color))
    print(_cyan("  QUIZ COMPLETE — Session Summary", color))
    print(_cyan("=" * 50, color))

    headers = ["Metric", "Value"]
    accuracy_str = f"{stats.accuracy():.1f}%"
    rows: list[tuple[str, Union[int, str]]] = [
        ("Total Questions", stats.total),
        ("Correct Answers", stats.correct_count),
        ("Incorrect Answers", stats.incorrect_count()),
        ("Accuracy", accuracy_str),
    ]

    if _TABULATE_AVAILABLE:
        print(tabulate(rows, headers=headers, tablefmt="rounded_outline"))
    else:  # pragma: no cover
        col_w = 22
        print(f"  {'Metric':<{col_w}} {'Value'}")
        print(f"  {'-' * col_w} -----")
        for row in rows:
            print(f"  {str(row[0]):<{col_w}} {row[1]}")

    if stats.missed:
        print()
        header = _red("  Terms to review:", color)
        print(header)
        for card in stats.missed:
            print(f"    • {card.front}  →  {card.back}")
    else:
        print(_green("\n  Perfect score! No terms to review.", color))

    print()


def prompt_answer(question_text: str) -> str:
    """Prompt the user for an answer, reading from stdin.

    Prints the prompt string and reads a single line. Returns the raw input
    so callers can check for the ``"exit"`` keyword or compare against the
    card's back.

    Args:
        question_text: The label to display before the input cursor
            (e.g. ``"Your answer"``).

    Returns:
        The stripped string entered by the user.

    Raises:
        EOFError: Propagated when stdin is exhausted (e.g. piped input).
    """
    return input(f"  {question_text}: ").strip()


def print_error(message: str, color: bool = True) -> None:
    """Print an error message to stderr in red.

    Args:
        message: The error text.
        color: Whether to use ANSI colour codes.
    """
    print(_red(f"Error: {message}", color), file=sys.stderr)
