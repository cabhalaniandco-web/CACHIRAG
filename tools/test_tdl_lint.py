#!/usr/bin/env python3
"""Tests for tools/tdl_lint.py.

Run: python3 tools/test_tdl_lint.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tdl_lint import lint  # noqa: E402

HERE = Path(__file__).resolve().parent
ADDON = HERE.parent / "tally" / "GSTR2B_Portal_ImportButtons.tdl"
BROKEN = HERE / "testdata" / "broken_sample.tdl"

# Every defect marked in the fixture, as a substring of the expected message.
EXPECTED_IN_BROKEN = [
    "UDF index 20001 is used twice",
    "UDF index 101 is outside the developer range",
    "references undefined [Form: Sample Missing Form]",
    "references undefined [Line: Sample Missing Line]",
    "references undefined [Field: Sample Missing Field]",
    "references undefined [Collection: Sample Missing Collection]",
    "stores into undeclared UDF 'SampleUndeclaredUDF'",
    "reads undeclared UDF $SampleAlsoUndeclaredUDF",
    "filter 'SampleMissingFilter' has no [System: Formula] entry",
    "references undefined [Function: Sample Missing Function]",
    "uses @@SampleMissingFormula with no definition",
    "assigns to undeclared variable 'vundeclared'",
    "step 15 does not come after step 20",
    "uses undeclared variable ##vAlsoUndeclared",
    "ELSE takes no condition",
    "calls a function whose name contains a space",
    "passes a method reference inline to $$Function",
    "unclosed IF block",
    "without SET TARGET : ..",
]


def main() -> int:
    failures: list[str] = []

    broken = lint(BROKEN)
    for expected in EXPECTED_IN_BROKEN:
        if not any(expected in message for message in broken.errors):
            failures.append(f"linter missed the defect: {expected}")
    print(f"{BROKEN.name}: {len(broken.errors)} error(s) reported, "
          f"{len(EXPECTED_IN_BROKEN) - len(failures)}/{len(EXPECTED_IN_BROKEN)} expected defects found")

    addon = lint(ADDON)
    for message in addon.errors:
        failures.append(f"add-on should be clean but got: {message}")
    print(f"{ADDON.name}: {len(addon.errors)} error(s), {len(addon.warnings)} warning(s)")

    if failures:
        print()
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
