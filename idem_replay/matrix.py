"""The 20-cell matrix: five crash points against four provider behaviours."""
from __future__ import annotations

from dataclasses import dataclass

from .model import (
    ROW_AFTER_CRASH,
    CrashPoint,
    Decision,
    Dedupe,
    Provider,
    RowState,
    decide,
)

KEY_IN_WINDOW = Provider("key_in_window", Dedupe.KEY, 86_400, True)
KEY_OUTSIDE_WINDOW = Provider("key_outside_window", Dedupe.KEY, 86_400, False)
NO_DEDUPE = Provider("no_dedupe", Dedupe.NONE)
PAYLOAD_KEYED = Provider("payload_keyed", Dedupe.PAYLOAD)

PROVIDERS = (KEY_IN_WINDOW, KEY_OUTSIDE_WINDOW, NO_DEDUPE, PAYLOAD_KEYED)


@dataclass(frozen=True)
class Cell:
    """One crash point under one declared provider behaviour."""

    crash_point: CrashPoint
    provider: Provider
    row: RowState
    decision: Decision

    @property
    def name(self) -> str:
        return f"{self.crash_point.value}/{self.provider.name}"


def cells(providers: tuple[Provider, ...] = PROVIDERS) -> list[Cell]:
    """Return every cell, in crash-point order then provider order."""
    return [
        Cell(point, provider, ROW_AFTER_CRASH[point], decide(ROW_AFTER_CRASH[point], provider))
        for point in CrashPoint
        for provider in providers
    ]


def summary(cells_in: list[Cell]) -> dict[str, object]:
    """Count the matrix by row state and by decision."""
    by_row: dict[str, int] = {}
    by_decision: dict[str, int] = {}
    for cell in cells_in:
        by_row[cell.row.value] = by_row.get(cell.row.value, 0) + 1
        by_decision[cell.decision.value] = by_decision.get(cell.decision.value, 0) + 1

    pending = [cell for cell in cells_in if cell.row is RowState.PENDING]
    rescued = sum(1 for cell in pending if cell.decision is Decision.SAFE_RESEND)
    return {
        "cells": len(cells_in),
        "crash_points": len({cell.crash_point for cell in cells_in}),
        "providers": len({cell.provider.name for cell in cells_in}),
        "by_row": dict(sorted(by_row.items())),
        "by_decision": dict(sorted(by_decision.items())),
        "pending_cells": len(pending),
        "pending_rescued_by_key": rescued,
        "pending_rescue_fraction": round(rescued / len(pending), 4) if pending else None,
    }
