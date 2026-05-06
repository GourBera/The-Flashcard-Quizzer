"""Entry point for the Flashcard Quizzer CLI application.

Usage examples::

    # Play an adaptive quiz on Python basics
    python main.py -f data/python_basics.json -m adaptive

    # Play a random quiz on server acronyms and export results to JSON
    python main.py -f data/server_acronyms.json -m random --export results.json

    # Show final stats only (no interactive quiz; useful for testing)
    python main.py -f data/python_basics.json --stats

    # Disable colour output (useful for log redirection)
    python main.py -f data/python_basics.json --no-color

    # Use a custom config file
    python main.py -f data/python_basics.json --config myconfig.json
"""

import argparse
import logging
import os
import sys

from utils.config import AppConfig, load_config
from utils.data_loader import FlashCardLoadError, load_flashcards
from utils.exporter import ExportError, export_session
from utils.quiz_engine import QuizModeFactory, QuizSession
from utils.stats_tracker import SessionStats
from utils import ui


def _build_parser(default_mode: str) -> argparse.ArgumentParser:
    """Build and return the argument parser.

    Args:
        default_mode: The default quiz mode from the loaded config.

    Returns:
        A configured :class:`argparse.ArgumentParser`.
    """
    parser = argparse.ArgumentParser(
        prog="flashcard_quizzer",
        description=(
            "The Flashcard Quizzer — a CLI tool for memorising "
            "flashcards in Sequential, Random, or Adaptive mode."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python main.py -f data/python_basics.json -m adaptive\n"
            "  python main.py -f data/server_acronyms.json -m random "
            "--export results.json\n"
        ),
    )
    parser.add_argument(
        "-f",
        "--file",
        required=True,
        metavar="FILE",
        help="Path to a JSON flashcard file.",
    )
    parser.add_argument(
        "-m",
        "--mode",
        default=default_mode,
        choices=QuizModeFactory.available_modes(),
        metavar="MODE",
        help=(
            f"Quiz mode: {', '.join(QuizModeFactory.available_modes())}. "
            f"(default: {default_mode})"
        ),
    )
    parser.add_argument(
        "--export",
        metavar="FILE",
        default=None,
        help=(
            "Export session results to this file. "
            "Format is inferred from the extension (.json or .csv)."
        ),
    )
    parser.add_argument(
        "--config",
        metavar="FILE",
        default="config.json",
        help="Path to a JSON configuration file (default: config.json).",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        default=False,
        help="Disable ANSI colour output.",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        default=False,
        help=(
            "Print deck info and exit without running the interactive quiz. "
            "Useful for previewing a card file."
        ),
    )
    parser.add_argument(
        "--log-level",
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Override the logging level.",
    )
    return parser


def _configure_logging(level: str) -> None:
    """Configure the root logger.

    Args:
        level: A logging level string (e.g. ``"DEBUG"``).
    """
    numeric = getattr(logging, level.upper(), logging.WARNING)
    logging.basicConfig(
        level=numeric,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _infer_export_format(path: str) -> str:
    """Infer the export format from the file extension.

    Args:
        path: The export file path.

    Returns:
        ``"csv"`` if the extension is ``.csv``; ``"json"`` otherwise.
    """
    _, ext = os.path.splitext(path)
    return "csv" if ext.lower() == ".csv" else "json"


def run_quiz(
    cards_path: str,
    mode_str: str,
    config: AppConfig,
    export_path: str | None = None,
) -> int:
    """Load cards, run the interactive quiz loop, and display final stats.

    Args:
        cards_path: Path to the flashcard JSON file.
        mode_str: Quiz mode string (``"sequential"``, ``"random"``,
            or ``"adaptive"``).
        config: The loaded :class:`~utils.config.AppConfig`.
        export_path: Optional path to export session results.

    Returns:
        Exit code — ``0`` on clean finish or user exit, ``1`` on error.
    """
    color = config.color_enabled

    # ------------------------------------------------------------------
    # Load cards
    # ------------------------------------------------------------------
    try:
        cards = load_flashcards(cards_path)
    except FlashCardLoadError as exc:
        ui.print_error(str(exc), color=color)
        return 1

    # ------------------------------------------------------------------
    # Build session
    # ------------------------------------------------------------------
    try:
        quiz_mode = QuizModeFactory.create(mode_str)
    except ValueError as exc:
        ui.print_error(str(exc), color=color)
        return 1

    stats = SessionStats()
    session = QuizSession(mode=quiz_mode, cards=cards, listeners=[stats])

    ui.print_welcome(mode=mode_str, total=len(cards), color=color)

    # ------------------------------------------------------------------
    # Quiz loop
    # ------------------------------------------------------------------
    question_number = 0
    try:
        while True:
            card = session.next_card()
            if card is None:
                break
            question_number += 1

            # Estimate total: real count for sequential/random; dynamic for adaptive
            deck_size = len(cards)
            ui.print_card_prompt(
                current=question_number,
                total=deck_size,
                front=card.front,
                color=color,
            )

            try:
                answer = ui.prompt_answer("Your answer")
            except EOFError:
                # Piped input exhausted
                break

            if answer.lower() == "exit":
                ui.print_goodbye(color=color)
                session.end_session()
                ui.display_stats_table(stats, color=color)
                _maybe_export(stats, export_path, cards_path, mode_str, config, color)
                return 0

            correct = session.record_answer(card, answer)
            if correct:
                ui.print_correct(color=color)
            else:
                ui.print_incorrect(card.back, color=color)

    except KeyboardInterrupt:
        ui.print_goodbye(color=color)

    # ------------------------------------------------------------------
    # End session & stats
    # ------------------------------------------------------------------
    session.end_session()
    ui.display_stats_table(stats, color=color)
    _maybe_export(stats, export_path, cards_path, mode_str, config, color)
    return 0


def _maybe_export(
    stats: SessionStats,
    export_path: str | None,
    cards_path: str,
    mode_str: str,
    config: AppConfig,
    color: bool,
) -> None:
    """Export session results if an export path is configured.

    Args:
        stats: The session statistics.
        export_path: CLI-supplied export path (overrides config).
        cards_path: The flashcard file path (used as deck label).
        mode_str: The quiz mode label.
        config: The application config.
        color: Whether to use coloured output in error messages.
    """
    effective_path = export_path or (
        config.export_path if config.export_enabled else None
    )
    if not effective_path:
        return

    fmt = _infer_export_format(effective_path)
    try:
        export_session(
            stats=stats,
            filepath=effective_path,
            fmt=fmt,
            deck_name=os.path.basename(cards_path),
            mode=mode_str,
        )
    except ExportError as exc:
        ui.print_error(str(exc), color=color)


def main(argv: list[str] | None = None) -> int:
    """Application entry point.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Exit code.
    """
    # Load config first so we can use config defaults in the parser
    # We do a minimal pre-parse to find --config before full parsing.
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--config", default="config.json")
    pre_parser.add_argument("--no-color", action="store_true", default=False)
    pre_parser.add_argument("--log-level", default=None)
    known, _ = pre_parser.parse_known_args(argv)

    config = load_config(known.config)

    # Resolve log level: CLI flag > config file
    log_level = known.log_level or config.log_level
    _configure_logging(log_level)

    # Apply --no-color flag
    if known.no_color:
        config.color_enabled = False

    parser = _build_parser(default_mode=config.default_mode)
    args = parser.parse_args(argv)

    # Re-apply no-color from full parse
    if args.no_color:
        config.color_enabled = False

    # --stats: preview mode, no quiz
    if args.stats:
        try:
            cards = load_flashcards(args.file)
        except FlashCardLoadError as exc:
            ui.print_error(str(exc), color=config.color_enabled)
            return 1
        print(f"\nDeck: {args.file}")
        print(f"Cards: {len(cards)}")
        for i, card in enumerate(cards, start=1):
            print(f"  {i:>3}. {card.front}")
        return 0

    return run_quiz(
        cards_path=args.file,
        mode_str=args.mode,
        config=config,
        export_path=args.export,
    )


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
