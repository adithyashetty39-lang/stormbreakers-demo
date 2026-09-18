"""The deliberately flaky test used for the flaky-vs-regression demo.

DEMO NOTE (Team Stormbreakers): true `random.random()` flakiness is hard to
control right before judging — you cannot guarantee "3 of the last 10 runs
failed" on demand. So this test's flakiness is DETERMINISTIC and driven by
`GITHUB_RUN_NUMBER` (a real env var GitHub Actions sets on every run,
auto-incrementing per workflow file). It fails on every 3rd run:

    run 1 pass, run 2 pass, run 3 FAIL, run 4 pass, run 5 pass, run 6 FAIL, ...

That gives you a ~1-in-3 historical failure rate you can *plan around*: push
~10 throwaway commits to main before the event (see README "Seed run
history") and you know in advance which run numbers failed, so the
Build & Test Agent's `get_test_history` call has a real, reproducible
pattern to reason about instead of hoping real flakiness cooperates on
demo day.

Locally (no GITHUB_RUN_NUMBER set) it always passes, so it never blocks a
normal `pytest` run for a developer.

To simulate a specific run number locally:
    GITHUB_RUN_NUMBER=3 pytest tests/test_flaky.py
"""
import os

import pytest

from app.pricing import cart_total


def _is_flaky_failure_run() -> bool:
    run_number = os.environ.get("GITHUB_RUN_NUMBER")
    if run_number is None:
        return False
    try:
        return int(run_number) % 3 == 0
    except ValueError:
        return False


def test_cart_total_under_load_flaky():
    """A test that is timing/environment-sensitive in real life.

    The assertion itself is always correct; this simulates the class of
    "passes almost always, fails under specific runner conditions" test
    that real flaky tests are, without depending on actual timing races.
    """
    items = [{"unit_price": 12.5, "quantity": 4}]
    total = cart_total(items)

    if _is_flaky_failure_run():
        pytest.fail(
            "simulated flake: cart total computation exceeded expected "
            "tolerance under CI runner load (GITHUB_RUN_NUMBER="
            f"{os.environ.get('GITHUB_RUN_NUMBER')})"
        )

    assert total == 50.0
