from __future__ import annotations

from abc import ABC, abstractmethod
import hmac
from typing import Optional, Mapping, Any


def _normalize(value: Optional[str]) -> str:
    # Clean the string: make lowercase and remove spaces
    return (value or "").strip().lower()


class AnswerHandler(ABC):
    # Base class for checking one security answer

    def __init__(self, next_handler: Optional["AnswerHandler"] = None) -> None:
        # Points to the next checker in the chain
        self._next = next_handler

    def set_next(self, next_handler: "AnswerHandler") -> "AnswerHandler":
        # Set who comes next in the chain
        self._next = next_handler
        return next_handler

    def handle(self, user, form: Mapping[str, Any]) -> bool:
        # First check this answer
        if not self._check(user, form):
            return False

        # Then move to the next handler if it exists
        if self._next:
            return self._next.handle(user, form)

        return True

    @abstractmethod
    def _check(self, user, form: Mapping[str, Any]) -> bool:
        # Each child class must implement its own check
        ...


class Answer1Handler(AnswerHandler):
    def _check(self, user, form: Mapping[str, Any]) -> bool:
        # Compare user's answer 1 with the stored correct answer
        a1 = _normalize(form.get("a1"))
        correct1 = _normalize(getattr(user, "sec_a1", None))
        return hmac.compare_digest(a1, correct1)


class Answer2Handler(AnswerHandler):
    def _check(self, user, form: Mapping[str, Any]) -> bool:
        a2 = _normalize(form.get("a2"))
        correct2 = _normalize(getattr(user, "sec_a2", None))
        return hmac.compare_digest(a2, correct2)


class Answer3Handler(AnswerHandler):
    def _check(self, user, form: Mapping[str, Any]) -> bool:
        a3 = _normalize(form.get("a3"))
        correct3 = _normalize(getattr(user, "sec_a3", None))
        return hmac.compare_digest(a3, correct3)


def build_recovery_chain() -> AnswerHandler:
    # Build the chain: answer1 → answer2 → answer3
    first = Answer1Handler()
    second = first.set_next(Answer2Handler())
    second.set_next(Answer3Handler())
    return first


def verify_security_answers(user, form: Mapping[str, Any]) -> bool:
    # Run the full chain of answer checks
    chain = build_recovery_chain()
    return chain.handle(user, form)
