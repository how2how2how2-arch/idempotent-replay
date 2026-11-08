"""Prove the per-cell tests bite when the decision table is wrong.

Each plant rewrites one line of idem_replay/model.py, runs the suite in a
subprocess, and requires that the set of failing cells is exactly the set that
depends on the rewritten line. The file is restored in a finally block, and a
plant that does not bite is itself a failure.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / "idem_replay" / "model.py"
# Only a verdict line names a failing cell. The verbose listing names every
# test, passing ones included, so matching it would read the instrument's
# inventory as its judgement and report a green suite as fully red.
CELL = re.compile(r"^(?:ERROR|FAIL): test_cell_(\w+?)__(\w+)", re.MULTILINE)

PENDING = (
    "after_insert_before_send",
    "after_send_before_response",
    "after_response_before_receipt",
)

PLANTS = (
    (
        "ignore the window on a key-deduping provider",
        "    if provider.dedupe is Dedupe.KEY and provider.replay_inside_window:",
        "    if provider.dedupe is Dedupe.KEY:",
        {f"{point}__key_outside_window" for point in PENDING},
    ),
    (
        "treat a payload-deduping provider as having no dedupe",
        "    if provider.dedupe is Dedupe.PAYLOAD:\n"
        "        return Decision.RESEND_IF_PAYLOAD_IDENTICAL\n",
        "",
        {f"{point}__payload_keyed" for point in PENDING},
    ),
)


def failing_cells() -> set[str]:
    run = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    text = run.stdout + run.stderr
    return {f"{a}__{b}" for a, b in CELL.findall(text)}


def main() -> int:
    original = MODEL.read_text(encoding="utf-8")
    baseline = failing_cells()
    if baseline:
        print(f"REFUSED: the unplanted suite already fails on {sorted(baseline)}")
        return 2
    print("baseline: 0 failing cells")

    failures = 0
    try:
        for name, old, new, expected in PLANTS:
            if original.count(old) != 1:
                print(f"REFUSED {name}: the line to rewrite appears {original.count(old)} times")
                return 2
            mutant = original.replace(old, new)
            if mutant == original:
                print(f"REFUSED {name}: the mutant is identical to the original")
                return 2
            MODEL.write_text(mutant, encoding="utf-8")
            got = failing_cells()
            MODEL.write_text(original, encoding="utf-8")
            if got == expected:
                print(f"ok   {name}: {len(got)} cells failed, exactly the ones that depend on it")
            else:
                failures += 1
                print(f"FAIL {name}: expected {sorted(expected)}")
                print(f"                     got      {sorted(got)}")
    finally:
        MODEL.write_text(original, encoding="utf-8")

    restored = failing_cells()
    if restored:
        print(f"FAIL restore: {sorted(restored)} still failing")
        failures += 1
    else:
        print("restored: 0 failing cells")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
