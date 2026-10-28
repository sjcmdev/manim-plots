# Proofs of concept

Four throwaway experiments that tested the mechanism behind ADR 0001 before it was
frozen. Their reports are in `docs/poc/`. The code is frozen evidence: it is not part of
the package, not collected by the default `pytest` run, and not maintained.

| Directory | Report |
|---|---|
| `poc1/` | `docs/poc/poc1-points-property.md` |
| `poc2/` | `docs/poc/poc2-frame-lifecycle.md` |
| `poc3/` | `docs/poc/poc3-stack-context.md` |
| `poc4/` | `docs/poc/poc4-keyed-alignment.md` — the model closest to production |

Run a suite from the repository root with `python -m pytest poc/poc4 -p no:cacheprovider`.
The `python -m pocN.<module>` commands in the reports need this directory on the path:
`$env:PYTHONPATH = "poc"` in PowerShell, `PYTHONPATH=poc` in a POSIX shell. A run
overwrites the JSON in `pocN/results/`, which is the evidence the report quotes;
restore it with `git restore poc` unless the rerun is the point.

What the evidence is and is not:

- `poc/poc2/model.py`, `poc/poc3/baseline_model.py` and `poc/poc4/baseline_model.py` are
  one file: PoC 3 and 4 keep a frozen copy of PoC 2's model as the baseline they
  regress against (`docs/poc/poc3-stack-context.md`, on `baseline_model.py`).
- `poc/poc2/results/` also holds 85 JSON files that the frozen suite no longer writes:
  outputs of earlier runs under an earlier naming. They are kept, and no report number
  rests on them alone.
- `poc/poc4/results/summary.json` is a snapshot aggregated from an earlier run, and the
  report quotes it. Several raw files beside it come from later reruns, so aggregating
  them again gives other numbers: for the parameter workload, update p95 4.04 ms in
  `l7_parameter_cost.json` against 3.91 ms in the summary. Neither is a production
  measurement; F-1001 is measured on the library (`tests/benchmark/`).
- PoC 1's images (`property.png`, `plain.png`) are written by its test and not tracked.
