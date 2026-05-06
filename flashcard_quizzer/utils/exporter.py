"""Session result exporter for the Flashcard Quizzer.

Supports exporting quiz session summaries to JSON or CSV so users can track
their progress over time and share results.
"""

import csv
import json
import logging
import os
from datetime import datetime

from utils.stats_tracker import SessionStats

logger = logging.getLogger(__name__)


class ExportError(Exception):
    """Raised when a session export operation fails."""

    pass


def export_session(
    stats: SessionStats,
    filepath: str,
    fmt: str = "json",
    deck_name: str = "",
    mode: str = "",
) -> None:
    """Export a session summary to a file in JSON or CSV format.

    Args:
        stats: The :class:`~utils.stats_tracker.SessionStats` observer
            containing the session results.
        filepath: Destination file path (created if it doesn't exist).
        fmt: Export format — ``"json"`` (default) or ``"csv"``.
        deck_name: Optional label for the flashcard deck (e.g. the filename).
        mode: Optional quiz mode label (e.g. ``"adaptive"``).

    Raises:
        ExportError: If the file cannot be written or the format is unknown.
    """
    fmt = fmt.strip().lower()
    if fmt not in ("json", "csv"):
        raise ExportError(f"Unknown export format '{fmt}'. Valid formats: json, csv.")

    summary = stats.summary()
    summary["timestamp"] = datetime.now().isoformat(timespec="seconds")
    summary["deck"] = deck_name
    summary["mode"] = mode

    try:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        if fmt == "json":
            _export_json(summary, filepath)
        else:
            _export_csv(summary, filepath)
    except OSError as exc:
        raise ExportError(f"Could not write export file '{filepath}': {exc}") from exc

    logger.info("Session exported to '%s' (%s).", filepath, fmt.upper())
    print(f"  Results exported to: {filepath}")


def _export_json(data: dict[str, object], filepath: str) -> None:
    """Write *data* as formatted JSON to *filepath*.

    Args:
        data: The dictionary to serialise.
        filepath: Destination path.
    """
    with open(filepath, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)


def _export_csv(data: dict[str, object], filepath: str) -> None:
    """Write *data* as a single-row CSV to *filepath*.

    The ``missed_terms`` list is serialised as a semicolon-separated string.

    Args:
        data: The dictionary to serialise.
        filepath: Destination path.
    """
    # Flatten missed_terms list for CSV
    row = dict(data)
    missed_value = row.pop("missed_terms", [])
    if isinstance(missed_value, list):
        missed_terms = "; ".join(str(term) for term in missed_value)
    else:
        missed_terms = str(missed_value) if missed_value else ""
    row["missed_terms"] = missed_terms

    write_header = not os.path.exists(filepath)
    with open(filepath, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(row.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(row)
