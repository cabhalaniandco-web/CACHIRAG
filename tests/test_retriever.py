from app.retriever import Document, TfidfRetriever, tokenize


def test_tokenize_lowercases_and_splits():
    assert tokenize("Hello, RAG-World! 123") == ["hello", "rag", "world", "123"]


def test_search_ranks_relevant_document_first():
    retriever = TfidfRetriever()
    retriever.add_many(
        [
            Document(id="a", text="caching stores results for fast reuse"),
            Document(id="b", text="retrieval finds relevant documents for a query"),
            Document(id="c", text="bananas are a yellow fruit"),
        ]
    )
    results = retriever.search("how does caching store results", top_k=2)
    assert results
    assert results[0].document.id == "a"
    assert results[0].score > 0


def test_search_empty_corpus_returns_nothing():
    assert TfidfRetriever().search("anything") == []


def test_add_replaces_existing_document():
    retriever = TfidfRetriever()
    retriever.add(Document(id="a", text="original text about kangaroos"))
    retriever.add(Document(id="a", text="updated text about caching and retrieval"))
    assert len(retriever) == 1
    results = retriever.search("caching retrieval")
    assert results[0].document.id == "a"
    assert "caching" in results[0].document.text
