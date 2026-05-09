# ADR-0006: Ship v1 with the cosine-similarity threshold disabled

**Status:** Accepted
**Supersedes:** Initial scaffolded default of `0.3`

## Context

The retrieval pipeline scores candidate chunks against the user's query using
cosine similarity, then optionally discards chunks below a threshold before
passing the survivors to the cross-encoder reranker. The scaffolded
configuration set `REPOSAGE_SIMILARITY_THRESHOLD = 0.3`.

That value was inherited from common RAG tutorials. We need to either justify
it, replace it with a calibrated number, or disable it.

Two facts about the embedding model in use (`nomic-embed-text-v1.5`) make `0.3`
suspect:

**1. Anisotropy.** Modern transformer-based embedding models concentrate their
outputs in a narrow cone on the unit hypersphere rather than spreading evenly
across it. The empirical consequence is that the cosine similarity between two
*unrelated* pieces of text typically lands around **0.4–0.5**, not near zero.
The discriminative band — where genuinely relevant pairs separate from
unrelated ones — sits around **0.45–0.65**. A threshold of `0.3` is below that
noise floor; it filters nothing of consequence.

**2. Score distributions are model-specific.** A threshold that works for
`all-MiniLM-L6-v2` does not transfer to `nomic-embed-text-v1.5`. Each model has
its own anisotropy and discriminative band. Magic numbers copied from a tutorial
carry the bias of whichever model the tutorial used.

We have no labeled evaluation data yet, so any specific non-zero threshold we
pick today is a guess.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| Keep the scaffolded `0.3` | No code change. | Below the noise floor for `nomic-embed`; filters nothing in practice — false sense of precision. |
| Calibrate empirically now | Defensible, model-specific number. | Requires labeled (query, relevant, irrelevant) triples we do not yet have. Premature. |
| Hardcode a higher guess (e.g., `0.5`) | Closer to the noise floor than `0.3`. | Still a guess. Risks discarding chunks the reranker would have rescued. |
| **Disable the threshold (`0.0`)** | Honest about the absence of evidence; the cross-encoder reranker is the precision filter regardless. | Slightly larger candidate set reaches the reranker (top-K = 20 chunks; cost is negligible). |

## Decision

Set the default `REPOSAGE_SIMILARITY_THRESHOLD = 0.0` for v1. Calibrate the
threshold per-model during the evaluation phase, once labeled triples exist.

## Consequences

**Positive:**

- Behaviour matches the evidence we have: we do not pre-filter on a number we
  cannot defend.
- The downstream cross-encoder reranker is significantly better than cosine at
  separating relevant from irrelevant chunks. Disabling the upstream threshold
  cannot discard candidates the reranker might have rescued.
- The setting remains user-tunable via `REPOSAGE_SIMILARITY_THRESHOLD`;
  operators on a different embedder can override.

**Negative:**

- A slightly larger candidate set reaches the reranker — top-K = 20 chunks
  rather than some smaller post-filter set. The reranker's per-call cost is
  tens of milliseconds at this size, so the overhead is not material.

## Revisit when

The evaluation phase produces:

1. Labeled (query, relevant chunk, irrelevant chunk) triples on a few seed
   repositories.
2. The cosine-similarity score distribution of relevant pairs vs. irrelevant
   pairs, plotted side-by-side.

If those distributions separate cleanly above some value `t`, set the default
to `t`. If they do not separate cleanly, document the result and ship with the
threshold permanently disabled — accept that the reranker is the precision
stage and stop pretending the cosine score is one.

## References

- Ethayarajh, K. (2019). *How Contextual are Contextualized Word Representations?
  Comparing the Geometry of BERT, ELMo, and GPT-2 Embeddings.* — measured
  anisotropy of transformer outputs.
- The cross-encoder used downstream: `cross-encoder/ms-marco-MiniLM-L-6-v2`.
