# RepoSage — Claude Code Context

This file is the project context Claude Code reads at the start of each session.
Hard constraints, naming conventions, and architectural decisions live here so the
agent's suggestions stay aligned with the codebase. For the *why* behind specific
technical choices, see [`docs/decisions/`](docs/decisions/).

## Project Overview

RepoSage is a RAG-based developer tool that lets users ask natural language questions
about any GitHub repository. It indexes a repo's code and documentation, stores
semantic embeddings in ChromaDB, and uses Claude as the synthesis layer to answer
questions grounded in the actual codebase.

Target users: developers onboarding to an unfamiliar codebase, doing code reviews,
or exploring open-source projects.

---

## Architecture

Two distinct pipelines:

### Ingestion Pipeline (run once per repo / on update)
```
GitHub API → filter files → AST-aware chunking → embed chunks → store in ChromaDB
```

### Query Pipeline (per user question)
```
question → embed → retrieve top-20 → rerank top-5 → Claude synthesis → answer with citations
```

### Component Map
```
reposage/
├── api/                    # FastAPI layer — routes only, no business logic
│   └── routes/
│       ├── ingest.py       # POST /ingest, GET /status/{job_id}
│       ├── query.py        # POST /query
│       └── repos.py        # GET /repos, DELETE /repos/{id}
├── core/                   # Pure business logic, no framework dependencies
│   ├── chunking/
│   │   ├── base.py         # Abstract BaseChunker
│   │   ├── code_chunker.py # AST-aware via tree-sitter
│   │   └── text_chunker.py # Markdown/prose chunker
│   ├── embedding/
│   │   └── embedder.py     # Abstracted — swappable model behind interface
│   ├── retrieval/
│   │   ├── retriever.py    # ChromaDB vector search
│   │   └── reranker.py     # Cross-encoder reranking
│   └── synthesis/
│       └── claude_client.py
├── ingestion/
│   ├── pipeline.py         # Orchestrates full ingestion flow
│   ├── github_loader.py    # GitHub API + gitpython
│   └── filters.py          # File inclusion/exclusion rules
├── store/
│   └── chroma_store.py     # Abstracted vector store interface
├── models/
│   └── schemas.py          # All Pydantic models — single source of truth
└── config.py               # Pydantic Settings — env-driven config
```

---

## Tech Stack

| Layer | Library | Notes |
|---|---|---|
| API | FastAPI | Async throughout |
| Validation | Pydantic v2 | Settings + request/response schemas |
| Vector DB | ChromaDB | One collection per repo |
| Embeddings | `nomic-ai/nomic-embed-text-v1.5` | Handles code + prose in same vector space |
| Chunking | `tree-sitter` | AST-aware, per-language parsers |
| Reranking | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Via sentence-transformers |
| GitHub | `PyGithub` + `gitpython` | API access + local clone fallback |
| LLM | Anthropic Claude API | Synthesis only — not retrieval |
| Eval | RAGAS | Retrieval quality evaluation |

**Python version: 3.11+**

---

## Coding Conventions

### General
- Type hints everywhere — no untyped function signatures
- Pydantic models for all data contracts — no raw dicts crossing layer boundaries
- Dataclasses for internal value objects with no validation needs
- `pathlib.Path` over `os.path` always

### Async
- All I/O is async — GitHub calls, ChromaDB writes, Claude API
- CPU-bound work (embedding, chunking) runs in `asyncio.run_in_executor`
- No `time.sleep` — use `asyncio.sleep`

### Error Handling
- Custom exception hierarchy in `core/exceptions.py`
- Never catch bare `Exception` — catch specific types
- FastAPI exception handlers at the boundary — core raises, API catches and maps
- All external API calls have retry logic with exponential backoff

### Abstractions
- External services sit behind abstract interfaces (vector store, embedder, chunker)
- Concrete implementations injected via FastAPI `Depends()`
- This enables swapping ChromaDB → Qdrant or MiniLM → CodeBERT without touching business logic

### Naming
- `snake_case` for everything Python
- Collections in ChromaDB: `{owner}__{repo}@{commit_sha}` (double underscore as separator)
- Job IDs: `uuid4` strings
- Environment variables: `REPOSAGE_` prefix for all app config

---

## Hard Constraints

These are non-negotiable architectural decisions. Do not suggest alternatives:

- **No LangChain** — all pipeline logic is explicit and hand-rolled
- **No global state** — everything injected, nothing imported from a singleton module
- **No raw string prompts scattered in code** — prompts live in `core/synthesis/prompts.py`
- **No synchronous I/O in async endpoints** — use executor for blocking calls
- **ChromaDB collections are immutable after creation** — re-ingest creates a new collection, old one deleted explicitly
- **Claude is synthesis only** — retrieval is always vector search + reranking, never ask Claude to search

---

## Ingestion Rules

### Files to Index
Include: `.py`, `.ts`, `.js`, `.go`, `.rs`, `.java`, `.cpp`, `.c`, `.rb`, `.md`, `.rst`,
`pyproject.toml`, `package.json`, `Dockerfile`, `*.yaml`, `*.yml`

Exclude: `node_modules/`, `.git/`, `dist/`, `build/`, `__pycache__/`, `*.lock`,
`*.min.js`, binary files, images, files > 500KB

### Chunking
- Code files: AST-aware via tree-sitter (class → method → block hierarchy)
- Prose files: Sentence-aware with 20% overlap
- Chunk size target: 512 tokens **by the embedder's tokenizer** (`nomic-embed-text-v1.5`, WordPiece). Hard cap: 8192 tokens (the embedder's max sequence length — anything beyond is silently truncated). `tiktoken` is reserved for Claude-side prompt-budget accounting, never for chunk sizing.
- Each chunk stores metadata: `file_path`, `language`, `start_line`, `end_line`, `chunk_type`

---

## Retrieval Strategy

```
1. Embed user query with same model used for ingestion
2. Retrieve top-20 candidates from ChromaDB (cosine similarity)
3. Rerank with cross-encoder → keep top-5
4. Build prompt with chunks + metadata
5. Claude returns answer with file:line citations
```

Similarity threshold: disabled in v1 (`0.0`); see [ADR-0006](docs/decisions/0006-disable-similarity-threshold-v1.md) for the calibration plan.

---

## Claude Synthesis Prompt Contract

Claude is always called with:
- **System prompt**: instructs citation of file paths and line ranges,
  instructs refusal to answer if context is insufficient
- **User message**: retrieved chunks with metadata + original question
- **Model**: `claude-opus-4-7` for quality, configurable via env
- **Max tokens**: 2048 for answers (code answers with multiple citations need the room — 1024 clipped real responses)
- Claude must never answer from its own training data — only from provided context

---

## Environment Variables

```bash
# Required
REPOSAGE_GITHUB_TOKEN=
REPOSAGE_ANTHROPIC_API_KEY=

# ChromaDB
REPOSAGE_CHROMA_HOST=localhost
REPOSAGE_CHROMA_PORT=8000
REPOSAGE_CHROMA_PERSIST_DIR=./data/chroma

# Embedding
REPOSAGE_EMBEDDING_MODEL=nomic-ai/nomic-embed-text-v1.5
REPOSAGE_EMBEDDING_DEVICE=cpu   # or cuda

# Retrieval
REPOSAGE_RETRIEVAL_TOP_K=20
REPOSAGE_RERANK_TOP_N=5
REPOSAGE_SIMILARITY_THRESHOLD=0.0  # disabled in v1; calibrate per-model with eval data

# Claude
REPOSAGE_CLAUDE_MODEL=claude-opus-4-7
REPOSAGE_CLAUDE_MAX_TOKENS=2048

# App
REPOSAGE_LOG_LEVEL=INFO
REPOSAGE_MAX_REPO_SIZE_MB=500
```

---

## Key Design Decisions

Summarised here; full reasoning lives in [`docs/decisions/`](docs/decisions/).

**Why nomic-embed-text over all-MiniLM?**
MiniLM was trained on prose. nomic-embed-text-v1.5 was trained on code paired with
natural language, so an English query and a relevant code chunk land in the same
neighbourhood of the embedding space.

**Why tree-sitter over fixed-size chunking?**
Fixed chunks split functions mid-body, blurring the embedding across two unrelated
contexts. Tree-sitter respects AST boundaries — each chunk is a complete logical
unit (class, function, method), so embeddings stay semantically coherent.

**Why rerank after vector search?**
Vector search optimises for broad recall. Cross-encoders compare query and chunk
together and optimise for precision. The two-stage approach gets both.

**Why one ChromaDB collection per repo?**
Isolation — re-ingestion, deletion, and versioning are clean operations. No risk of
chunks from repo A surfacing in queries against repo B.
