"""FastAPI application exposing the CACHIRAG pipeline."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import __version__
from app.data import SEED_DOCUMENTS
from app.rag import CachiRagPipeline
from app.retriever import Document

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="CACHIRAG",
    version=__version__,
    description="A cache-augmented Retrieval-Augmented Generation service.",
)

pipeline = CachiRagPipeline()
pipeline.add_documents(list(SEED_DOCUMENTS))


class DocumentIn(BaseModel):
    id: str = Field(..., min_length=1, description="Unique document identifier.")
    text: str = Field(..., min_length=1, description="Document body to index.")
    metadata: dict[str, str] = Field(default_factory=dict)


class AddDocumentsRequest(BaseModel):
    documents: list[DocumentIn] = Field(..., min_length=1)


class AddDocumentsResponse(BaseModel):
    added: int
    corpus_size: int


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "corpus_size": len(pipeline.retriever),
    }


@app.post("/documents", response_model=AddDocumentsResponse)
def add_documents(request: AddDocumentsRequest) -> AddDocumentsResponse:
    documents = [
        Document(id=doc.id, text=doc.text, metadata=doc.metadata)
        for doc in request.documents
    ]
    corpus_size = pipeline.add_documents(documents)
    return AddDocumentsResponse(added=len(documents), corpus_size=corpus_size)


@app.get("/documents")
def list_documents() -> dict:
    return {
        "corpus_size": len(pipeline.retriever),
        "documents": [
            {"id": doc.id, "metadata": doc.metadata} for doc in pipeline.retriever.documents
        ],
    }


@app.post("/query")
def query(request: QueryRequest) -> dict:
    if len(pipeline.retriever) == 0:
        raise HTTPException(status_code=409, detail="No documents indexed yet.")
    answer = pipeline.query(request.query, top_k=request.top_k)
    return answer.to_dict()


@app.get("/cache/stats")
def cache_stats() -> dict:
    stats = pipeline.cache.stats()
    return {
        "hits": stats.hits,
        "misses": stats.misses,
        "size": stats.size,
        "capacity": stats.capacity,
        "hit_rate": stats.hit_rate,
    }


@app.delete("/cache")
def clear_cache() -> dict:
    pipeline.cache.clear()
    pipeline.cache.reset_stats()
    return {"status": "cleared"}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
