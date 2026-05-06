"""Tests for utils/ui.py and utils/config.py and utils/exporter.py.

Covers:
- UI output functions (no crashes, correct content)
- Config loading with defaults and partial overrides
- Export to JSON and CSV
- Export error handling
"""

import csv
import json
import os
import tempfile

import pytest

from utils.config import AppConfig, load_config
from utils.data_loader import FlashCard
from utils.exporter import ExportError, export_session
from utils.stats_tracker import SessionStats
from utils import ui


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_stats(correct: int = 3, wrong: int = 1) -> SessionStats:
    stats = SessionStats()
    for i in range(correct):
        stats.on_answer(FlashCard(f"Q{i}", f"A{i}"), correct=True)
    for i in range(wrong):
        stats.on_answer(FlashCard(f"M{i}", f"B{i}"), correct=False)
    return stats


def _write_config(data: dict) -> str:
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    with open(path, "w") as fh:
        json.dump(data, fh)
    return path


# ---------------------------------------------------------------------------
# UI tests
# ---------------------------------------------------------------------------


class TestUI:
    def test_display_stats_no_crash_with_missed(self, capsys) -> None:
        stats = make_stats(correct=2, wrong=2)
        ui.display_stats_table(stats, color=False)
        out = capsys.readouterr().out
        assert "50.0%" in out

    def test_display_stats_perfect_score_message(self, capsys) -> None:
        stats = make_stats(correct=3, wrong=0)
        ui.display_stats_table(stats, color=False)
        out = capsys.readouterr().out
        assert "Perfect" in out

    def test_print_correct_outputs_correct(self, capsys) -> None:
        ui.print_correct(color=False)
        out = capsys.readouterr().out
        assert "Correct" in out

    def test_print_incorrect_shows_answer(self, capsys) -> None:
        ui.print_incorrect("Paris", color=False)
        out = capsys.readouterr().out
        assert "Paris" in out

    def test_print_welcome_shows_mode(self, capsys) -> None:
        ui.print_welcome(mode="adaptive", total=10, color=False)
        out = capsys.readouterr().out
        assert "Adaptive" in out
        assert "10" in out

    def test_print_card_prompt_shows_front(self, capsys) -> None:
        ui.print_card_prompt(current=2, total=5, front="What is DNS?", color=False)
        out = capsys.readouterr().out
        assert "What is DNS?" in out
        assert "2/5" in out

    def test_print_goodbye(self, capsys) -> None:
        ui.print_goodbye(color=False)
        out = capsys.readouterr().out
        assert "Quitting" in out or "bye" in out.lower() or "next time" in out.lower()

    def test_print_error_goes_to_stderr(self, capsys) -> None:
        ui.print_error("Something went wrong", color=False)
        err = capsys.readouterr().err
        assert "Something went wrong" in err

    def test_prompt_answer_returns_stripped_input(self, monkeypatch) -> None:
        monkeypatch.setattr("builtins.input", lambda _: "  Paris  ")
        result = ui.prompt_answer("Your answer")
        assert result == "Paris"

    def test_display_stats_no_missed_cards(self, capsys) -> None:
        stats = make_stats(correct=5, wrong=0)
        ui.display_stats_table(stats, color=False)
        out = capsys.readouterr().out
        assert "100.0%" in out

    # --- Color-enabled paths (covers the colorama branches) -----------------

    def test_display_stats_with_color(self, capsys) -> None:
        stats = make_stats(correct=3, wrong=1)
        ui.display_stats_table(stats, color=True)
        out = capsys.readouterr().out
        assert "75.0%" in out

    def test_print_correct_with_color(self, capsys) -> None:
        ui.print_correct(color=True)
        out = capsys.readouterr().out
        assert "Correct" in out

    def test_print_incorrect_with_color(self, capsys) -> None:
        ui.print_incorrect("Berlin", color=True)
        out = capsys.readouterr().out
        assert "Berlin" in out

    def test_print_welcome_with_color(self, capsys) -> None:
        ui.print_welcome(mode="random", total=5, color=True)
        out = capsys.readouterr().out
        assert "5" in out

    def test_print_card_prompt_with_color(self, capsys) -> None:
        ui.print_card_prompt(current=1, total=3, front="Capital of France?", color=True)
        out = capsys.readouterr().out
        assert "France" in out

    def test_print_error_with_color(self, capsys) -> None:
        ui.print_error("oh no", color=True)
        err = capsys.readouterr().err
        assert "oh no" in err


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------


class TestAppConfig:
    def test_defaults_when_no_file(self) -> None:
        config = load_config("/tmp/nonexistent_config_12345.json")
        assert config.color_enabled is True
        assert config.export_enabled is False
        assert config.default_mode == "sequential"
        assert config.log_level == "WARNING"

    def test_partial_override(self) -> None:
        path = _write_config({"color_enabled": False, "default_mode": "adaptive"})
        config = load_config(path)
        assert config.color_enabled is False
        assert config.default_mode == "adaptive"
        assert config.log_level == "WARNING"  # still default

    def test_full_override(self) -> None:
        data = {
            "color_enabled": False,
            "export_enabled": True,
            "export_path": "out.csv",
            "export_format": "csv",
            "log_level": "DEBUG",
            "default_mode": "random",
        }
        path = _write_config(data)
        config = load_config(path)
        assert config.export_enabled is True
        assert config.export_format == "csv"
        assert config.log_level == "DEBUG"

    def test_invalid_json_falls_back_to_defaults(self) -> None:
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        with open(path, "w") as fh:
            fh.write("{invalid json}")
        config = load_config(path)
        assert isinstance(config, AppConfig)
        assert config.color_enabled is True

    def test_non_dict_json_falls_back_to_defaults(self) -> None:
        path = _write_config(["not", "a", "dict"])
        config = load_config(path)
        assert isinstance(config, AppConfig)

    def test_unknown_keys_are_ignored(self) -> None:
        path = _write_config({"unknown_key": "value", "color_enabled": False})
        config = load_config(path)
        assert config.color_enabled is False


# ---------------------------------------------------------------------------
# Exporter tests
# ---------------------------------------------------------------------------


class TestExporter:
    def _temp_path(self, suffix: str = ".json") -> str:
        fd, path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        os.unlink(path)  # remove so exporter creates it fresh
        return path

    def test_export_json_creates_file(self) -> None:
        stats = make_stats(correct=3, wrong=1)
        path = self._temp_path(".json")
        export_session(stats, path, fmt="json")
        assert os.path.exists(path)

    def test_export_json_content(self) -> None:
        stats = make_stats(correct=2, wrong=1)
        path = self._temp_path(".json")
        export_session(stats, path, fmt="json", deck_name="test.json", mode="sequential")
        with open(path) as fh:
            data = json.load(fh)
        assert data["total"] == 3
        assert data["correct"] == 2
        assert data["deck"] == "test.json"
        assert data["mode"] == "sequential"
        assert "timestamp" in data

    def test_export_csv_creates_file(self) -> None:
        stats = make_stats(correct=1, wrong=0)
        path = self._temp_path(".csv")
        export_session(stats, path, fmt="csv")
        assert os.path.exists(path)

    def test_export_csv_content(self) -> None:
        stats = make_stats(correct=2, wrong=1)
        path = self._temp_path(".csv")
        export_session(stats, path, fmt="csv")
        with open(path, newline="") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["total"] == "3"

    def test_export_csv_appends_multiple_sessions(self) -> None:
        path = self._temp_path(".csv")
        for _ in range(3):
            stats = make_stats(correct=1, wrong=0)
            export_session(stats, path, fmt="csv")
        with open(path, newline="") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)
        assert len(rows) == 3

    def test_export_invalid_format_raises(self) -> None:
        stats = make_stats()
        path = self._temp_path(".txt")
        with pytest.raises(ExportError, match="Unknown export format"):
            export_session(stats, path, fmt="xml")

    def test_export_prints_confirmation(self, capsys) -> None:
        stats = make_stats(correct=1, wrong=0)
        path = self._temp_path(".json")
        export_session(stats, path, fmt="json")
        out = capsys.readouterr().out
        assert "exported" in out.lower() or path in out

    def test_export_oserror_raises_export_error(self) -> None:
        """Covers the OSError → ExportError conversion path."""
        from unittest.mock import patch as _patch
        stats = make_stats(correct=1, wrong=0)
        path = self._temp_path(".json")
        with _patch("builtins.open", side_effect=OSError("permission denied")):
            with pytest.raises(ExportError, match="permission denied"):
                export_session(stats, path, fmt="json")
