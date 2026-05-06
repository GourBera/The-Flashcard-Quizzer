"""Tests for utils/stats_tracker.py.

Covers:
- SessionStats.on_answer increments counters correctly
- Accuracy calculation (including zero-division guard)
- Missed card tracking (unique only)
- on_session_end marks session finished
- summary() returns correct structure
- incorrect_count()
"""

from utils.data_loader import FlashCard
from utils.stats_tracker import QuizObserver, SessionStats


def make_card(front: str = "Q", back: str = "A") -> FlashCard:
    return FlashCard(front=front, back=back)


class TestSessionStats:
    def test_initial_state(self) -> None:
        stats = SessionStats()
        assert stats.total == 0
        assert stats.correct_count == 0
        assert stats.missed == []

    def test_correct_answer_increments_total_and_correct(self) -> None:
        stats = SessionStats()
        stats.on_answer(make_card(), correct=True)
        assert stats.total == 1
        assert stats.correct_count == 1

    def test_wrong_answer_increments_total_only(self) -> None:
        stats = SessionStats()
        stats.on_answer(make_card(), correct=False)
        assert stats.total == 1
        assert stats.correct_count == 0

    def test_wrong_answer_adds_to_missed(self) -> None:
        stats = SessionStats()
        card = make_card("Capital of France?", "Paris")
        stats.on_answer(card, correct=False)
        assert len(stats.missed) == 1
        assert stats.missed[0].front == "Capital of France?"

    def test_correct_answer_does_not_add_to_missed(self) -> None:
        stats = SessionStats()
        stats.on_answer(make_card(), correct=True)
        assert stats.missed == []

    def test_duplicate_missed_card_counted_once(self) -> None:
        stats = SessionStats()
        card = make_card("Q", "A")
        stats.on_answer(card, correct=False)
        stats.on_answer(card, correct=False)
        assert len(stats.missed) == 1

    def test_different_missed_cards_all_tracked(self) -> None:
        stats = SessionStats()
        for i in range(5):
            stats.on_answer(make_card(f"Q{i}", f"A{i}"), correct=False)
        assert len(stats.missed) == 5

    def test_accuracy_all_correct(self) -> None:
        stats = SessionStats()
        for _ in range(10):
            stats.on_answer(make_card(), correct=True)
        assert stats.accuracy() == 100.0

    def test_accuracy_all_wrong(self) -> None:
        stats = SessionStats()
        for _ in range(4):
            stats.on_answer(make_card(), correct=False)
        assert stats.accuracy() == 0.0

    def test_accuracy_partial(self) -> None:
        stats = SessionStats()
        stats.on_answer(make_card("Q1", "A1"), correct=True)
        stats.on_answer(make_card("Q2", "A2"), correct=True)
        stats.on_answer(make_card("Q3", "A3"), correct=False)
        stats.on_answer(make_card("Q4", "A4"), correct=False)
        assert stats.accuracy() == 50.0

    def test_accuracy_zero_before_any_answers(self) -> None:
        assert SessionStats().accuracy() == 0.0

    def test_incorrect_count(self) -> None:
        stats = SessionStats()
        stats.on_answer(make_card("Q1", "A1"), correct=True)
        stats.on_answer(make_card("Q2", "A2"), correct=False)
        stats.on_answer(make_card("Q3", "A3"), correct=False)
        assert stats.incorrect_count() == 2

    def test_on_session_end_marks_finished(self) -> None:
        stats = SessionStats()
        stats.on_answer(make_card(), correct=True)
        stats.on_session_end()
        assert stats._finished is True

    def test_summary_dict_structure(self) -> None:
        stats = SessionStats()
        stats.on_answer(make_card("Q1", "A1"), correct=True)
        stats.on_answer(make_card("Q2", "A2"), correct=False)
        summary = stats.summary()
        assert summary["total"] == 2
        assert summary["correct"] == 1
        assert summary["incorrect"] == 1
        assert summary["accuracy_pct"] == 50.0
        assert "Q2" in summary["missed_terms"]  # type: ignore[operator]

    def test_summary_missed_terms_empty_on_perfect_score(self) -> None:
        stats = SessionStats()
        stats.on_answer(make_card(), correct=True)
        assert stats.summary()["missed_terms"] == []

    def test_is_quiz_observer_subclass(self) -> None:
        """SessionStats must be a concrete subclass of QuizObserver."""
        assert issubclass(SessionStats, QuizObserver)

    def test_observer_protocol_methods_exist(self) -> None:
        stats = SessionStats()
        assert callable(stats.on_answer)
        assert callable(stats.on_session_end)
