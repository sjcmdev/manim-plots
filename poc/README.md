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
