"""
NEU Unofficial Guide — RAG Pipeline
Milestones 3 + 4: Document Ingestion → Chunking → Embedding + Vector Store → Retrieval

Architecture (from planning.md):
  Document Ingestion  : Python file reading — .txt files from documents/
  Chunking            : LangChain RecursiveCharacterTextSplitter, 300 tokens / 50 overlap
  Embedding + Store   : all-MiniLM-L6-v2 (sentence-transformers) → ChromaDB
  Retrieval           : ChromaDB similarity search, top-k = 5

Chunking strategy (from planning.md):
  - Chunk size : 300 tokens
  - Overlap    : 50 tokens
  - Splitter   : LangChain RecursiveCharacterTextSplitter with tiktoken length function
  - Reasoning  : The corpus is review-heavy (RMP, RateMyCourses, Reddit, Grad Café).
                 Short, self-contained opinions fit naturally within 300 tokens without
                 mixing reviews across chunk boundaries. The 50-token overlap ensures
                 facts that straddle a boundary (e.g. a professor's name in one sentence
                 and their grading policy in the next) remain searchable.

Retrieval approach (from planning.md):
  - Embedding model : all-MiniLM-L6-v2 — fast, local, no per-query cost.
                      Note: 256-token context window; chunks near the 300-token ceiling
                      are silently truncated before embedding (acceptable for this project).
  - Top-k           : 5 — balances recall against flooding the generation prompt with
                      redundant reviews about the same professor.
"""

import os
from pathlib import Path
from typing import List, Dict

from langchain_text_splitters import RecursiveCharacterTextSplitter
import tiktoken
from sentence_transformers import SentenceTransformer
import chromadb

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DOCS_DIR     = Path(__file__).parent / "documents"
CHROMA_DIR   = Path(__file__).parent / "chroma_db"   # persisted vector store on disk
COLLECTION   = "neu_unofficial_guide"

CHUNK_SIZE    = 300   # tokens
CHUNK_OVERLAP = 50    # tokens
ENCODING      = "cl100k_base"  # same tokenizer used by most modern LLMs

EMBED_MODEL   = "all-MiniLM-L6-v2"   # sentence-transformers model
TOP_K         = 5                     # chunks returned per query


# ---------------------------------------------------------------------------
# Token-aware length function
# ---------------------------------------------------------------------------
def _token_len(text: str) -> int:
    """Return the number of tokens in *text* using the cl100k_base tokeniser."""
    enc = tiktoken.get_encoding(ENCODING)
    return len(enc.encode(text))


# ---------------------------------------------------------------------------
# Stage 1 — Document Ingestion
# ---------------------------------------------------------------------------
def load_documents(docs_dir: Path = DOCS_DIR) -> List[Dict[str, str]]:
    """
    Read every .txt file in *docs_dir* and return a list of document dicts.

    Each dict has:
        "source"   : filename (e.g. "ratemyprofessors_neu_cs.txt")
        "text"     : full raw text content of the file
    """
    documents = []
    txt_files = sorted(docs_dir.glob("*.txt"))

    if not txt_files:
        print(f"[WARNING] No .txt files found in {docs_dir}")
        return documents

    for filepath in txt_files:
        text = filepath.read_text(encoding="utf-8").strip()
        if not text:
            print(f"[WARNING] Skipping empty file: {filepath.name}")
            continue
        documents.append({
            "source": filepath.name,
            "text": text,
        })
        print(f"[LOADED]  {filepath.name}  ({_token_len(text):,} tokens)")

    print(f"\n[INFO] Loaded {len(documents)} document(s) from {docs_dir}\n")
    return documents


# ---------------------------------------------------------------------------
# Stage 2 — Chunking
# ---------------------------------------------------------------------------
def chunk_text(documents: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Split each document into overlapping token-sized chunks.

    Uses LangChain's RecursiveCharacterTextSplitter with a tiktoken-based
    length function so chunk_size and chunk_overlap are measured in tokens,
    not characters.

    Returns a flat list of chunk dicts, each containing:
        "chunk_id"  : unique id, e.g. "ratemyprofessors_neu_cs.txt_chunk_0"
        "source"    : originating filename
        "text"      : chunk text
        "token_count": actual token count of this chunk
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=_token_len,
        # Try to split on natural boundaries first: paragraphs → sentences → words
        separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""],
    )

    all_chunks = []

    for doc in documents:
        raw_chunks = splitter.split_text(doc["text"])

        for i, chunk_text_content in enumerate(raw_chunks):
            token_count = _token_len(chunk_text_content)
            all_chunks.append({
                "chunk_id": f"{doc['source']}_chunk_{i}",
                "source": doc["source"],
                "text": chunk_text_content,
                "token_count": token_count,
            })

        print(
            f"[CHUNKED] {doc['source']}  →  {len(raw_chunks)} chunk(s)"
        )

    print(f"\n[INFO] Total chunks produced: {len(all_chunks)}\n")
    return all_chunks


# ---------------------------------------------------------------------------
# Stage 3 — Embedding + Vector Store
# ---------------------------------------------------------------------------
def embed_and_store(chunks: List[Dict[str, str]], reset: bool = False) -> chromadb.Collection:
    """
    Embed each chunk with all-MiniLM-L6-v2 and upsert into a ChromaDB collection.

    Args:
        chunks : output of chunk_text()
        reset  : if True, drop and recreate the collection (full re-index)

    Returns:
        The ChromaDB collection, ready for querying.

    Metadata stored per chunk:
        source      : originating filename  (e.g. "ratemyprofessors_neu_cs.txt")
        chunk_id    : unique chunk identifier
        token_count : number of tokens in the chunk
    """
    # Load embedding model (downloads once, cached locally by sentence-transformers)
    print(f"[EMBED]   Loading model: {EMBED_MODEL}")
    model = SentenceTransformer(EMBED_MODEL)

    # Persistent ChromaDB client — vectors survive between runs
    CHROMA_DIR.mkdir(exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    if reset and COLLECTION in [c.name for c in client.list_collections()]:
        client.delete_collection(COLLECTION)
        print(f"[CHROMA]  Dropped existing collection '{COLLECTION}'")

    collection = client.get_or_create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"},  # cosine similarity for semantic search
    )

    # Skip chunks already in the store (idempotent upsert by chunk_id)
    existing_ids = set(collection.get(include=[])["ids"])
    new_chunks   = [c for c in chunks if c["chunk_id"] not in existing_ids]

    if not new_chunks:
        print(f"[CHROMA]  All {len(chunks)} chunks already indexed — nothing to add.\n")
        return collection

    print(f"[EMBED]   Embedding {len(new_chunks)} chunk(s) …")
    texts      = [c["text"]        for c in new_chunks]
    ids        = [c["chunk_id"]    for c in new_chunks]
    metadatas  = [
        {"source": c["source"], "chunk_id": c["chunk_id"], "token_count": c["token_count"]}
        for c in new_chunks
    ]

    # Embed in one batch — all-MiniLM-L6-v2 is fast enough for 36 chunks
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_list=True)

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    print(f"[CHROMA]  Stored {len(new_chunks)} chunk(s) in collection '{COLLECTION}'")
    print(f"[CHROMA]  Total vectors in store: {collection.count()}\n")
    return collection


# ---------------------------------------------------------------------------
# Stage 4 — Retrieval
# ---------------------------------------------------------------------------
def retrieve(query: str, collection: chromadb.Collection, top_k: int = TOP_K) -> List[Dict]:
    """
    Embed *query* with all-MiniLM-L6-v2 and return the top-k most similar chunks.

    Args:
        query      : the user's natural-language question
        collection : ChromaDB collection returned by embed_and_store()
        top_k      : number of chunks to return (default 5, from planning.md)

    Returns:
        List of result dicts, each containing:
            "rank"        : 1-based rank
            "score"       : cosine similarity (higher = more relevant)
            "source"      : originating filename
            "chunk_id"    : unique chunk identifier
            "text"        : chunk text
    """
    model = SentenceTransformer(EMBED_MODEL)
    query_embedding = model.encode(query, convert_to_list=True)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    retrieved = []
    for rank, (doc, meta, dist) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ), start=1):
        # ChromaDB returns cosine *distance* (0 = identical, 2 = opposite)
        # Convert to similarity score in [0, 1]
        similarity = 1 - (dist / 2)
        retrieved.append({
            "rank":        rank,
            "score":       round(similarity, 4),
            "source":      meta["source"],
            "chunk_id":    meta["chunk_id"],
            "text":        doc,
        })

    return retrieved


# ---------------------------------------------------------------------------
# Quick sanity check — run directly to verify chunking on your documents
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # --- Stages 1 & 2: ingest + chunk ---
    docs   = load_documents()
    chunks = chunk_text(docs)

    # --- Stage 3: embed + store ---
    collection = embed_and_store(chunks)

    # --- Stage 4: retrieve — run all 5 eval questions from planning.md ---
    eval_questions = [
        "What do students say about the workload in CS 3500 (Object-Oriented Design)?",
        "Which CS professor is mentioned as giving strong or useful exam reviews?",
        "Do students recommend Northeastern's CS program for co-op and job outcomes?",
        "How difficult is it to get good grades in NEU's CS master's courses?",
        "What is Professor Karl Lieberherr's reputation among CS students?",
    ]

    print("=" * 60)
    print("RETRIEVAL TEST — Evaluation Questions (top-5 chunks each)")
    print("=" * 60)
    for q in eval_questions:
        print(f"\nQ: {q}")
        print("-" * 50)
        hits = retrieve(q, collection)
        for hit in hits:
            print(f"  [{hit['rank']}] score={hit['score']}  source={hit['source']}")
            print(f"      {hit['text'][:120].strip()} …")
        print()
