# patterns/chain_of_responsibility.py

from __future__ import annotations

from abc import ABC, abstractmethod
import hmac
from typing import Optional, Mapping, Any


def _normalize(value: Optional[str]) -> str:
    """
    Normalize user input and stored answers so that we compare
    in a consistent, case-insensitive way.
    """
    return (value or "").strip().lower()


class AnswerHandler(ABC):
    """
    Abstract handler in the Chain of Responsibility.
    Each concrete handler checks ONE security answer.
    """

    def __init__(self, next_handler: Optional["AnswerHandler"] = None) -> None:
        self._next: Optional["AnswerHandler"] = next_handler

    def set_next(self, next_handler: "AnswerHandler") -> "AnswerHandler":
        """
        Set the next handler in the chain and return it so we can chain calls.
        """
        self._next = next_handler
        return next_handler

    def handle(self, user, form: Mapping[str, Any]) -> bool:
        """
        Template method: check this handler;
        if it passes, forward to the next handler (if any).
        """
        if not self._check(user, form):
            # This handler failed → stop the chain, recovery denied.
            return False

        if self._next is not None:
            # Pass to the next handler in the chain.
            return self._next.handle(user, form)

        # End of chain and all checks passed.
        return True

    @abstractmethod
    def _check(self, user, form: Mapping[str, Any]) -> bool:
        """
        Concrete handlers implement this with their specific check.
        """
        ...


class Answer1Handler(AnswerHandler):
    """
    Checks the first security answer (a1 vs user.sec_a1).
    """

    def _check(self, user, form: Mapping[str, Any]) -> bool:
        a1 = _normalize(form.get("a1"))
        correct1 = _normalize(getattr(user, "sec_a1", None))
        return hmac.compare_digest(a1, correct1)


class Answer2Handler(AnswerHandler):
    """
    Checks the second security answer (a2 vs user.sec_a2).
    """

    def _check(self, user, form: Mapping[str, Any]) -> bool:
        a2 = _normalize(form.get("a2"))
        correct2 = _normalize(getattr(user, "sec_a2", None))
        return hmac.compare_digest(a2, correct2)


class Answer3Handler(AnswerHandler):
    """
    Checks the third security answer (a3 vs user.sec_a3).
    """

    def _check(self, user, form: Mapping[str, Any]) -> bool:
        a3 = _normalize(form.get("a3"))
        correct3 = _normalize(getattr(user, "sec_a3", None))
        return hmac.compare_digest(a3, correct3)


def build_recovery_chain() -> AnswerHandler:
    """
    Build the chain:
        Answer1Handler → Answer2Handler → Answer3Handler
    """
    first = Answer1Handler()
    second = first.set_next(Answer2Handler())
    second.set_next(Answer3Handler())
    return first


def verify_security_answers(user, form: Mapping[str, Any]) -> bool:
    """
    Public function used by app.py. This keeps the SAME signature
    you already use, but now it's backed by a real CoR chain.
    """
    chain = build_recovery_chain()
    return chain.handle(user, form)