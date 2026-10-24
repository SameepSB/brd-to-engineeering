from src.retrieval.adapter import LocalQdrantAdapter
from src.tools.contracts import RetrievalRequest, RetrievalResponse, RetrievedChunkOutput


def retrieve_request(adapter: LocalQdrantAdapter, request: RetrievalRequest) -> RetrievalResponse:
    try:
        chunks = adapter.retrieve(request.query, top_k=request.top_k)
    except (ValueError, RuntimeError) as exc:
        return RetrievalResponse(chunks=[], error=f"{type(exc).__name__}: retrieval failed")
    return RetrievalResponse(
        chunks=[
            RetrievedChunkOutput(
                source_id=item.source_id,
                chunk_id=item.chunk_id,
                source_locator=item.source_locator,
                text=item.text,
                score=min(1.0, max(0.0, item.score)),
            )
            for item in chunks
        ]
    )
