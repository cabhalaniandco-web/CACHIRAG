# CACHIRAG

**Cache-augmented Retrieval-Augmented Generation** — a small, fully-offline RAG
service that caches answers so repeated questions are served instantly.

There are no external model or API calls: retrieval uses a dependency-free TF-IDF
index, and answers are assembled extractively from the retrieved passages. This
keeps the service deterministic and runnable anywhere without secrets. Swapping the
answer composer in `app/rag.py` for a real LLM is the natural next step.

## Architecture

| Component | File | Responsibility |
| --- | --- | --- |
| Retriever | `app/retriever.py` | In-memory TF-IDF index with cosine-similarity ranking |
| Cache | `app/cache.py` | Thread-safe LRU cache with hit/miss statistics |
| Pipeline | `app/rag.py` | Retrieve → assemble answer → cache the result |
| API | `app/main.py` | FastAPI endpoints + a small web UI |
| Seed data | `app/data.py` | Documents indexed on startup |

## Quick start

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then open http://localhost:8000 for the web UI, or hit the API directly:

```bash
# Ask a question (first call is a CACHE MISS, second is a CACHE HIT)
curl -s localhost:8000/query -H 'content-type: application/json' \
  -d '{"query":"What is cache-augmented RAG?"}'

# Add a document
curl -s localhost:8000/documents -H 'content-type: application/json' \
  -d '{"documents":[{"id":"otters","text":"otters float and hold hands"}]}'

# Cache statistics
curl -s localhost:8000/cache/stats
```

## API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Service status and corpus size |
| `GET` | `/` | Web UI |
| `POST` | `/documents` | Add/replace documents (clears the cache) |
| `GET` | `/documents` | List indexed documents |
| `POST` | `/query` | Ask a question; returns answer, passages, cache flag, latency |
| `GET` | `/cache/stats` | Cache hits, misses, hit rate, size |
| `DELETE` | `/cache` | Clear the cache and reset stats |

## Development

```bash
ruff check .          # lint
pytest                # run the test suite
python scripts/demo.py  # end-to-end demo against a running server
```

## Cloud Agent environment

`.cursor/environment.json` provisions the Cloud Agent environment:

- **install** creates a virtualenv and installs pinned dependencies from `requirements.txt`.
- **terminals** runs the API server (`uvicorn`) on port `8000`.
