# RepoSage

Ask natural-language questions about a GitHub repository. Answers are grounded
in the repo's actual code and documentation, with `file:line` citations back to
the source.

A hand-rolled RAG pipeline — no LangChain. The non-obvious technical choices
(embedder, chunker, retrieval thresholds, reranking) are documented as ADRs in
[`docs/decisions/`](docs/decisions/).

## How it works

Two pipelines.

**Ingestion** — run once per repo, refreshes on update:

```
GitHub API → file filter → AST-aware chunking → embed → ChromaDB
```

**Query** — per question:

```
question → embed → top-20 retrieval → cross-encoder rerank → top-5 to Claude → cited answer
```

Component layout:

```
reposage/
├── api/         FastAPI routes — no business logic
├── core/        Chunking, embedding, retrieval, synthesis — pure logic, no framework deps
├── ingestion/   GitHub fetch, file filtering, pipeline orchestration
├── store/       Vector store interface, ChromaDB-backed
└── models/      Pydantic schemas — single source of truth for contracts
```

## Tech stack

| Layer | Choice |
|---|---|
| API | FastAPI (async throughout) |
| Embeddings | [`nomic-ai/nomic-embed-text-v1.5`](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5) |
| Chunking | [`tree-sitter`](https://tree-sitter.github.io/) — AST-aware, per-language |
| Vector DB | [ChromaDB](https://www.trychroma.com/), one collection per repo |
| Reranking | `cross-encoder/ms-marco-MiniLM-L-6-v2` via sentence-transformers |
| Synthesis | Claude (`claude-opus-4-7`) — synthesis only, never retrieval |
| Eval | [RAGAS](https://docs.ragas.io/) |

Python 3.11+. Dependency management via [`uv`](https://github.com/astral-sh/uv).

## Quickstart

```bash
uv sync
cp .env.example .env  # add REPOSAGE_GITHUB_TOKEN and REPOSAGE_ANTHROPIC_API_KEY
```

API and CLI entry points are landing in Phase 1; see status below.

## Status

| Phase | Scope | Status |
|---|---|---|
| 1 | Ingestion pipeline (chunking, embedding, ChromaDB writes) | In progress |
| 2 | Query pipeline (retrieval, reranking, Claude synthesis) | Not started |
| 3 | Evaluation harness with RAGAS, threshold calibration | Not started |

## License

Apache 2.0. See [`LICENSE`](LICENSE).
