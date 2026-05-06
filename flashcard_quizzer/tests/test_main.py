"""Tests for main.py.

Covers the CLI entry point: argument parsing, --stats flag, run_quiz
success/failure paths, export flow, and graceful error handling.
"""

import json
import os
import tempfile
from unittest.mock import patch

import main as app_main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_deck(cards: list[dict]) -> str:
    """Write a card list to a temp JSON file and return the path."""
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    with open(path, "w") as fh:
        json.dump(cards, fh)
    return path


_SAMPLE = [
    {"front": "Q1", "back": "A1"},
    {"front": "Q2", "back": "A2"},
]


# ---------------------------------------------------------------------------
# --stats flag
# ---------------------------------------------------------------------------


class TestStatsFlag:
    def test_stats_flag_prints_deck_info(self, capsys) -> None:
        path = _write_deck(_SAMPLE)
        try:
            code = app_main.main(["--file", path, "--stats"])
            captured = capsys.readouterr()
            assert code == 0
            assert "Q1" in captured.out
            assert "Q2" in captured.out
        finally:
            os.unlink(path)

    def test_stats_flag_missing_file(self, capsys) -> None:
        code = app_main.main(["--file", "nonexistent_deck.json", "--stats"])
        assert code == 1
        captured = capsys.readouterr()
        # Error is printed to stderr via print_error
        assert captured.out or captured.err


# ---------------------------------------------------------------------------
# run_quiz — happy path
# ---------------------------------------------------------------------------


class TestRunQuiz:
    def test_run_quiz_all_correct_sequential(self, capsys) -> None:
        path = _write_deck(_SAMPLE)
        # Provide correct answers for both cards, then an empty line (EOFError path)
        answers = ["A1", "A2"]
        with patch("builtins.input", side_effect=answers + [EOFError]):
            code = app_main.main(["--file", path, "--mode", "sequential", "--no-color"])
        os.unlink(path)
        assert code == 0
        out = capsys.readouterr().out
        assert "Correct" in out

    def test_run_quiz_wrong_answer(self, capsys) -> None:
        path = _write_deck([{"front": "Q1", "back": "A1"}])
        with patch("builtins.input", side_effect=["WRONG", EOFError]):
            code = app_main.main(["--file", path, "--mode", "sequential", "--no-color"])
        os.unlink(path)
        assert code == 0
        out = capsys.readouterr().out
        assert "Incorrect" in out

    def test_run_quiz_exit_keyword(self, capsys) -> None:
        path = _write_deck(_SAMPLE)
        with patch("builtins.input", side_effect=["exit"]):
            code = app_main.main(["--file", path, "--mode", "sequential", "--no-color"])
        os.unlink(path)
        assert code == 0
        out = capsys.readouterr().out
        assert "Quitting" in out or "See you" in out

    def test_run_quiz_keyboard_interrupt(self, capsys) -> None:
        path = _write_deck(_SAMPLE)
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            code = app_main.main(["--file", path, "--mode", "sequential", "--no-color"])
        os.unlink(path)
        assert code == 0

    def test_run_quiz_invalid_file(self, capsys) -> None:
        code = app_main.main(["--file", "no_such_file.json", "--mode", "sequential"])
        assert code == 1

    def test_run_quiz_random_mode(self, capsys) -> None:
        path = _write_deck(_SAMPLE)
        with patch("builtins.input", side_effect=["A1", "A2", EOFError]):
            code = app_main.main(["--file", path, "--mode", "random", "--no-color"])
        os.unlink(path)
        assert code == 0

    def test_run_quiz_adaptive_mode(self, capsys) -> None:
        path = _write_deck([{"front": "Q1", "back": "A1"}])
        with patch("builtins.input", side_effect=["A1", EOFError]):
            code = app_main.main(["--file", path, "--mode", "adaptive", "--no-color"])
        os.unlink(path)
        assert code == 0


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


class TestExport:
    def test_export_json(self, capsys, tmp_path) -> None:
        deck_path = _write_deck([{"front": "Q1", "back": "A1"}])
        export_path = str(tmp_path / "results.json")
        with patch("builtins.input", side_effect=["A1", EOFError]):
            code = app_main.main([
                "--file", deck_path,
                "--mode", "sequential",
                "--no-color",
                "--export", export_path,
            ])
        os.unlink(deck_path)
        assert code == 0
        assert os.path.exists(export_path)
        with open(export_path) as fh:
            data = json.load(fh)
        assert data["total"] == 1

    def test_export_csv(self, capsys, tmp_path) -> None:
        deck_path = _write_deck([{"front": "Q1", "back": "A1"}])
        export_path = str(tmp_path / "results.csv")
        with patch("builtins.input", side_effect=["A1", EOFError]):
            code = app_main.main([
                "--file", deck_path,
                "--mode", "sequential",
                "--no-color",
                "--export", export_path,
            ])
        os.unlink(deck_path)
        assert code == 0
        assert os.path.exists(export_path)


# ---------------------------------------------------------------------------
# Helper function coverage
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_infer_export_format_json(self) -> None:
        assert app_main._infer_export_format("out.json") == "json"

    def test_infer_export_format_csv(self) -> None:
        assert app_main._infer_export_format("out.csv") == "csv"

    def test_infer_export_format_default_json(self) -> None:
        assert app_main._infer_export_format("out.txt") == "json"

    def test_configure_logging_does_not_crash(self) -> None:
        app_main._configure_logging("DEBUG")
        app_main._configure_logging("WARNING")

    def test_run_quiz_eof_mid_session(self, capsys) -> None:
        """Covers the EOFError break when input ends before all cards are answered."""
        # 3 cards but only 1 answer — EOFError raised on 2nd prompt
        deck_path = _write_deck([
            {"front": "Q1", "back": "A1"},
            {"front": "Q2", "back": "A2"},
            {"front": "Q3", "back": "A3"},
        ])
        with patch("builtins.input", side_effect=["A1", EOFError]):
            code = app_main.main(["--file", deck_path, "--mode", "sequential", "--no-color"])
        os.unlink(deck_path)
        assert code == 0

    def test_run_quiz_invalid_mode_returns_1(self, capsys) -> None:
        """Covers the ValueError path when the quiz mode string is invalid."""
        from utils.config import AppConfig
        deck_path = _write_deck(_SAMPLE)
        # Bypass argparse by calling run_quiz directly with a bogus mode string
        code = app_main.run_quiz(
            cards_path=deck_path,
            mode_str="bogusmode",
            config=AppConfig(),
        )
        os.unlink(deck_path)
        assert code == 1

    def test_maybe_export_via_config(self, tmp_path) -> None:
        """Covers _maybe_export when config.export_enabled=True (no --export flag)."""
        from utils.config import AppConfig

        export_path = str(tmp_path / "out.json")
        config = AppConfig(export_enabled=True, export_path=export_path)

        deck_path = _write_deck([{"front": "Q", "back": "A"}])
        with (
            patch("builtins.input", side_effect=["A", EOFError]),
            patch("main.load_config", return_value=config),
        ):
            code = app_main.main([
                "--file", deck_path,
                "--mode", "sequential",
                "--no-color",
            ])
        os.unlink(deck_path)
        assert code == 0
        assert os.path.exists(export_path)

    def test_maybe_export_export_error_prints_message(self, capsys, tmp_path) -> None:
        """Covers ExportError handling in _maybe_export."""
        from utils.exporter import ExportError

        deck_path = _write_deck([{"front": "Q", "back": "A"}])
        export_path = str(tmp_path / "out.json")
        with (
            patch("builtins.input", side_effect=["A", EOFError]),
            patch("main.export_session", side_effect=ExportError("disk full")),
        ):
            code = app_main.main([
                "--file", deck_path,
                "--mode", "sequential",
                "--no-color",
                "--export", export_path,
            ])
        os.unlink(deck_path)
        assert code == 0  # Export error is non-fatal
        captured = capsys.readouterr()
        assert "disk full" in captured.out or "disk full" in captured.err
