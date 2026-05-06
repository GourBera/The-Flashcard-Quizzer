"""Quiz engine implementing the Strategy and Factory design patterns.

Design Patterns Used
--------------------
Strategy Pattern
    ``QuizMode`` is the abstract strategy interface. ``SequentialMode``,
    ``RandomMode``, and ``AdaptiveMode`` are concrete strategies. Each
    encapsulates a different algorithm for ordering flashcards, making it
    trivial to add new modes (e.g. Spaced Repetition) without modifying the
    ``QuizSession`` orchestrator.

Factory Pattern
    ``QuizModeFactory`` centralises mode construction and maps user-supplied
    strings to the correct strategy class, hiding instantiation details from
    callers.
"""

import logging
import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from utils.data_loader import FlashCard

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Strategy interface
# ---------------------------------------------------------------------------


class QuizMode(ABC):
    """Abstract base class for quiz ordering strategies.

    A concrete strategy must implement :meth:`next_card` and may override
    :meth:`record_result` to react to the user's answer (e.g. *AdaptiveMode*
    uses this to re-queue missed cards).
    """

    @abstractmethod
    def next_card(self) -> FlashCard | None:
        """Return the next card to present, or ``None`` when the deck is done.

        Returns:
            The next :class:`~utils.data_loader.FlashCard`, or ``None``.
        """

    @abstractmethod
    def load(self, cards: list[FlashCard]) -> None:
        """Initialise the strategy with the deck of cards.

        Args:
            cards: The full list of flashcards to quiz on.
        """

    def record_result(self, card: FlashCard, correct: bool) -> None:  # noqa: ARG002
        """Called after each answer so strategies can adapt the queue.

        The default implementation does nothing; override in adaptive modes.

        Args:
            card: The card that was just answered.
            correct: Whether the user answered correctly.
        """


# ---------------------------------------------------------------------------
# Concrete strategies
# ---------------------------------------------------------------------------


class SequentialMode(QuizMode):
    """Presents cards in the original order (1 → N).

    This is the simplest strategy and mirrors the order in the JSON file,
    which makes it predictable and easy to test.
    """

    def __init__(self) -> None:
        self._queue: list[FlashCard] = []

    def load(self, cards: list[FlashCard]) -> None:
        """Load cards in their natural order."""
        self._queue = list(cards)
        logger.debug("SequentialMode loaded %d cards.", len(self._queue))

    def next_card(self) -> FlashCard | None:
        """Pop the first card from the queue."""
        if not self._queue:
            return None
        return self._queue.pop(0)


class RandomMode(QuizMode):
    """Presents cards in a randomly shuffled order.

    Each call to :meth:`load` produces a fresh shuffle, so repeated sessions
    differ from each other.
    """

    def __init__(self) -> None:
        self._queue: list[FlashCard] = []

    def load(self, cards: list[FlashCard]) -> None:
        """Load cards and shuffle them."""
        self._queue = list(cards)
        random.shuffle(self._queue)
        logger.debug("RandomMode shuffled %d cards.", len(self._queue))

    def next_card(self) -> FlashCard | None:
        """Pop the first card from the shuffled queue."""
        if not self._queue:
            return None
        return self._queue.pop(0)


class AdaptiveMode(QuizMode):
    """Prioritises cards the user previously answered incorrectly.

    Algorithm
    ---------
    1. Cards start with ``weight = 1``.
    2. On an incorrect answer the card's weight is incremented and it is
       re-inserted near the front of the queue (after any other pending
       re-queued cards).
    3. Correctly answered cards are removed from the queue permanently.
    4. The session ends only when every card has been answered correctly at
       least once.

    This ensures that difficult cards appear more often until mastered,
    mirroring real-world spaced-repetition concepts.
    """

    def __init__(self) -> None:
        self._queue: list[FlashCard] = []
        self._requeue_position: int = 0  # index after which wrong cards re-enter

    def load(self, cards: list[FlashCard]) -> None:
        """Load a fresh, shuffled deck with weights reset to 1."""
        self._queue = [FlashCard(c.front, c.back, 1) for c in cards]
        random.shuffle(self._queue)
        self._requeue_position = 0
        logger.debug("AdaptiveMode loaded %d cards.", len(self._queue))

    def next_card(self) -> FlashCard | None:
        """Pop the first card from the adaptive queue."""
        if not self._queue:
            return None
        card = self._queue.pop(0)
        # Adjust requeue pointer after pop
        if self._requeue_position > 0:
            self._requeue_position -= 1
        return card

    def record_result(self, card: FlashCard, correct: bool) -> None:
        """Re-insert incorrect cards near the front; discard correct ones.

        Args:
            card: The card that was just answered.
            correct: Whether the user answered correctly.
        """
        if not correct:
            card.weight += 1
            # Re-insert after currently pending wrong cards (but not at end)
            insert_at = min(self._requeue_position, len(self._queue))
            self._queue.insert(insert_at, card)
            self._requeue_position = insert_at + 1
            logger.debug(
                "AdaptiveMode re-queued '%s' at position %d (weight=%d).",
                card.front[:30],
                insert_at,
                card.weight,
            )
        else:
            logger.debug("AdaptiveMode card '%s' answered correctly.", card.front[:30])


# ---------------------------------------------------------------------------
# Observer protocol (used by QuizSession to emit events)
# ---------------------------------------------------------------------------


@runtime_checkable
class QuizEventListener(Protocol):
    """Protocol for objects that listen to quiz session events."""

    def on_answer(self, card: FlashCard, correct: bool) -> None:
        """Called after each answer.

        Args:
            card: The card that was answered.
            correct: Whether the answer was correct.
        """

    def on_session_end(self) -> None:
        """Called when the quiz session finishes."""


# ---------------------------------------------------------------------------
# Quiz session orchestrator
# ---------------------------------------------------------------------------


class QuizSession:
    """Orchestrates a quiz session using a chosen :class:`QuizMode` strategy.

    The session drives the question–answer loop, delegates card ordering to
    the strategy, and notifies all registered :class:`QuizEventListener`
    observers after each answer and at session end.

    Args:
        mode: The concrete :class:`QuizMode` strategy to use.
        cards: The deck of flashcards.
        listeners: Optional list of observers implementing
            :class:`QuizEventListener`.
    """

    def __init__(
        self,
        mode: QuizMode,
        cards: list[FlashCard],
        listeners: list[QuizEventListener] | None = None,
    ) -> None:
        self._mode = mode
        self._mode.load(cards)
        self._listeners: list[QuizEventListener] = listeners or []

    def add_listener(self, listener: QuizEventListener) -> None:
        """Register an observer.

        Args:
            listener: An object implementing :class:`QuizEventListener`.
        """
        self._listeners.append(listener)

    def record_answer(self, card: FlashCard, answer: str) -> bool:
        """Evaluate the user's answer and notify listeners.

        Comparison is case-insensitive and strips leading/trailing whitespace.

        Args:
            card: The card that was presented.
            answer: The raw text entered by the user.

        Returns:
            ``True`` if the answer matches the card's back; ``False`` otherwise.
        """
        correct = answer.strip().lower() == card.back.strip().lower()
        self._mode.record_result(card, correct)
        for listener in self._listeners:
            listener.on_answer(card, correct)
        return correct

    def next_card(self) -> FlashCard | None:
        """Delegate to the strategy to get the next card.

        Returns:
            The next :class:`~utils.data_loader.FlashCard`, or ``None`` when done.
        """
        return self._mode.next_card()

    def end_session(self) -> None:
        """Notify all listeners that the session has ended."""
        for listener in self._listeners:
            listener.on_session_end()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_MODE_REGISTRY: dict[str, type[QuizMode]] = {
    "sequential": SequentialMode,
    "random": RandomMode,
    "adaptive": AdaptiveMode,
}


class QuizModeFactory:
    """Factory that creates :class:`QuizMode` instances from a string key.

    Supported mode strings: ``"sequential"``, ``"random"``, ``"adaptive"``.

    Example::

        mode = QuizModeFactory.create("adaptive")
        session = QuizSession(mode, cards)
    """

    @staticmethod
    def create(mode: str) -> QuizMode:
        """Instantiate and return the requested :class:`QuizMode`.

        Args:
            mode: A mode string (case-insensitive).

        Returns:
            A concrete :class:`QuizMode` instance.

        Raises:
            ValueError: If *mode* is not a recognised key.
        """
        key = mode.strip().lower()
        if key not in _MODE_REGISTRY:
            valid = ", ".join(sorted(_MODE_REGISTRY))
            raise ValueError(
                f"Unknown quiz mode '{mode}'. Valid modes are: {valid}."
            )
        return _MODE_REGISTRY[key]()

    @staticmethod
    def available_modes() -> list[str]:
        """Return a sorted list of valid mode names.

        Returns:
            List of mode name strings.
        """
        return sorted(_MODE_REGISTRY.keys())
