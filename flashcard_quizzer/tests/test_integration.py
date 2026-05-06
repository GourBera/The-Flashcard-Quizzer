"""Integration tests for the Flashcard Quizzer.

Simulates complete quiz sessions end-to-end, verifying that the data loader,
quiz engine, and stats tracker work together correctly.
"""

import json
import os
import tempfile

import pytest

from utils.data_loader import FlashCard, load_flashcards
from utils.quiz_engine import AdaptiveMode, QuizModeFactory, QuizSession, SequentialMode
from utils.stats_tracker import SessionStats

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_deck(n: int = 5) -> list[FlashCard]:
    return [FlashCard(front=f"Q{i}", back=f"A{i}") for i in range(n)]


def _write_json_file(data: object) -> str:
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    with open(path, "w") as fh:
        json.dump(data, fh)
    return path


# ---------------------------------------------------------------------------
# Full session — stats accuracy
# ---------------------------------------------------------------------------


class TestFullSession:
    def test_full_session_all_correct(self) -> None:
        """Answering all questions correctly yields 100% accuracy."""
        cards = make_deck(3)
        stats = SessionStats()
        mode = SequentialMode()
        session = QuizSession(mode=mode, cards=cards, listeners=[stats])

        while (card := session.next_card()) is not None:
            session.record_answer(card, card.back)  # always correct

        session.end_session()

        assert stats.total == 3
        assert stats.correct_count == 3
        assert stats.accuracy() == 100.0
        assert stats.missed == []

    def test_full_session_all_wrong(self) -> None:
        """Answering all questions incorrectly yields 0% accuracy."""
        cards = make_deck(3)
        stats = SessionStats()
        mode = SequentialMode()
        session = QuizSession(mode=mode, cards=cards, listeners=[stats])

        while (card := session.next_card()) is not None:
            session.record_answer(card, "WRONG")

        session.end_session()

        assert stats.total == 3
        assert stats.correct_count == 0
        assert stats.accuracy() == 0.0
        assert len(stats.missed) == 3

    def test_full_session_partial_correct(self) -> None:
        """Mixed answers produce the correct accuracy percentage."""
        cards = [
            FlashCard(front="Q0", back="A0"),
            FlashCard(front="Q1", back="A1"),
            FlashCard(front="Q2", back="A2"),
            FlashCard(front="Q3", back="A3"),
        ]
        answers = ["A0", "wrong", "A2", "wrong"]  # 2 correct out of 4

        stats = SessionStats()
        mode = SequentialMode()
        session = QuizSession(mode=mode, cards=cards, listeners=[stats])

        for answer in answers:
            card = session.next_card()
            if card:
                session.record_answer(card, answer)

        session.end_session()

        assert stats.total == 4
        assert stats.correct_count == 2
        assert stats.accuracy() == 50.0

    def test_full_session_missed_cards_list(self) -> None:
        """Missed cards are tracked and contain unique entries only."""
        cards = make_deck(3)
        stats = SessionStats()
        mode = SequentialMode()
        session = QuizSession(mode=mode, cards=cards, listeners=[stats])

        session.record_answer(cards[0], "WRONG")
        session.record_answer(cards[1], cards[1].back)
        session.record_answer(cards[2], "WRONG")

        missed_fronts = {c.front for c in stats.missed}
        assert "Q0" in missed_fronts
        assert "Q2" in missed_fronts
        assert "Q1" not in missed_fronts

    def test_full_session_missed_cards_unique(self) -> None:
        """The same missed card appearing twice is only listed once."""
        card = FlashCard(front="Q", back="A")
        stats = SessionStats()

        # Simulate wrong twice (AdaptiveMode would re-queue it)
        stats.on_answer(card, correct=False)
        stats.on_answer(card, correct=False)

        assert len(stats.missed) == 1

    def test_session_summary_dict_keys(self) -> None:
        """summary() returns the expected keys."""
        stats = SessionStats()
        stats.on_answer(FlashCard("Q", "A"), correct=True)
        summary = stats.summary()
        expected_keys = {
            "total",
            "correct",
            "incorrect",
            "accuracy_pct",
            "missed_terms",
        }
        assert expected_keys == set(summary.keys())

    def test_session_accuracy_zero_when_no_questions(self) -> None:
        """accuracy() returns 0.0 before any questions are answered."""
        stats = SessionStats()
        assert stats.accuracy() == 0.0


# ---------------------------------------------------------------------------
# Integration with data loader
# ---------------------------------------------------------------------------


class TestDataLoaderIntegration:
    def test_load_and_quiz_array_format(self) -> None:
        """Cards loaded from array-format JSON can be used in a quiz session."""
        data = [
            {"front": "Capital of Japan?", "back": "Tokyo"},
            {"front": "Capital of Germany?", "back": "Berlin"},
        ]
        path = _write_json_file(data)
        cards = load_flashcards(path)

        stats = SessionStats()
        mode = SequentialMode()
        session = QuizSession(mode=mode, cards=cards, listeners=[stats])

        card = session.next_card()
        assert card is not None
        session.record_answer(card, "Tokyo")
        session.end_session()

        assert stats.correct_count == 1

    def test_load_and_quiz_object_format(self) -> None:
        """Cards loaded from object-format JSON work in a quiz session."""
        data = {"cards": [{"front": "def keyword", "back": "define function"}]}
        path = _write_json_file(data)
        cards = load_flashcards(path)

        stats = SessionStats()
        session = QuizSession(mode=SequentialMode(), cards=cards, listeners=[stats])
        card = session.next_card()
        session.record_answer(card, "DEFINE FUNCTION")  # type: ignore[arg-type]
        assert stats.correct_count == 1


# ---------------------------------------------------------------------------
# Adaptive mode integration
# ---------------------------------------------------------------------------


class TestAdaptiveModeIntegration:
    def test_adaptive_session_eventually_ends(self) -> None:
        """An adaptive session with all-wrong answers eventually terminates
        once we start answering correctly."""
        cards = make_deck(3)
        mode = AdaptiveMode()
        session = QuizSession(mode=mode, cards=cards)

        # Answer wrong twice per card, then correct
        wrong_counts: dict[str, int] = {}
        iterations = 0
        while (card := session.next_card()) is not None:
            iterations += 1
            wrong_counts[card.front] = wrong_counts.get(card.front, 0)
            if wrong_counts[card.front] < 2:
                session.record_answer(card, "WRONG")
                wrong_counts[card.front] += 1
            else:
                session.record_answer(card, card.back)
            if iterations > 100:  # guard against infinite loop in test
                pytest.fail("AdaptiveMode did not terminate within 100 iterations.")
        assert iterations > 3  # re-queuing occurred

    def test_factory_to_session_pipeline(self) -> None:
        """Full pipeline: factory → session → stats."""
        cards = make_deck(4)
        stats = SessionStats()
        mode = QuizModeFactory.create("sequential")
        session = QuizSession(mode=mode, cards=cards, listeners=[stats])

        answers = ["A0", "wrong", "A2", "A3"]
        for answer in answers:
            card = session.next_card()
            if card:
                session.record_answer(card, answer)
        session.end_session()

        assert stats.total == 4
        assert stats.incorrect_count() == 1
