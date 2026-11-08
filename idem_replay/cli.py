"""Command line: the matrix, one cell, or your own declared tools."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .matrix import PROVIDERS, cells, summary
from .model import (
    ROW_AFTER_CRASH,
    CrashPoint,
    Decision,
    Dedupe,
    Provider,
    decide,
)


def _providers_from(declaration: Path) -> list[Provider]:
    data = json.loads(declaration.read_text(encoding="utf-8"))
    tools = data.get("tools")
    if not isinstance(tools, list) or not tools:
        raise ValueError('the declaration needs a non-empty "tools" list')
    providers: list[Provider] = []
    for tool in tools:
        provider = Provider(
            name=str(tool["name"]),
            dedupe=Dedupe(str(tool["dedupe"])),
            window_seconds=tool.get("window_seconds"),
            replay_inside_window=bool(tool.get("replay_inside_window", True)),
        )
        provider.validate()
        providers.append(provider)
    return providers


def _print_table(cell_list) -> None:
    width = max(len(cell.name) for cell in cell_list)
    for cell in cell_list:
        print(f"{cell.name:<{width}}  {cell.row.value:<7}  {cell.decision.value}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="idem-replay", description=__doc__)
    parser.add_argument("--json", action="store_true", help="print cells and summary as JSON")
    parser.add_argument("--summary", action="store_true", help="print only the counts")
    parser.add_argument("--cell", help="one cell, as CRASH_POINT/PROVIDER")
    parser.add_argument("--declare", type=Path, help="a JSON file of declared tools")
    args = parser.parse_args(argv)

    if args.declare:
        try:
            providers = _providers_from(args.declare)
        except (ValueError, KeyError, json.JSONDecodeError) as error:
            print(f"declaration refused: {error}", file=sys.stderr)
            return 2
        cell_list = cells(tuple(providers))
    else:
        providers = PROVIDERS
        cell_list = cells()

    if args.cell:
        wanted = args.cell
        match = [cell for cell in cell_list if cell.name == wanted]
        if not match:
            names = ", ".join(cell.name for cell in cell_list)
            print(f"no such cell: {wanted}\nknown cells: {names}", file=sys.stderr)
            return 2
        cell = match[0]
        print(f"{cell.name}  row={cell.row.value}  decision={cell.decision.value}")
        return 0

    if args.summary:
        print(json.dumps(summary(cell_list), indent=2, sort_keys=True))
        return 0

    if args.json:
        payload = {
            "cells": [
                {
                    "name": cell.name,
                    "crash_point": cell.crash_point.value,
                    "provider": cell.provider.name,
                    "row": cell.row.value,
                    "decision": cell.decision.value,
                }
                for cell in cell_list
            ],
            "summary": summary(cell_list),
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    _print_table(cell_list)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
