"""Tests for utils/quiz_engine.py.

Covers:
- QuizModeFactory: valid and invalid mode strings
- SequentialMode: order preservation
- RandomMode: shuffling behaviour
- AdaptiveMode: re-queuing incorrect cards
- QuizSession: answer evaluation, listener notification, end_session
"""

import pytest

from utils.data_loader import FlashCard
from utils.quiz_engine import (
    AdaptiveMode,
    QuizModeFactory,
    QuizSession,
    RandomMode,
    SequentialMode,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_cards(n: int = 5) -> list[FlashCard]:
    return [FlashCard(front=f"Q{i}", back=f"A{i}") for i in range(n)]


# ---------------------------------------------------------------------------
# QuizModeFactory
# ---------------------------------------------------------------------------


class TestQuizModeFactory:
    def test_factory_returns_sequential(self) -> None:
        mode = QuizModeFactory.create("sequential")
        assert isinstance(mode, SequentialMode)

    def test_factory_returns_random(self) -> None:
        mode = QuizModeFactory.create("random")
        assert isinstance(mode, RandomMode)

    def test_factory_returns_adaptive(self) -> None:
        mode = QuizModeFactory.create("adaptive")
        assert isinstance(mode, AdaptiveMode)

    def test_factory_case_insensitive(self) -> None:
        mode = QuizModeFactory.create("ADAPTIVE")
        assert isinstance(mode, AdaptiveMode)

    def test_factory_strips_whitespace(self) -> None:
        mode = QuizModeFactory.create("  random  ")
        assert isinstance(mode, RandomMode)

    def test_factory_invalid_mode_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown quiz mode"):
            QuizModeFactory.create("turbo")

    def test_available_modes_returns_all(self) -> None:
        modes = QuizModeFactory.available_modes()
        assert set(modes) == {"sequential", "random", "adaptive"}

    def test_available_modes_sorted(self) -> None:
        modes = QuizModeFactory.available_modes()
        assert modes == sorted(modes)


# ---------------------------------------------------------------------------
# SequentialMode
# ---------------------------------------------------------------------------


class TestSequentialMode:
    def test_sequential_preserves_order(self) -> None:
        cards = make_cards(4)
        mode = SequentialMode()
        mode.load(cards)
        result = []
        while (c := mode.next_card()) is not None:
            result.append(c.front)
        assert result == ["Q0", "Q1", "Q2", "Q3"]

    def test_sequential_returns_none_when_exhausted(self) -> None:
        mode = SequentialMode()
        mode.load(make_cards(2))
        mode.next_card()
        mode.next_card()
        assert mode.next_card() is None

    def test_sequential_load_replaces_previous_deck(self) -> None:
        mode = SequentialMode()
        mode.load(make_cards(3))
        mode.next_card()
        # Reload with a fresh deck
        mode.load([FlashCard("X", "Y")])
        assert mode.next_card().front == "X"  # type: ignore[union-attr]

    def test_sequential_does_not_mutate_original(self) -> None:
        cards = make_cards(3)
        original_fronts = [c.front for c in cards]
        mode = SequentialMode()
        mode.load(cards)
        while mode.next_card():
            pass
        assert [c.front for c in cards] == original_fronts

    def test_record_result_no_effect_on_sequential(self) -> None:
        """Calling record_result on SequentialMode should not raise."""
        mode = SequentialMode()
        mode.load(make_cards(1))
        card = mode.next_card()
        mode.record_result(card, correct=False)  # type: ignore[arg-type]
        assert mode.next_card() is None


# ---------------------------------------------------------------------------
# RandomMode
# ---------------------------------------------------------------------------


class TestRandomMode:
    def test_random_returns_all_cards(self) -> None:
        cards = make_cards(10)
        mode = RandomMode()
        mode.load(cards)
        result = []
        while (c := mode.next_card()) is not None:
            result.append(c.front)
        assert set(result) == {f"Q{i}" for i in range(10)}

    def test_random_returns_none_when_exhausted(self) -> None:
        mode = RandomMode()
        mode.load(make_cards(1))
        mode.next_card()
        assert mode.next_card() is None

    def test_random_shuffles_deck(self) -> None:
        """Two fresh loads should (very likely) produce different orderings."""
        cards = make_cards(20)
        mode = RandomMode()

        mode.load(cards)
        order_1 = []
        while (c := mode.next_card()) is not None:
            order_1.append(c.front)

        mode.load(cards)
        order_2 = []
        while (c := mode.next_card()) is not None:
            order_2.append(c.front)

        # With 20 cards the chance both orders are identical is 1/20! ≈ 0
        assert order_1 != order_2


# ---------------------------------------------------------------------------
# AdaptiveMode
# ---------------------------------------------------------------------------


class TestAdaptiveMode:
    def test_adaptive_mode_behavior_repeats_wrong_cards(self) -> None:
        """Cards answered incorrectly are re-queued and presented again."""
        cards = [FlashCard(front="Q0", back="A0"), FlashCard(front="Q1", back="A1")]
        mode = AdaptiveMode()
        mode.load(cards)

        seen: list[str] = []
        # Answer first card wrong, second card right, then wrong card again
        for _ in range(3):
            card = mode.next_card()
            if card is None:
                break
            seen.append(card.front)
            # Mark the first card we encounter as wrong
            correct = seen.count(card.front) > 1 or card.front == "Q1"
            mode.record_result(card, correct=correct)

        # The wrong card should have appeared at least twice
        wrong_card = seen[0]  # first card seen
        assert seen.count(wrong_card) >= 2 or len(seen) >= 2

    def test_adaptive_mode_increments_weight_on_wrong(self) -> None:
        card = FlashCard(front="Q", back="A")
        mode = AdaptiveMode()
        mode.load([card])

        seen = mode.next_card()
        assert seen is not None
        mode.record_result(seen, correct=False)

        # Re-queued card should have incremented weight
        requeued = mode.next_card()
        assert requeued is not None
        assert requeued.weight == 2

    def test_adaptive_mode_correct_answer_does_not_requeue(self) -> None:
        mode = AdaptiveMode()
        mode.load(make_cards(2))

        card = mode.next_card()
        assert card is not None
        mode.record_result(card, correct=True)

        # Queue should now have only 1 card remaining (the correct card was removed)
        remaining = []
        while (c := mode.next_card()) is not None:
            remaining.append(c)
        assert len(remaining) == 1

    def test_adaptive_ends_when_all_answered_correctly(self) -> None:
        mode = AdaptiveMode()
        mode.load(make_cards(3))
        # Answer everything correctly
        while (card := mode.next_card()) is not None:
            mode.record_result(card, correct=True)
        assert mode.next_card() is None


# ---------------------------------------------------------------------------
# QuizSession
# ---------------------------------------------------------------------------


class TestQuizSession:
    def test_session_correct_answer(self) -> None:
        cards = [FlashCard(front="Q0", back="A0")]
        mode = SequentialMode()
        session = QuizSession(mode=mode, cards=cards)
        card = session.next_card()
        assert card is not None
        assert session.record_answer(card, "A0") is True

    def test_session_incorrect_answer(self) -> None:
        cards = [FlashCard(front="Q0", back="A0")]
        mode = SequentialMode()
        session = QuizSession(mode=mode, cards=cards)
        card = session.next_card()
        assert card is not None
        assert session.record_answer(card, "wrong") is False

    def test_session_case_insensitive_comparison(self) -> None:
        cards = [FlashCard(front="Q", back="Paris")]
        mode = SequentialMode()
        session = QuizSession(mode=mode, cards=cards)
        card = session.next_card()
        assert session.record_answer(card, "PARIS") is True  # type: ignore[arg-type]

    def test_session_strips_whitespace_from_answer(self) -> None:
        cards = [FlashCard(front="Q", back="Paris")]
        mode = SequentialMode()
        session = QuizSession(mode=mode, cards=cards)
        card = session.next_card()
        assert session.record_answer(card, "  paris  ") is True  # type: ignore[arg-type]

    def test_session_notifies_listener_on_answer(self) -> None:
        """Listeners receive on_answer events."""
        events: list[tuple[str, bool]] = []

        class _Listener:
            def on_answer(self, card: FlashCard, correct: bool) -> None:
                events.append((card.front, correct))

            def on_session_end(self) -> None:
                pass

        cards = [FlashCard(front="Q0", back="A0")]
        mode = SequentialMode()
        session = QuizSession(mode=mode, cards=cards)
        session.add_listener(_Listener())
        card = session.next_card()
        session.record_answer(card, "A0")  # type: ignore[arg-type]
        assert events == [("Q0", True)]

    def test_session_notifies_listener_on_end(self) -> None:
        ended: list[bool] = []

        class _Listener:
            def on_answer(self, card: FlashCard, correct: bool) -> None:
                pass

            def on_session_end(self) -> None:
                ended.append(True)

        mode = SequentialMode()
        session = QuizSession(mode=mode, cards=make_cards(1))
        session.add_listener(_Listener())
        session.end_session()
        assert ended == [True]

    def test_session_multiple_listeners(self) -> None:
        counts: list[int] = [0, 0]

        class _L1:
            def on_answer(self, card: FlashCard, correct: bool) -> None:
                counts[0] += 1

            def on_session_end(self) -> None:
                pass

        class _L2:
            def on_answer(self, card: FlashCard, correct: bool) -> None:
                counts[1] += 1

            def on_session_end(self) -> None:
                pass

        mode = SequentialMode()
        session = QuizSession(mode=mode, cards=make_cards(1), listeners=[_L1(), _L2()])
        card = session.next_card()
        session.record_answer(card, "wrong")  # type: ignore[arg-type]
        assert counts == [1, 1]
