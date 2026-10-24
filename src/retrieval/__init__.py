"""Local retrieval adapter and chunking strategy."""

from src.retrieval.adapter import LocalQdrantAdapter, RetrievedChunk, chunk_documents

__all__ = ["LocalQdrantAdapter", "RetrievedChunk", "chunk_documents"]
