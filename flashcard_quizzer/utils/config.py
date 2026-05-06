"""Application configuration management for the Flashcard Quizzer.

Provides an :class:`AppConfig` dataclass whose values are loaded from an
optional JSON config file with safe defaults so the application works
out-of-the-box with no configuration required.
"""

import json
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_DEFAULTS: dict[str, object] = {
    "color_enabled": True,
    "export_enabled": False,
    "export_path": "quiz_results.json",
    "export_format": "json",
    "log_level": "WARNING",
    "default_mode": "sequential",
}


@dataclass
class AppConfig:
    """Holds runtime configuration for the Flashcard Quizzer.

    Attributes:
        color_enabled: Whether ANSI colour output is active.
        export_enabled: Whether session results are exported after each quiz.
        export_path: Destination file path for exported results.
        export_format: Export file format — ``"json"`` or ``"csv"``.
        log_level: Python logging level string (e.g. ``"DEBUG"``, ``"INFO"``).
        default_mode: Default quiz mode when ``-m`` is not supplied.
    """

    color_enabled: bool = field(default=True)
    export_enabled: bool = field(default=False)
    export_path: str = field(default="quiz_results.json")
    export_format: str = field(default="json")
    log_level: str = field(default="WARNING")
    default_mode: str = field(default="sequential")


def load_config(path: str = "config.json") -> AppConfig:
    """Load configuration from a JSON file, falling back to defaults.

    Missing keys in the file are filled from :data:`_DEFAULTS` so a partial
    config file is valid. Non-existent files are silently ignored and the
    default :class:`AppConfig` is returned.

    Args:
        path: Path to the JSON configuration file.

    Returns:
        A fully-populated :class:`AppConfig` instance.
    """
    merged = dict(_DEFAULTS)

    try:
        with open(path, encoding="utf-8") as fh:
            user_cfg = json.load(fh)
        if not isinstance(user_cfg, dict):
            logger.warning(
                "Config file '%s' must be a JSON object; using defaults.", path
            )
        else:
            # Only accept keys that exist in _DEFAULTS to avoid silent typos
            unknown = set(user_cfg) - set(_DEFAULTS)
            if unknown:
                logger.warning(
                    "Config file '%s' contains unknown keys: %s. They will be ignored.",
                    path,
                    ", ".join(sorted(unknown)),
                )
            for key in _DEFAULTS:
                if key in user_cfg:
                    merged[key] = user_cfg[key]
        logger.info("Loaded config from '%s'.", path)
    except FileNotFoundError:
        logger.debug("No config file found at '%s'; using defaults.", path)
    except json.JSONDecodeError as exc:
        logger.warning(
            "Config file '%s' is not valid JSON (%s); using defaults.", path, exc
        )

    return AppConfig(
        color_enabled=bool(merged["color_enabled"]),
        export_enabled=bool(merged["export_enabled"]),
        export_path=str(merged["export_path"]),
        export_format=str(merged["export_format"]),
        log_level=str(merged["log_level"]),
        default_mode=str(merged["default_mode"]),
    )
