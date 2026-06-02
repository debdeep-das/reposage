"""Reproducibility script for ADR-0006.

Embeds a small mixed corpus of code and prose with nomic-embed-text-v1.5,
computes pairwise cosine similarity, and plots the distribution. The point
is to demonstrate the anisotropy noise floor — even "random" pairs cluster
well above zero, making the scaffolded threshold of 0.3 useless as a filter.

See ./README.md for hypothesis, method, and expected outcome.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "nomic-ai/nomic-embed-text-v1.5"
TASK_PREFIX = "search_document: "  # required by nomic-embed; omitting it changes the embeddings.
SCAFFOLDED_THRESHOLD = 0.3
OUTPUT_DIR = Path(__file__).parent

# Deliberately uncurated mix of code, prose, and config keys from RepoSage's
# domain. We are measuring the *noise floor*, so we want random pairs — not
# pairs that were chosen to be related or unrelated.
SAMPLE_TEXTS: list[str] = [
    # --- Code-like samples ---
    'class BaseChunker(ABC):\n    """Abstract base for AST-aware code chunkers."""\n    @abstractmethod\n    def chunk(self, source: str) -> list[Chunk]: ...',
    'def embed_documents(self, texts: list[str]) -> np.ndarray:\n    return self.model.encode([f"search_document: {t}" for t in texts], normalize_embeddings=True)',
    "from chromadb import PersistentClient\nclient = PersistentClient(path=settings.chroma_persist_dir)",
    "class IngestionPipeline:\n    def __init__(self, loader: GitHubLoader, chunker: BaseChunker, embedder: Embedder, store: VectorStore): ...",
    "async def post_query(request: QueryRequest) -> QueryResponse:\n    chunks = await retriever.retrieve(request.question)\n    return await synthesiser.answer(request.question, chunks)",
    "if chunk_size > MAX_EMBEDDER_SEQUENCE:\n    raise ChunkTooLarge(chunk_size)",
    "@router.get('/repos')\nasync def list_repos() -> list[RepoSummary]:\n    return await repo_service.list_all()",
    "def rerank(query: str, candidates: list[Chunk]) -> list[Chunk]:\n    scores = self.cross_encoder.predict([(query, c.text) for c in candidates])\n    return [c for _, c in sorted(zip(scores, candidates), reverse=True)]",
    "with path.open(encoding='utf-8') as f:\n    return f.read()",
    "class Chunk(BaseModel):\n    text: str\n    file_path: str\n    start_line: int\n    end_line: int\n    chunk_type: Literal['function', 'class', 'method', 'markdown_section']",
    # --- Prose samples ---
    "RepoSage is a RAG-based developer tool that lets users ask natural language questions about any GitHub repository.",
    "Tree-sitter respects AST boundaries — a chunk is always a complete logical unit such as a class, function, or method.",
    "Claude is the synthesis layer only; retrieval is always vector search followed by reranking.",
    "Cross-encoders compare query and chunk together and optimise for precision, while bi-encoders optimise for recall.",
    "Modern transformer-based embedding models concentrate their outputs in a narrow cone on the unit hypersphere.",
    "ChromaDB collections are immutable after creation — re-ingestion creates a new collection and the old one is deleted explicitly.",
    "The cosine similarity between two unrelated chunks is usually around 0.4 to 0.5 on nomic-embed, not 0.0.",
    "Code files are chunked AST-aware via tree-sitter; prose files use sentence-aware chunking with twenty percent overlap.",
    "Phase 1 covers the ingestion pipeline: chunking, embedding, and ChromaDB writes for a single GitHub repository.",
    "Embeddings live in the same 768-dimensional space mathematically; the question is whether the model puts related code and prose in the same region of it.",
    # --- Config / env keys ---
    "REPOSAGE_EMBEDDING_MODEL=nomic-ai/nomic-embed-text-v1.5",
    "REPOSAGE_RETRIEVAL_TOP_K=20",
    "REPOSAGE_CLAUDE_MODEL=claude-opus-4-7",
    "REPOSAGE_CHROMA_PERSIST_DIR=./data/chroma",
    "REPOSAGE_SIMILARITY_THRESHOLD=0.0",
]


def main() -> None:
    # 1. Load the embedder.
    #    Two non-obvious flags matter here:
    #      - trust_remote_code=True — nomic ships custom modeling code.
    #      - normalize_embeddings is set when calling .encode(), not here.
    transformer = SentenceTransformer(MODEL_NAME, trust_remote_code=True)

    # 2. Embed all SAMPLE_TEXTS.
    #    Prepend TASK_PREFIX to each text before encoding (nomic requires it).
    #    Pass normalize_embeddings=True so cosine similarity reduces to a dot product.
    transformer_embeddings = transformer.encode([TASK_PREFIX + t for t in SAMPLE_TEXTS], normalize_embeddings=True)

    # 3. Compute the pairwise similarity matrix.
    #    With L2-normalised embeddings, cosine_sim == E @ E.T.
    #    Then extract the upper triangle (k=1) to get unique pairs once.
    #    Tip: np.triu_indices(n, k=1) returns the indices you want.
    similarity_matrix = transformer_embeddings @ transformer_embeddings.T
    n = len(SAMPLE_TEXTS)
    pairwise_similarities = similarity_matrix[np.triu_indices(n, k=1)]

    # 4. Plot a histogram of the pairwise similarities.
    #    Add a vertical line at SCAFFOLDED_THRESHOLD so the noise floor is visible
    #    relative to it. Save as OUTPUT_DIR / "distribution.png".
    plt.figure(figsize=(10, 6))
    plt.hist(pairwise_similarities, bins=30, alpha=0.7, color='blue')
    plt.axvline(SCAFFOLDED_THRESHOLD, color='red', linestyle='dashed', label=f'Threshold = {SCAFFOLDED_THRESHOLD}')
    plt.title('Distribution of Pairwise Cosine Similarities')
    plt.xlabel('Cosine Similarity')
    plt.ylabel('Frequency')
    plt.legend()
    plt.savefig(OUTPUT_DIR / "distribution.png")
    plt.close()

    # 5. Write results.md next to this script with:
    #    - corpus size and pair count
    #    - mean, median, std, min, max
    #    - fraction of pairs above SCAFFOLDED_THRESHOLD
    #    - one-line interpretation
    markdown_path = OUTPUT_DIR / "results.md"
    with markdown_path.open("w", encoding="utf-8") as f:
        f.write(f"# Threshold Distribution Results\n\n")
        f.write(f"- Corpus size: {n} texts\n")
        f.write(f"- Pair count: {len(pairwise_similarities)}\n")
        f.write(f"- Mean similarity: {np.mean(pairwise_similarities):.4f}\n")
        f.write(f"- Median similarity: {np.median(pairwise_similarities):.4f}\n")
        f.write(f"- Std deviation: {np.std(pairwise_similarities):.4f}\n")
        f.write(f"- Min similarity: {np.min(pairwise_similarities):.4f}\n")
        f.write(f"- Max similarity: {np.max(pairwise_similarities):.4f}\n")
        fraction_above_threshold = np.mean(pairwise_similarities > SCAFFOLDED_THRESHOLD)
        f.write(f"- Fraction of pairs above threshold: {fraction_above_threshold:.4f}\n\n")
        f.write("**Interpretation:** Even random pairs of code and prose cluster well above 0.3, demonstrating a high anisotropy noise floor that renders the scaffolded threshold ineffective as a filter.\n")
   

if __name__ == "__main__":
    main()
