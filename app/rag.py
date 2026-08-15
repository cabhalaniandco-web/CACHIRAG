"""The CACHIRAG pipeline: retrieve, assemble an answer, and cache the result."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field

from app.cache import LRUCache
from app.retriever import Document, TfidfRetriever


@dataclass
class Passage:
    """A retrieved passage returned alongside an answer."""

    id: str
    text: str
    score: float
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class Answer:
    """The result of a query."""

    query: str
    answer: str
    passages: list[Passage]
    cached: bool
    elapsed_ms: float

    def to_dict(self) -> dict:
        data = asdict(self)
        return data


def _normalize_query(query: str) -> str:
    return " ".join(query.lower().split())


def _compose_answer(query: str, passages: list[Passage]) -> str:
    """Assemble an extractive answer from the retrieved passages.

    This deliberately avoids any external LLM so the demo is deterministic and
    offline. Swapping this function for a real generator is the natural next step.
    """
    if not passages:
        return (
            f"I could not find anything relevant to '{query}'. "
            "Try adding more documents first."
        )
    top = passages[0]
    supporting = " ".join(p.text for p in passages)
    return (
        f"Based on {len(passages)} retrieved passage(s), the most relevant source "
        f"is '{top.id}'. {supporting}"
    )


class CachiRagPipeline:
    """Ties the retriever and cache together behind a single ``query`` call."""

    def __init__(self, cache_capacity: int = 128, top_k: int = 3) -> None:
        self.retriever = TfidfRetriever()
        self.cache: LRUCache[str, Answer] = LRUCache(capacity=cache_capacity)
        self.top_k = top_k

    def add_documents(self, documents: list[Document]) -> int:
        self.retriever.add_many(documents)
        # New documents can change results, so previously cached answers are stale.
        self.cache.clear()
        return len(self.retriever)

    def query(self, query: str, top_k: int | None = None) -> Answer:
        started = time.perf_counter()
        key = _normalize_query(query)

        cached = self.cache.get(key)
        if cached is not None:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
            return Answer(
                query=query,
                answer=cached.answer,
                passages=cached.passages,
                cached=True,
                elapsed_ms=elapsed_ms,
            )

        k = top_k or self.top_k
        scored = self.retriever.search(query, top_k=k)
        passages = [
            Passage(
                id=item.document.id,
                text=item.document.text,
                score=item.score,
                metadata=item.document.metadata,
            )
            for item in scored
        ]
        answer_text = _compose_answer(query, passages)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
        answer = Answer(
            query=query,
            answer=answer_text,
            passages=passages,
            cached=False,
            elapsed_ms=elapsed_ms,
        )
        self.cache.set(key, answer)
        return answer
