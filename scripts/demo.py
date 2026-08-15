"""End-to-end demo that exercises the running CACHIRAG API.

Usage:
    python scripts/demo.py [base_url]

Defaults to http://127.0.0.1:8000. Requires the server to be running.
"""

from __future__ import annotations

import sys

import httpx


def main(base_url: str = "http://127.0.0.1:8000") -> int:
    with httpx.Client(base_url=base_url, timeout=10.0) as client:
        health = client.get("/health").json()
        print(f"health: {health}")

        client.delete("/cache")

        print("\n-- First ask (expect CACHE MISS) --")
        q = {"query": "What is cache-augmented RAG?"}
        first = client.post("/query", json=q).json()
        print(f"cached={first['cached']} elapsed_ms={first['elapsed_ms']}")
        print(f"answer: {first['answer'][:120]}...")
        print("top passages:", [p["id"] for p in first["passages"]])

        print("\n-- Second ask, same query (expect CACHE HIT) --")
        second = client.post("/query", json=q).json()
        print(f"cached={second['cached']} elapsed_ms={second['elapsed_ms']}")

        print("\n-- Add a new document (invalidates cache) --")
        add = client.post(
            "/documents",
            json={"documents": [{"id": "otters", "text": "otters float and hold hands"}]},
        ).json()
        print(f"corpus_size={add['corpus_size']}")

        print("\n-- Ask about the new document --")
        third = client.post("/query", json={"query": "do otters hold hands"}).json()
        print("top passages:", [p["id"] for p in third["passages"]])

        stats = client.get("/cache/stats").json()
        print(f"\ncache stats: {stats}")

        ok = first["cached"] is False and second["cached"] is True and "otters" in [
            p["id"] for p in third["passages"]
        ]
        print("\nDEMO RESULT:", "PASS" if ok else "FAIL")
        return 0 if ok else 1


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    raise SystemExit(main(url))
