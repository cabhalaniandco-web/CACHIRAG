"""A small, dependency-free TF-IDF retriever.

This keeps CACHIRAG fully offline and deterministic: there are no external model
or API calls, so it runs anywhere without secrets. It is intentionally simple —
enough to demonstrate a real retrieval step in a RAG pipeline.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase and split text into alphanumeric tokens."""
    return _TOKEN_RE.findall(text.lower())


@dataclass
class Document:
    """A single indexed document."""

    id: str
    text: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class ScoredDocument:
    """A document paired with its relevance score for a query."""

    document: Document
    score: float


class TfidfRetriever:
    """In-memory TF-IDF retriever with cosine similarity ranking."""

    def __init__(self) -> None:
        self._documents: dict[str, Document] = {}
        self._term_frequencies: dict[str, dict[str, int]] = {}
        self._document_frequency: dict[str, int] = {}

    def __len__(self) -> int:
        return len(self._documents)

    @property
    def documents(self) -> list[Document]:
        return list(self._documents.values())

    def add(self, document: Document) -> None:
        """Add or replace a document, updating the corpus statistics."""
        if document.id in self._documents:
            self._remove_stats(document.id)

        self._documents[document.id] = document
        counts: dict[str, int] = {}
        for token in tokenize(document.text):
            counts[token] = counts.get(token, 0) + 1
        self._term_frequencies[document.id] = counts
        for term in counts:
            self._document_frequency[term] = self._document_frequency.get(term, 0) + 1

    def add_many(self, documents: list[Document]) -> None:
        for document in documents:
            self.add(document)

    def _remove_stats(self, doc_id: str) -> None:
        for term in self._term_frequencies.get(doc_id, {}):
            remaining = self._document_frequency.get(term, 0) - 1
            if remaining <= 0:
                self._document_frequency.pop(term, None)
            else:
                self._document_frequency[term] = remaining
        self._term_frequencies.pop(doc_id, None)
        self._documents.pop(doc_id, None)

    def _idf(self, term: str) -> float:
        total_docs = len(self._documents)
        df = self._document_frequency.get(term, 0)
        # Smoothed inverse document frequency.
        return math.log((1 + total_docs) / (1 + df)) + 1.0

    def _vector(self, counts: dict[str, int]) -> dict[str, float]:
        return {term: freq * self._idf(term) for term, freq in counts.items()}

    def search(self, query: str, top_k: int = 3) -> list[ScoredDocument]:
        """Return the ``top_k`` documents most relevant to ``query``."""
        if not self._documents:
            return []

        query_counts: dict[str, int] = {}
        for token in tokenize(query):
            query_counts[token] = query_counts.get(token, 0) + 1
        query_vec = self._vector(query_counts)
        query_norm = math.sqrt(sum(w * w for w in query_vec.values()))
        if query_norm == 0:
            return []

        results: list[ScoredDocument] = []
        for doc_id, counts in self._term_frequencies.items():
            doc_vec = self._vector(counts)
            doc_norm = math.sqrt(sum(w * w for w in doc_vec.values()))
            if doc_norm == 0:
                continue
            dot = sum(weight * doc_vec.get(term, 0.0) for term, weight in query_vec.items())
            score = dot / (query_norm * doc_norm)
            if score > 0:
                results.append(ScoredDocument(self._documents[doc_id], round(score, 6)))

        results.sort(key=lambda item: item.score, reverse=True)
        return results[:top_k]
