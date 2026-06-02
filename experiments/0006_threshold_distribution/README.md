# Experiment 0006 — Cosine similarity distribution on nomic-embed-text-v1.5

**Proves:** [ADR-0006 — Ship v1 with the cosine-similarity threshold disabled](../../docs/decisions/0006-disable-similarity-threshold-v1.md)

## Hypothesis

The scaffolded default `REPOSAGE_SIMILARITY_THRESHOLD = 0.3` sits **below** the
anisotropy noise floor of `nomic-embed-text-v1.5`. If true, even *unrelated*
pieces of code and prose will routinely score above `0.3`, making the threshold
filter nothing of consequence.

## Method

1. Take ~25 short text samples from RepoSage's own domain — a mix of Python
   snippets, English prose, and config keys. None of the pairs are curated for
   relevance; we treat them all as "random pairs" and measure what cosine
   similarity does on them.
2. Embed each with `nomic-embed-text-v1.5` using the required
   `search_document:` task prefix and L2-normalised output.
3. Compute pairwise cosine similarity across all unique pairs — the upper
   triangle of the similarity matrix, excluding the diagonal.
4. Plot the distribution as a histogram. Mark `0.3` as a vertical line so the
   noise floor is visible relative to the scaffolded threshold.
5. Report summary statistics: mean, median, std dev, min, max, and the fraction
   of pairs scoring above `0.3`.

## Expected outcome

If anisotropy is in play, the distribution should land around **0.4–0.5** with
a relatively tight spread. The fraction of pairs above `0.3` should be close to
**100%** — confirming that the threshold filters nothing.

If the mean is near `0.0`, anisotropy is not in effect and the threshold could
be useful with calibration. (Not expected — every published study on
transformer-output anisotropy says otherwise — but the point of the experiment
is to measure rather than assume.)

## Run it

```bash
uv sync --extra experiments
uv run python experiments/0006_threshold_distribution/run.py
```

Outputs `results.md` and `distribution.png` next to the script; both get
committed so the ADR's evidence is always traceable to a real run.
