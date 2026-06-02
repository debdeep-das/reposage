# Experiments

Reproducible evidence for the decisions in [`docs/decisions/`](../docs/decisions/).

Each experiment lives in `<adr-id>_<slug>/` with:

- `README.md` — hypothesis, method, expected outcome
- `run.py` — the script (self-contained, runnable)
- `results.md` — observations from the most recent run
- optional `*.png` — plots

## Index

| Experiment | Proves | Status |
|---|---|---|
| [`0006_threshold_distribution/`](0006_threshold_distribution/) | [ADR-0006](../docs/decisions/0006-disable-similarity-threshold-v1.md) — disable similarity threshold for v1 | Complete |

## Running

```bash
uv sync --extra experiments
uv run python experiments/<experiment-name>/run.py
```

Each script writes its outputs (`results.md`, plots) next to itself, so the
evidence committed to git matches the most recent reproducible run.
