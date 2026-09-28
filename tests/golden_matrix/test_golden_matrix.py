"""Pytest entry for the golden matrix.

Selected cases run once, concurrently, in a session fixture; each parametrized
test then compares its digest to the checked-in golden. Use ``-k <case id>`` to
narrow the run and ``FRONTIER_GOLDEN_WORKERS`` to change concurrency.
"""

from __future__ import annotations

import os

import pytest

from tests.golden_matrix import harness

CASES = harness.scenarios()
CASE_IDS = [case["id"] for case in CASES]


def _selected_case_ids(session) -> set[str]:
    selected = set()
    for item in session.items:
        callspec = getattr(item, "callspec", None)
        if callspec is not None and "case" in callspec.params:
            selected.add(callspec.params["case"]["id"])
    return selected


@pytest.fixture(scope="session")
def golden_results(request, tmp_path_factory):
    selected = _selected_case_ids(request.session)
    cases = [case for case in CASES if case["id"] in selected]
    workers = int(os.environ.get("FRONTIER_GOLDEN_WORKERS", harness.DEFAULT_WORKERS))
    output = tmp_path_factory.mktemp("golden_matrix")
    return harness.run_scenarios(cases, output, workers=workers)


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_scenario_matches_golden(case, golden_results):
    path = harness.golden_path(case["id"])
    assert path.exists(), f"missing golden {path}; run tests/golden_matrix/run_golden_matrix.py --record"
    result = golden_results[case["id"]]
    if isinstance(result, Exception):
        raise AssertionError(str(result))
    harness.compare_digest(harness.load_golden(case["id"]), result)


def test_every_golden_has_a_scenario():
    stray = sorted(
        path.stem for path in harness.GOLDEN_DIR.glob("*.json") if path.stem not in CASE_IDS
    )
    assert not stray, f"goldens without a scenario: {stray}"
