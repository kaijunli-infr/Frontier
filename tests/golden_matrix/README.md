# Golden matrix

A checked-in numeric safety net for refactors. It runs the 58 release example
scenarios defined in `tests/integration/run_scheduler_refactor_fidelity.py`
(dense/MoE, offline/online, co-location/PDD/PD-AF, chunked/unchunked prefill,
Thinking Mode, Speculative Decoding, Prefix Caching, attention-DP with EP,
CUDA Graph) in dummy predictor mode and compares each run's metrics artifacts
to a digest under `goldens/`.

The full matrix runs in well under a minute with 8 workers.

## Run

```bash
export PYTHONPATH=$PWD
python -m pytest tests/golden_matrix -q                # full matrix
python -m pytest tests/golden_matrix -q -k pdd_offline # a subset
FRONTIER_GOLDEN_WORKERS=8 python -m pytest tests/golden_matrix -q
python tests/golden_matrix/run_golden_matrix.py --check --workers 8
```

`--check` prints every drifted field as `<artifact>.<path>: <golden> != <actual>`.

## What is compared

| Artifact | Stored as | Compared |
|---|---|---|
| `request_metrics.csv`, other CSVs | full rows | every field, floats at rel 1e-12 |
| `system_metrics.json` | full document | every field, floats at rel 1e-12 |
| `*.jsonl` ledgers (stage, transfer, EP wave) | row count + SHA-256 of canonical rows | exact |

Canonical ledger rows sort keys and round floats to 12 significant digits, so
formatting-only differences do not change the hash. A ledger hash mismatch says
that a ledger changed but not where; replay the case with the two-worktree
fidelity harness to see the row:

```bash
python tests/integration/run_scheduler_refactor_fidelity.py \
  --baseline /path/to/baseline-worktree --candidate $PWD \
  --output /tmp/fidelity --case <case id>
```

## Re-recording

```bash
python tests/golden_matrix/run_golden_matrix.py --record --workers 8
```

Re-record only from a commit whose outputs are the agreed baseline, or after an
explicitly approved fidelity change, and name the reason in the commit message.
Each golden records the commit it was taken from in `recorded_from`; that field
is informational and not compared.

This is dummy-mode structural evidence. It proves a refactor preserved the
simulator's control flow and accounting, not trained numerical parity.
