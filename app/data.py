"""Seed documents so the service is useful the moment it boots."""

from __future__ import annotations

from app.retriever import Document

SEED_DOCUMENTS: list[Document] = [
    Document(
        id="rag-overview",
        text=(
            "Retrieval-Augmented Generation (RAG) combines a retriever that finds "
            "relevant documents with a generator that produces an answer grounded "
            "in the retrieved context. It reduces hallucination by giving the model "
            "source passages to rely on."
        ),
        metadata={"topic": "rag"},
    ),
    Document(
        id="caching",
        text=(
            "Caching stores the result of an expensive computation so repeated "
            "requests can be served quickly. A least-recently-used cache evicts the "
            "entries that have not been accessed for the longest time when it is full."
        ),
        metadata={"topic": "caching"},
    ),
    Document(
        id="cachirag",
        text=(
            "CACHIRAG is a cache-augmented RAG service. It caches answers keyed by "
            "the normalized query so that repeated questions skip retrieval and are "
            "returned instantly, while new questions run the full retrieval pipeline."
        ),
        metadata={"topic": "cachirag"},
    ),
    Document(
        id="tfidf",
        text=(
            "TF-IDF weighs a term by how often it appears in a document and how rare "
            "it is across the corpus. Cosine similarity between TF-IDF vectors ranks "
            "documents by relevance to a query."
        ),
        metadata={"topic": "retrieval"},
    ),
    Document(
        id="embeddings",
        text=(
            "Vector embeddings map text into a dense numeric space where similar "
            "meanings are close together. Approximate nearest-neighbor search over "
            "embeddings powers semantic retrieval in production RAG systems."
        ),
        metadata={"topic": "retrieval"},
    ),
]
