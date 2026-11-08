# idem-replay

Decide whether an interrupted effectful call may be **resent**, or whether it needs a
human, from the dedupe behaviour the tool's provider actually has.

A ledger records a key before a call and the receipt after it. The interesting state is the
one in between: the process died, the row says `pending`, and nobody knows whether the email
went out. Resending may duplicate an effect; not resending may drop one. The answer depends
on what the provider will do when it sees the same request twice — and that is a property
of the provider, not of your code.

This tool takes that property as a declaration and answers the question for each of the five
places a process can die.

```
$ python3 -m idem_replay --cell after_send_before_response/no_dedupe
after_send_before_response/no_dedupe  row=pending  decision=needs_human
```

## What it is

A decision table of twenty cells — five crash points against four provider behaviours — with
one unit test per cell, and a CLI that applies the same table to the tools you declare.

| crash point | ledger row left behind |
| --- | --- |
| `before_insert` | `none` |
| `after_insert_before_send` | `pending` |
| `after_send_before_response` | `pending` |
| `after_response_before_receipt` | `pending` |
| `after_receipt` | `done` |

| provider behaviour | meaning |
| --- | --- |
| `key_in_window` | dedupes on the key you send, and the replay lands inside its retention window |
| `key_outside_window` | same, but the key has been pruned |
| `no_dedupe` | no caller-supplied key and no content comparison |
| `payload_keyed` | compares the request body, so only byte-identical replays collapse |

The five decisions are `no_action`, `already_recorded`, `safe_resend`,
`resend_if_payload_identical` and `needs_human`.

```console
$ python3 -m idem_replay --summary
{
  "by_decision": {
    "already_recorded": 4,
    "needs_human": 6,
    "no_action": 4,
    "resend_if_payload_identical": 3,
    "safe_resend": 3
  },
  "by_row": {
    "done": 4,
    "none": 4,
    "pending": 12
  },
  "cells": 20,
  "crash_points": 5,
  "pending_cells": 12,
  "pending_rescue_fraction": 0.25,
  "pending_rescued_by_key": 3,
  "providers": 4
}
```

Twelve cells can leave a `pending` row, which is where the whole question lives. A live
provider key rescues **3 of those 12**. Three more are safe only if the replay body is
byte-identical. **Six need a human** — and those six are not a rounding error, they are the
providers nobody can check for you.

## What it is not

- **No provider API was ever called.** No account, no key, no request. The claims about
  dedupe windows and parameter comparison are quotations from a provider's public
  documentation, gathered in [EVIDENCE.md](EVIDENCE.md), and the fourth behaviour is a
  construction of mine with **no citation at all**. That file says which is which, per row.
- **Not a ledger.** There is no storage, no unique index, no transaction. The row state is an
  input you pass in; the guarantee that the row exists before the call is yours to keep.
- **Not a retry driver.** It decides; it does not send. There is no HTTP client in this
  repository.
- **`payload_keyed` is not verified.** I found no provider documented to behave exactly that
  way. The row exists because the RFC lists it as a declarable behaviour, and it is the row I
  would check first if you have a real provider in mind.
- **The RFC's `unknown` row is not modelled as a state here.** Upstream, `unknown` is the row
  a human resolves after the fact. Here the input is `pending` at a crash point and the output
  is `needs_human`, so `unknown` is the name of a conclusion rather than of a row. `failed`
  and `revoked` are out of scope: they are decisions the ledger already made, not crash points.

## Reproduce every number

```console
$ python3 -m unittest discover -s tests
Ran 25 tests in 0.000s

OK
```

Twenty of those are one per cell; the other five check the structure the matrix rests on —
that there are twenty cells, that the crash points map to the RFC's row states, that the
counts above are the counts above, that every cell has a decision, and that a declaration
which dedupes on a key but omits its window is refused.

The tests are only evidence if they fail when the table is wrong, so a plant proves it:

```console
$ python3 tools/plant.py
baseline: 0 failing cells
ok   ignore the window on a key-deduping provider: 3 cells failed, exactly the ones that depend on it
ok   treat a payload-deduping provider as having no dedupe: 3 cells failed, exactly the ones that depend on it
restored: 0 failing cells
```

Each plant rewrites one line of `idem_replay/model.py`, requires that **exactly** the cells
depending on that line fail, and restores the file. Both currently kill three cells and no
others; the script exits non-zero if a plant stops biting, so a green run is a claim about
today rather than about the day it was written.

## Use it on your own tools

```console
$ cat examples/declaration.json
{"tools": [{"name": "charge_card", "dedupe": "key", "window_seconds": 86400, ...}]}

$ python3 -m idem_replay --declare examples/declaration.json
before_insert/charge_card                         none     no_action
after_insert_before_send/charge_card              pending  safe_resend
after_send_before_response/charge_card            pending  safe_resend
after_response_before_receipt/charge_card         pending  safe_resend
after_receipt/charge_card                         done     already_recorded
...
```

Three declared tools give fifteen rows. A declaration that says it dedupes on a key without
saying for how long is refused, because the same row is a safe resend inside the window and a
possible second effect outside it:

```console
$ python3 -m idem_replay --declare examples/incomplete-declaration.json; echo "exit $?"
declaration refused: 'charge_card' dedupes on a key but declares no window_seconds; inside and outside that window are different answers
exit 2
```

## The least certain parts

1. **`payload_keyed`.** A construction, not a citation. If your provider normalises the body
   before comparing — sorted keys, trimmed whitespace, dropped nulls — then "byte-identical"
   is the wrong test and this row is wrong with it.
2. **The window boundary.** The provider says keys may be pruned "after they're at least 24
   hours old", so 86400 seconds is a floor. A replay at 25 hours may still be deduplicated;
   the table answers `needs_human` there, which is the safe direction but not the true one.
3. **Same key, different parameters.** A key-deduping provider compares parameters and errors
   on a mismatch, so that case is refused rather than acted on twice. The twenty cells do not
   separate it from a like-for-like replay, because both are `safe_resend` in the sense that
   neither can cause a second effect — but only one of them proceeds.
4. **The row still has to exist.** Every answer marked `safe_resend` assumes the `pending` row
   was committed before the call left. If it was not, the key never reached the provider and
   there is nothing to deduplicate against.

## Layout

```
idem_replay/model.py    the row states, the declarations, the decision function
idem_replay/matrix.py   the twenty cells and their counts
idem_replay/cli.py      --summary, --json, --cell, --declare
tests/test_cells.py     one test per cell, plus the structure
tools/plant.py          proves the tests bite
EVIDENCE.md             what stands behind each declared behaviour
```

MIT licensed. Python 3.11 or newer, standard library only — no dependencies to install, so the
reproduction above is the whole setup.
