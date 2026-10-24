import json
from pathlib import Path

from src.retrieval.adapter import LocalQdrantAdapter, chunk_documents, load_knowledge
from src.tools.contracts import RetrievalRequest
from src.tools.retrieval import retrieve_request


ROOT = Path(__file__).resolve().parents[1]


def test_corpus_has_varied_sources_and_local_qdrant_returns_resolvable_metadata():
    docs = load_knowledge(ROOT / "knowledge")
    assert len(docs) >= 5
    assert {doc.source_type for doc in docs} >= {"plan", "architecture", "timeline", "engineering", "decision"}
    adapter = LocalQdrantAdapter(docs, similarity_threshold=0.0)
    try:
        chunks = adapter.retrieve("approval audit retention source requirement", top_k=3)
        assert chunks
        assert len(chunks) <= 3
        assert all(chunk.source_id and chunk.chunk_id and chunk.source_locator for chunk in chunks)
        assert adapter.metadata["store"] == "qdrant-local"
        assert adapter.metadata["dimensions"] == 96
    finally:
        adapter.close()


def test_chunker_keeps_source_type_and_source_locator():
    from src.retrieval.adapter import KnowledgeDocument

    result = chunk_documents(
        [KnowledgeDocument("SRC-1", "standard", "standards.md#security", "# Security\n\nUse least privilege.")]
    )
    assert result[0]["source_type"] == "standard"
    assert result[0]["source_locator"].startswith("standards.md#security#chunk-")
    assert result[0]["chunk_id"].startswith("SRC-1-chunk-")


def test_empty_retrieval_is_explicit_and_typed():
    adapter = LocalQdrantAdapter([], similarity_threshold=0)
    try:
        response = retrieve_request(adapter, RetrievalRequest(query="anything"))
        assert response.chunks == []
        assert response.error is None
    finally:
        adapter.close()


def test_index_rejects_query_embedding_model_mismatch():
    adapter = LocalQdrantAdapter(load_knowledge(ROOT / "knowledge"))
    try:
        try:
            adapter.retrieve("approval", embedding_model="another-model")
        except ValueError as exc:
            assert "Embedding model mismatch" in str(exc)
        else:
            raise AssertionError("Expected explicit embedding model mismatch")
    finally:
        adapter.close()


def test_fixed_retrieval_regression_queries_meet_the_versioned_threshold():
    benchmark = json.loads((ROOT / "data" / "evaluation" / "retrieval-regression.json").read_text(encoding="utf-8"))
    adapter = LocalQdrantAdapter(load_knowledge(ROOT / "knowledge"), top_k=benchmark["top_k"])
    try:
        recalls = []
        for case in benchmark["cases"]:
            results = adapter.retrieve(case["query"])
            actual = {item.chunk_id for item in results}
            expected = set(case["expected_chunk_ids"])
            recalls.append(len(expected & actual) / len(expected) if expected else float(not results))
        assert min(recalls) >= benchmark["threshold"]
    finally:
        adapter.close()
