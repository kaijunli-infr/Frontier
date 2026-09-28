"""Record or check the golden matrix.

    python tests/golden_matrix/run_golden_matrix.py --check
    python tests/golden_matrix/run_golden_matrix.py --record
    python tests/golden_matrix/run_golden_matrix.py --check --case co-location_offline_dense_model_basic_short

``--record`` overwrites ``tests/golden_matrix/goldens/<case>.json`` from the
current worktree. Only record on a commit whose outputs are the agreed baseline,
or after an explicitly approved fidelity change, and say which in the commit.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.golden_matrix import harness  # noqa: E402


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--record", action="store_true", help="write goldens from this worktree")
    mode.add_argument("--check", action="store_true", help="compare this worktree to the goldens")
    parser.add_argument("--case", action="append", help="run selected case IDs only")
    parser.add_argument("--workers", type=int, default=harness.DEFAULT_WORKERS)
    parser.add_argument("--output", type=Path,
                        help="keep run artifacts here (default: a temporary directory)")
    args = parser.parse_args()

    cases = harness.scenarios()
    if args.case:
        cases = [case for case in cases if case["id"] in args.case]
        if len(cases) != len(set(args.case)):
            parser.error("unknown case ID")

    output = args.output.resolve() if args.output else Path(tempfile.mkdtemp(prefix="golden_matrix_"))
    output.mkdir(parents=True, exist_ok=True)
    head = _git_head()

    def report(case, result):
        status = "ERROR" if isinstance(result, Exception) else "RUN"
        print(f"{status} {case['id']}", flush=True)

    results = harness.run_scenarios(cases, output, workers=args.workers, on_result=report)

    failures = []
    for case in cases:
        result = results[case["id"]]
        if isinstance(result, Exception):
            failures.append(f"{case['id']}: {result}")
            continue
        if args.record:
            harness.GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
            harness.golden_path(case["id"]).write_text(
                json.dumps({"recorded_from": head, **result}, indent=1, sort_keys=False) + "\n",
                encoding="utf-8",
            )
            continue
        path = harness.golden_path(case["id"])
        if not path.exists():
            failures.append(f"{case['id']}: no golden at {path}; run --record")
            continue
        try:
            harness.compare_digest(harness.load_golden(case["id"]), result)
        except AssertionError as error:
            failures.append(f"{case['id']}: {error}")

    verb = "recorded" if args.record else "checked"
    print(f"{len(cases) - len(failures)} {verb}, {len(failures)} failed; artifacts: {output}")
    for line in failures:
        print(f"  {line}")
    return int(bool(failures))


if __name__ == "__main__":
    sys.exit(main())
