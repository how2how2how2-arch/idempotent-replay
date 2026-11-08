"""One test per cell of the 20-cell matrix, plus the structure the matrix rests on."""
from __future__ import annotations

import unittest

from idem_replay.model import (
    ROW_AFTER_CRASH,
    CrashPoint,
    Decision,
    Dedupe,
    Provider,
    RowState,
    decide,
)

KEY = Provider("key_in_window", Dedupe.KEY, 86_400, True)
KEY_EXPIRED = Provider("key_outside_window", Dedupe.KEY, 86_400, False)
NO_DEDUPE = Provider("no_dedupe", Dedupe.NONE)
PAYLOAD = Provider("payload_keyed", Dedupe.PAYLOAD)

PROVIDERS = (KEY, KEY_EXPIRED, NO_DEDUPE, PAYLOAD)

# The announced matrix, written out cell by cell. This is the contract: the
# table the announcement described, transcribed, and each cell is asserted.
EXPECTED: dict[tuple[CrashPoint, str], Decision] = {
    (CrashPoint.BEFORE_INSERT, "key_in_window"): Decision.NO_ACTION,
    (CrashPoint.BEFORE_INSERT, "key_outside_window"): Decision.NO_ACTION,
    (CrashPoint.BEFORE_INSERT, "no_dedupe"): Decision.NO_ACTION,
    (CrashPoint.BEFORE_INSERT, "payload_keyed"): Decision.NO_ACTION,
    (CrashPoint.AFTER_INSERT_BEFORE_SEND, "key_in_window"): Decision.SAFE_RESEND,
    (CrashPoint.AFTER_INSERT_BEFORE_SEND, "key_outside_window"): Decision.NEEDS_HUMAN,
    (CrashPoint.AFTER_INSERT_BEFORE_SEND, "no_dedupe"): Decision.NEEDS_HUMAN,
    (CrashPoint.AFTER_INSERT_BEFORE_SEND, "payload_keyed"): Decision.RESEND_IF_PAYLOAD_IDENTICAL,
    (CrashPoint.AFTER_SEND_BEFORE_RESPONSE, "key_in_window"): Decision.SAFE_RESEND,
    (CrashPoint.AFTER_SEND_BEFORE_RESPONSE, "key_outside_window"): Decision.NEEDS_HUMAN,
    (CrashPoint.AFTER_SEND_BEFORE_RESPONSE, "no_dedupe"): Decision.NEEDS_HUMAN,
    (CrashPoint.AFTER_SEND_BEFORE_RESPONSE, "payload_keyed"): Decision.RESEND_IF_PAYLOAD_IDENTICAL,
    (CrashPoint.AFTER_RESPONSE_BEFORE_RECEIPT, "key_in_window"): Decision.SAFE_RESEND,
    (CrashPoint.AFTER_RESPONSE_BEFORE_RECEIPT, "key_outside_window"): Decision.NEEDS_HUMAN,
    (CrashPoint.AFTER_RESPONSE_BEFORE_RECEIPT, "no_dedupe"): Decision.NEEDS_HUMAN,
    (CrashPoint.AFTER_RESPONSE_BEFORE_RECEIPT, "payload_keyed"): Decision.RESEND_IF_PAYLOAD_IDENTICAL,
    (CrashPoint.AFTER_RECEIPT, "key_in_window"): Decision.ALREADY_RECORDED,
    (CrashPoint.AFTER_RECEIPT, "key_outside_window"): Decision.ALREADY_RECORDED,
    (CrashPoint.AFTER_RECEIPT, "no_dedupe"): Decision.ALREADY_RECORDED,
    (CrashPoint.AFTER_RECEIPT, "payload_keyed"): Decision.ALREADY_RECORDED,
}


class CellTests(unittest.TestCase):
    """Generated below: one method per cell, so a failure names its cell."""


class StructureTests(unittest.TestCase):
    def test_matrix_has_twenty_cells(self) -> None:
        self.assertEqual(len(EXPECTED), 20)
        self.assertEqual(len(PROVIDERS), 4)
        self.assertEqual(len(CrashPoint), 5)

    def test_row_after_crash_is_the_rfc_state_machine(self) -> None:
        self.assertEqual(ROW_AFTER_CRASH[CrashPoint.BEFORE_INSERT], RowState.NONE)
        self.assertEqual(ROW_AFTER_CRASH[CrashPoint.AFTER_RECEIPT], RowState.DONE)
        for point in (
            CrashPoint.AFTER_INSERT_BEFORE_SEND,
            CrashPoint.AFTER_SEND_BEFORE_RESPONSE,
            CrashPoint.AFTER_RESPONSE_BEFORE_RECEIPT,
        ):
            self.assertEqual(ROW_AFTER_CRASH[point], RowState.PENDING)

    def test_announced_counts(self) -> None:
        pending = [
            (point, name, want)
            for (point, name), want in EXPECTED.items()
            if ROW_AFTER_CRASH[point] is RowState.PENDING
        ]
        self.assertEqual(len(pending), 12)
        self.assertEqual(sum(1 for *_, w in pending if w is Decision.SAFE_RESEND), 3)
        self.assertEqual(sum(1 for *_, w in pending if w is Decision.RESEND_IF_PAYLOAD_IDENTICAL), 3)
        self.assertEqual(sum(1 for *_, w in pending if w is Decision.NEEDS_HUMAN), 6)

    def test_every_cell_has_a_decision(self) -> None:
        for point in CrashPoint:
            for provider in PROVIDERS:
                with self.subTest(cell=f"{point.value}/{provider.name}"):
                    self.assertIn((point, provider.name), EXPECTED)

    def test_a_key_declaration_must_state_its_window(self) -> None:
        with self.assertRaises(ValueError):
            Provider("incomplete", Dedupe.KEY).validate()
        with self.assertRaises(ValueError):
            Provider("overstated", Dedupe.NONE, 86_400).validate()
        self.assertIsNone(KEY.validate())


def _make_cell(point: CrashPoint, provider: Provider, want: Decision):
    def cell(self: unittest.TestCase) -> None:
        self.assertEqual(decide(ROW_AFTER_CRASH[point], provider), want)

    cell.__doc__ = f"{point.value} x {provider.name} -> {want.value}"
    return cell


for _point in CrashPoint:
    for _provider in PROVIDERS:
        _want = EXPECTED[(_point, _provider.name)]
        setattr(
            CellTests,
            f"test_cell_{_point.value}__{_provider.name}",
            _make_cell(_point, _provider, _want),
        )


if __name__ == "__main__":
    unittest.main()
