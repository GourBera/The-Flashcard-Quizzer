"""Tests for utils/data_loader.py.

Covers:
- Array-format JSON loading
- Object-format JSON loading
- Invalid / malformed JSON
- Missing required fields (front / back)
- Non-existent file
- Empty deck
- Empty string values for front / back
"""

import json
import os
import tempfile

import pytest

from utils.data_loader import FlashCard, FlashCardLoadError, load_flashcards

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_json(data: object) -> str:
    """Write *data* to a temporary JSON file and return its path."""
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    return path


def _write_raw(content: str) -> str:
    """Write raw text to a temporary file and return its path."""
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


# ---------------------------------------------------------------------------
# FlashCard dataclass tests
# ---------------------------------------------------------------------------


class TestFlashCard:
    def test_valid_flashcard_creation(self) -> None:
        card = FlashCard(front="Q?", back="A")
        assert card.front == "Q?"
        assert card.back == "A"
        assert card.weight == 1

    def test_custom_weight(self) -> None:
        card = FlashCard(front="Q?", back="A", weight=3)
        assert card.weight == 3

    def test_empty_front_raises(self) -> None:
        with pytest.raises(FlashCardLoadError, match="front"):
            FlashCard(front="", back="A")

    def test_whitespace_front_raises(self) -> None:
        with pytest.raises(FlashCardLoadError, match="front"):
            FlashCard(front="   ", back="A")

    def test_empty_back_raises(self) -> None:
        with pytest.raises(FlashCardLoadError, match="back"):
            FlashCard(front="Q?", back="")

    def test_whitespace_back_raises(self) -> None:
        with pytest.raises(FlashCardLoadError, match="back"):
            FlashCard(front="Q?", back="   ")


# ---------------------------------------------------------------------------
# load_flashcards — happy path
# ---------------------------------------------------------------------------


class TestLoadFlashcardsHappyPath:
    def test_load_valid_flashcards_array(self) -> None:
        """Array-format JSON with valid cards loads correctly."""
        data = [{"front": "Capital of France?", "back": "Paris"}]
        path = _write_json(data)
        cards = load_flashcards(path)
        assert len(cards) == 1
        assert cards[0].front == "Capital of France?"
        assert cards[0].back == "Paris"

    def test_load_valid_flashcards_object_format(self) -> None:
        """Object-format JSON with 'cards' key loads correctly."""
        data = {
            "cards": [
                {"front": "What is 2+2?", "back": "4"},
                {"front": "What is 3*3?", "back": "9"},
            ]
        }
        path = _write_json(data)
        cards = load_flashcards(path)
        assert len(cards) == 2
        assert cards[1].back == "9"

    def test_load_multiple_cards(self) -> None:
        """Multiple cards in array format all load."""
        data = [{"front": f"Q{i}", "back": f"A{i}"} for i in range(10)]
        path = _write_json(data)
        cards = load_flashcards(path)
        assert len(cards) == 10

    def test_load_preserves_case(self) -> None:
        """Card text is preserved as-is (not lowercased)."""
        data = [{"front": "HTML", "back": "HyperText Markup Language"}]
        path = _write_json(data)
        cards = load_flashcards(path)
        assert cards[0].back == "HyperText Markup Language"

    def test_default_weight_is_one(self) -> None:
        """Loaded cards start with weight=1."""
        path = _write_json([{"front": "Q", "back": "A"}])
        cards = load_flashcards(path)
        assert cards[0].weight == 1


# ---------------------------------------------------------------------------
# load_flashcards — error handling
# ---------------------------------------------------------------------------


class TestLoadFlashcardsErrors:
    def test_load_nonexistent_file_raises(self) -> None:
        """Missing file raises FlashCardLoadError with helpful message."""
        with pytest.raises(FlashCardLoadError, match="not found"):
            load_flashcards("/tmp/does_not_exist_12345.json")

    def test_load_invalid_json_raises(self) -> None:
        """Malformed JSON raises FlashCardLoadError (not a raw JSONDecodeError)."""
        path = _write_raw("{this is not json}")
        with pytest.raises(FlashCardLoadError, match="not valid JSON"):
            load_flashcards(path)

    def test_load_missing_required_field_back(self) -> None:
        """Card missing 'back' raises FlashCardLoadError."""
        data = [{"front": "Capital of France?"}]
        path = _write_json(data)
        with pytest.raises(FlashCardLoadError, match="back"):
            load_flashcards(path)

    def test_load_missing_required_field_front(self) -> None:
        """Card missing 'front' raises FlashCardLoadError."""
        data = [{"back": "Paris"}]
        path = _write_json(data)
        with pytest.raises(FlashCardLoadError, match="front"):
            load_flashcards(path)

    def test_load_empty_deck_raises(self) -> None:
        """Empty array raises FlashCardLoadError."""
        path = _write_json([])
        with pytest.raises(FlashCardLoadError, match="no flashcards"):
            load_flashcards(path)

    def test_load_empty_object_cards_raises(self) -> None:
        """Object format with empty 'cards' list raises FlashCardLoadError."""
        path = _write_json({"cards": []})
        with pytest.raises(FlashCardLoadError, match="no flashcards"):
            load_flashcards(path)

    def test_load_wrong_root_type_raises(self) -> None:
        """JSON root that is neither list nor dict with 'cards' raises."""
        path = _write_json("just a string")
        with pytest.raises(FlashCardLoadError):
            load_flashcards(path)

    def test_load_cards_not_a_list_raises(self) -> None:
        """Object format where 'cards' value is not a list raises."""
        path = _write_json({"cards": "not a list"})
        with pytest.raises(FlashCardLoadError):
            load_flashcards(path)

    def test_load_card_not_a_dict_raises(self) -> None:
        """Non-dict card in array raises FlashCardLoadError."""
        path = _write_json(["just a string"])
        with pytest.raises(FlashCardLoadError):
            load_flashcards(path)

    def test_load_empty_front_string_raises(self) -> None:
        """Card with empty 'front' string raises FlashCardLoadError."""
        path = _write_json([{"front": "", "back": "A"}])
        with pytest.raises(FlashCardLoadError):
            load_flashcards(path)

    def test_load_both_fields_missing_raises(self) -> None:
        """Card with both fields missing raises FlashCardLoadError."""
        path = _write_json([{}])
        with pytest.raises(FlashCardLoadError, match="front|back"):
            load_flashcards(path)

    def test_error_message_contains_filename(self) -> None:
        """Error messages reference the source filename for clarity."""
        path = _write_raw("not json at all!!!")
        with pytest.raises(FlashCardLoadError) as exc_info:
            load_flashcards(path)
        assert os.path.basename(path) in str(exc_info.value)
