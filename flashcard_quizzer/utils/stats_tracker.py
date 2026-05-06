"""Session statistics tracker implementing the Observer design pattern.

Design Pattern: Observer
------------------------
``QuizObserver`` is the abstract observer interface. ``SessionStats`` is the
concrete observer that accumulates per-session metrics. By decoupling stats
tracking from the quiz loop, additional observers (e.g. ``FileExportObserver``)
can be attached without modifying ``QuizSession``.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from utils.data_loader import FlashCard

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Observer interface
# ---------------------------------------------------------------------------


class QuizObserver(ABC):
    """Abstract observer that receives events from a :class:`~utils.quiz_engine.QuizSession`.

    Implement this interface to add custom behaviour (e.g. stats tracking,
    file export, analytics) that reacts to quiz events without coupling to
    the session loop.
    """

    @abstractmethod
    def on_answer(self, card: FlashCard, correct: bool) -> None:
        """Called immediately after each answer is evaluated.

        Args:
            card: The flashcard that was answered.
            correct: ``True`` if the user's answer was correct.
        """

    @abstractmethod
    def on_session_end(self) -> None:
        """Called once when the quiz session ends (either completed or aborted)."""


# ---------------------------------------------------------------------------
# SessionStats — concrete observer
# ---------------------------------------------------------------------------


@dataclass
class SessionStats(QuizObserver):
    """Accumulates statistics for a single quiz session.

    Attributes:
        total: Total number of questions answered.
        correct_count: Number of correct answers.
        missed: List of cards the user answered incorrectly at least once.
    """

    total: int = field(default=0, init=False)
    correct_count: int = field(default=0, init=False)
    missed: list[FlashCard] = field(default_factory=list, init=False)
    _finished: bool = field(default=False, init=False, repr=False)

    def on_answer(self, card: FlashCard, correct: bool) -> None:
        """Update counters and missed list.

        Args:
            card: The card that was answered.
            correct: Whether the answer was correct.
        """
        self.total += 1
        if correct:
            self.correct_count += 1
        else:
            # Track unique missed cards (by front text)
            fronts = {c.front for c in self.missed}
            if card.front not in fronts:
                self.missed.append(card)
        logger.debug(
            "SessionStats updated: total=%d, correct=%d.",
            self.total,
            self.correct_count,
        )

    def on_session_end(self) -> None:
        """Mark the session as finished."""
        self._finished = True
        logger.info(
            "Session ended: %d/%d correct (%.1f%%).",
            self.correct_count,
            self.total,
            self.accuracy(),
        )

    def accuracy(self) -> float:
        """Return the accuracy as a percentage (0.0–100.0).

        Returns:
            ``0.0`` if no questions were answered; otherwise
            ``(correct / total) * 100``.
        """
        if self.total == 0:
            return 0.0
        return round((self.correct_count / self.total) * 100, 1)

    def incorrect_count(self) -> int:
        """Return the number of incorrect answers.

        Returns:
            ``total - correct_count``
        """
        return self.total - self.correct_count

    def summary(self) -> dict[str, object]:
        """Return a plain-dict summary suitable for serialisation.

        Returns:
            A dictionary with keys ``total``, ``correct``, ``incorrect``,
            ``accuracy_pct``, and ``missed_terms``.
        """
        return {
            "total": self.total,
            "correct": self.correct_count,
            "incorrect": self.incorrect_count(),
            "accuracy_pct": self.accuracy(),
            "missed_terms": [c.front for c in self.missed],
        }
