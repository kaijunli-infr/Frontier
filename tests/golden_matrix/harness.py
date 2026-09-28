"""Golden-matrix safety net for refactors.

Every release example scenario from ``tests/integration/run_scheduler_refactor_fidelity.py``
is run in dummy predictor mode and reduced to a JSON digest that is checked into
``tests/golden_matrix/goldens/``. A refactor that changes any final metric, or any
row of the stage, transfer, or EP-wave ledgers, fails the comparison.

Digest layout per scenario:

- ``request_metrics.csv``, ``system_metrics.json`` and every other CSV are stored
  verbatim so a drift can be read off the diff.
- ``*.jsonl`` ledgers are stored as a row count plus a SHA-256 over their
  canonical form (sorted keys, floats rounded to ``FLOAT_DIGITS`` significant
  digits) because they run to hundreds of kilobytes per scenario. To locate a
  ledger drift, replay the scenario with the two-worktree fidelity harness.

This is dummy-mode structural evidence, not trained numerical parity.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from tests.integration.run_scheduler_refactor_fidelity import (
    case_invocation,
    compare,
    load_artifact,
    scenarios,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_DIR = Path(__file__).resolve().parent / "goldens"
DIGEST_VERSION = 1
FLOAT_DIGITS = 12
RUN_TIMEOUT_S = 300
DEFAULT_WORKERS = 4

__all__ = [
    "GOLDEN_DIR",
    "REPO_ROOT",
    "scenarios",
    "golden_path",
    "load_golden",
    "run_scenario",
    "run_scenarios",
    "compare_digest",
]


def golden_path(case_id: str) -> Path:
    return GOLDEN_DIR / f"{case_id}.json"


def load_golden(case_id: str) -> dict:
    return json.loads(golden_path(case_id).read_text(encoding="utf-8"))


def _canonical(value):
    if isinstance(value, float):
        return float(f"{value:.{FLOAT_DIGITS}g}")
    if isinstance(value, dict):
        return {key: _canonical(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    return value


def _ledger_digest(rows: list) -> dict:
    sha = hashlib.sha256()
    for row in rows:
        sha.update(json.dumps(_canonical(row), separators=(",", ":")).encode("utf-8"))
        sha.update(b"\n")
    return {"kind": "hash", "rows": len(rows), "sha256": sha.hexdigest()}


def digest_metrics_dir(metrics_dir: Path) -> dict:
    artifacts = {}
    for path in sorted(metrics_dir.rglob("*")):
        name = str(path.relative_to(metrics_dir))
        if path.suffix == ".jsonl":
            artifacts[name] = _ledger_digest(load_artifact(path))
        elif path.suffix == ".csv":
            artifacts[name] = {"kind": "rows", "rows": load_artifact(path)}
        elif path.name == "system_metrics.json":
            artifacts[name] = {"kind": "json", "value": load_artifact(path)}
    return artifacts


def run_scenario(case: dict, output: Path, root: Path = REPO_ROOT) -> dict:
    """Run one scenario and return its digest. Raises on a failed run."""
    run_dir = output / case["id"]
    run_dir.mkdir(parents=True, exist_ok=False)
    command, settings = case_invocation(case, root, run_dir)
    with (run_dir / "run.log").open("w") as log:
        proc = subprocess.run(
            command, cwd=root, env={**os.environ, **settings},
            stdout=log, stderr=subprocess.STDOUT, timeout=RUN_TIMEOUT_S,
        )
    if proc.returncode:
        raise RuntimeError(
            f"{case['id']}: exit code {proc.returncode}; see {run_dir / 'run.log'}"
        )
    metric_paths = list((run_dir / "metrics").rglob("request_metrics.csv"))
    if len(metric_paths) != 1:
        raise RuntimeError(f"{case['id']}: expected one request_metrics.csv under {run_dir}")
    artifacts = digest_metrics_dir(metric_paths[0].parent)
    completed = len(artifacts["request_metrics.csv"]["rows"])
    if completed != case["expected_requests"]:
        raise RuntimeError(
            f"{case['id']}: completed {completed} requests, expected {case['expected_requests']}"
        )
    return {
        "digest_version": DIGEST_VERSION,
        "scenario": case,
        "artifacts": artifacts,
    }


def run_scenarios(cases: list, output: Path, workers: int = DEFAULT_WORKERS,
                  root: Path = REPO_ROOT, on_result=None) -> dict:
    """Run ``cases`` concurrently; map case id -> digest or the raised exception."""
    results = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(run_scenario, case, output, root): case for case in cases}
        for future in as_completed(futures):
            case = futures[future]
            try:
                results[case["id"]] = future.result()
            except Exception as error:  # noqa: BLE001 - surfaced per case
                results[case["id"]] = error
            if on_result is not None:
                on_result(case, results[case["id"]])
    return results


def compare_digest(golden: dict, actual: dict) -> None:
    """Raise AssertionError naming the first field that drifted from the golden."""
    assert golden["digest_version"] == actual["digest_version"], "digest_version differs"
    assert golden["scenario"] == actual["scenario"], "scenario definition differs"
    golden_artifacts, actual_artifacts = golden["artifacts"], actual["artifacts"]
    assert sorted(golden_artifacts) == sorted(actual_artifacts), (
        f"artifact set differs: {sorted(golden_artifacts)} != {sorted(actual_artifacts)}"
    )
    for name in sorted(golden_artifacts):
        compare(golden_artifacts[name], actual_artifacts[name], path=name)
