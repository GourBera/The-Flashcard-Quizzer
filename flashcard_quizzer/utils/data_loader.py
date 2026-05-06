"""Data loading and validation for the Flashcard Quizzer."""

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


class FlashCardLoadError(Exception):
    """Raised when flashcard data cannot be loaded or is invalid."""

    pass


@dataclass
class FlashCard:
    """Represents a single flashcard with a front (question) and back (answer).

    Attributes:
        front: The question or prompt shown to the user.
        back: The expected answer.
        weight: Adaptive weight; higher values mean the card is shown more often.
    """

    front: str
    back: str
    weight: int = field(default=1)

    def __post_init__(self) -> None:
        """Validate that front and back are non-empty strings."""
        if not self.front or not self.front.strip():
            raise FlashCardLoadError("FlashCard 'front' field must not be empty.")
        if not self.back or not self.back.strip():
            raise FlashCardLoadError("FlashCard 'back' field must not be empty.")


def _parse_raw_cards(raw: Any, source: str) -> list[FlashCard]:
    """Parse a raw Python object into a list of FlashCard instances.

    Args:
        raw: The decoded JSON value — either a list or a dict with a 'cards' key.
        source: A label for error messages (e.g. the file path).

    Returns:
        A non-empty list of validated FlashCard objects.

    Raises:
        FlashCardLoadError: If the structure is unrecognised, fields are missing,
            or the resulting deck is empty.
    """
    if isinstance(raw, list):
        card_list = raw
    elif isinstance(raw, dict) and "cards" in raw:
        card_list = raw["cards"]
    else:
        raise FlashCardLoadError(
            f"'{source}' must be a JSON array or an object with a 'cards' key.\n"
            '  Expected: [{"front": "...", "back": "..."}] '
            'or {"cards": [...]}'
        )

    if not isinstance(card_list, list):
        raise FlashCardLoadError(
            f"The 'cards' value in '{source}' must be a list, "
            f"got {type(card_list).__name__}."
        )

    cards: list[FlashCard] = []
    for idx, item in enumerate(card_list):
        if not isinstance(item, dict):
            raise FlashCardLoadError(
                f"Card at index {idx} in '{source}' must be a JSON object, "
                f"got {type(item).__name__}."
            )
        missing = [f for f in ("front", "back") if f not in item]
        if missing:
            raise FlashCardLoadError(
                f"Card at index {idx} in '{source}' is missing required "
                f"field(s): {', '.join(missing)}."
            )
        try:
            cards.append(FlashCard(front=str(item["front"]), back=str(item["back"])))
        except FlashCardLoadError as exc:
            raise FlashCardLoadError(
                f"Card at index {idx} in '{source}' is invalid: {exc}"
            ) from exc

    if not cards:
        raise FlashCardLoadError(
            f"'{source}' contains no flashcards. "
            "Add at least one card before running a quiz."
        )

    logger.info("Loaded %d flashcard(s) from '%s'.", len(cards), source)
    return cards


def load_flashcards(filepath: str) -> list[FlashCard]:
    """Load and validate flashcards from a JSON file.

    Supports two JSON formats:

    **Array format**::

        [{"front": "Q1", "back": "A1"}, ...]

    **Object format**::

        {"cards": [{"front": "Q1", "back": "A1"}, ...]}

    Args:
        filepath: Path to the JSON file.

    Returns:
        A list of validated :class:`FlashCard` objects.

    Raises:
        FlashCardLoadError: With a human-readable message for any of:
            missing file, invalid JSON, wrong structure, missing fields,
            or empty deck.
    """
    try:
        with open(filepath, encoding="utf-8") as fh:
            raw = json.load(fh)
    except FileNotFoundError:
        raise FlashCardLoadError(
            f"Flashcard file not found: '{filepath}'\n"
            "  Check the path and try again."
        )
    except json.JSONDecodeError as exc:
        raise FlashCardLoadError(
            f"'{filepath}' is not valid JSON.\n"
            f"  {exc.msg} (line {exc.lineno}, column {exc.colno})"
        ) from exc

    return _parse_raw_cards(raw, filepath)
