"""Decide what an interrupted effectful call may do next.

Nothing here talks to a provider. A provider's dedupe behaviour is an input,
declared per tool, and this module turns that declaration plus the crash point
into one decision. The module deliberately knows no provider names: which
declaration is true for which provider is a question for the deployment, and
the answer is written down in EVIDENCE.md rather than encoded here.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CrashPoint(Enum):
    """Where the process died, in the order the ledger rules put the steps."""

    BEFORE_INSERT = "before_insert"
    AFTER_INSERT_BEFORE_SEND = "after_insert_before_send"
    AFTER_SEND_BEFORE_RESPONSE = "after_send_before_response"
    AFTER_RESPONSE_BEFORE_RECEIPT = "after_response_before_receipt"
    AFTER_RECEIPT = "after_receipt"


class RowState(Enum):
    """What the ledger holds for that key once the process is gone."""

    NONE = "none"
    PENDING = "pending"
    DONE = "done"


class Dedupe(Enum):
    """What the provider compares a replay against."""

    KEY = "key"
    PAYLOAD = "payload"
    NONE = "none"


class Decision(Enum):
    """What the operator is allowed to do with the row."""

    NO_ACTION = "no_action"
    ALREADY_RECORDED = "already_recorded"
    SAFE_RESEND = "safe_resend"
    RESEND_IF_PAYLOAD_IDENTICAL = "resend_if_payload_identical"
    NEEDS_HUMAN = "needs_human"


ROW_AFTER_CRASH: dict[CrashPoint, RowState] = {
    CrashPoint.BEFORE_INSERT: RowState.NONE,
    CrashPoint.AFTER_INSERT_BEFORE_SEND: RowState.PENDING,
    CrashPoint.AFTER_SEND_BEFORE_RESPONSE: RowState.PENDING,
    CrashPoint.AFTER_RESPONSE_BEFORE_RECEIPT: RowState.PENDING,
    CrashPoint.AFTER_RECEIPT: RowState.DONE,
}


@dataclass(frozen=True)
class Provider:
    """A provider behaviour a tool declares. Not a provider."""

    name: str
    dedupe: Dedupe
    window_seconds: int | None = None
    replay_inside_window: bool = True

    def validate(self) -> None:
        """Raise ValueError unless the declaration says enough to decide.

        A declaration that dedupes on a key without saying for how long cannot
        decide the replay: the same row is a safe resend inside the window and a
        maybe-second-effect outside it. A declaration with a window but no key
        dedupe names a mechanism the provider does not have.
        """
        if self.dedupe is Dedupe.KEY and self.window_seconds is None:
            raise ValueError(
                f"{self.name!r} dedupes on a key but declares no window_seconds; "
                "inside and outside that window are different answers"
            )
        if self.dedupe is not Dedupe.KEY and self.window_seconds is not None:
            raise ValueError(
                f"{self.name!r} declares window_seconds but does not dedupe on a key"
            )
        if self.dedupe is Dedupe.KEY and self.window_seconds is not None and self.window_seconds <= 0:
            raise ValueError(f"{self.name!r} declares a window of {self.window_seconds}s")
        return None


def decide(row: RowState, provider: Provider) -> Decision:
    """Return what may be done with a row, given the provider's declaration."""
    if row is RowState.NONE:
        return Decision.NO_ACTION
    if row is RowState.DONE:
        return Decision.ALREADY_RECORDED

    # A pending row is the only state a provider-side check can rescue.
    provider.validate()
    if provider.dedupe is Dedupe.PAYLOAD:
        return Decision.RESEND_IF_PAYLOAD_IDENTICAL
    if provider.dedupe is Dedupe.KEY and provider.replay_inside_window:
        return Decision.SAFE_RESEND
    return Decision.NEEDS_HUMAN
