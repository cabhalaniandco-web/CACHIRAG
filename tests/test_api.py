from fastapi.testclient import TestClient

from app.main import app, pipeline

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["corpus_size"] >= 1


def test_query_cache_miss_then_hit():
    pipeline.cache.clear()
    pipeline.cache.reset_stats()

    first = client.post("/query", json={"query": "What is cache-augmented RAG?"})
    assert first.status_code == 200
    assert first.json()["cached"] is False

    second = client.post("/query", json={"query": "what is    Cache-Augmented rag?"})
    assert second.status_code == 200
    assert second.json()["cached"] is True

    stats = client.get("/cache/stats").json()
    assert stats["hits"] == 1
    assert stats["misses"] == 1


def test_add_document_and_retrieve():
    resp = client.post(
        "/documents",
        json={"documents": [{"id": "otters", "text": "otters float on water and hold hands"}]},
    )
    assert resp.status_code == 200
    assert resp.json()["added"] == 1

    answer = client.post("/query", json={"query": "do otters hold hands"}).json()
    passage_ids = [p["id"] for p in answer["passages"]]
    assert "otters" in passage_ids


def test_query_validation_rejects_empty():
    resp = client.post("/query", json={"query": ""})
    assert resp.status_code == 422
