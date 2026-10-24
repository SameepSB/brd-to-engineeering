from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from qdrant_client import QdrantClient, models

VECTOR_SIZE = 96
CORPUS_VERSION = "synthetic-2026-01"
EMBEDDING_MODEL = "local-hash-v1"


@dataclass(frozen=True)
class RetrievedChunk:
    source_id: str
    chunk_id: str
    source_locator: str
    text: str
    score: float


@dataclass(frozen=True)
class KnowledgeDocument:
    source_id: str
    source_type: str
    source_locator: str
    text: str


def chunk_documents(documents: Iterable[KnowledgeDocument], max_chars: int = 850) -> list[dict[str, str]]:
    """Split at headings/paragraph boundaries; retain type and source locator metadata."""
    if max_chars < 100:
        raise ValueError("max_chars must be at least 100")
    chunks: list[dict[str, str]] = []
    for document in documents:
        document_chunks: list[dict[str, str]] = []
        pieces = re.split(r"(?m)(?=^#{1,6}\s)", document.text)
        buffered = ""
        for piece in pieces:
            text = piece.strip()
            if not text:
                continue
            paragraphs = re.split(r"\n\s*\n", text)
            for paragraph in paragraphs:
                paragraph = paragraph.strip()
                if not paragraph:
                    continue
                if buffered and len(buffered) + len(paragraph) + 2 > max_chars:
                    document_chunks.append(_chunk_record(document, buffered, len(document_chunks)))
                    buffered = ""
                if len(paragraph) > max_chars:
                    if buffered:
                        document_chunks.append(_chunk_record(document, buffered, len(document_chunks)))
                        buffered = ""
                    for start in range(0, len(paragraph), max_chars):
                        document_chunks.append(
                            _chunk_record(document, paragraph[start : start + max_chars], len(document_chunks))
                        )
                else:
                    buffered = f"{buffered}\n\n{paragraph}".strip()
        if buffered:
            document_chunks.append(_chunk_record(document, buffered, len(document_chunks)))
        chunks.extend(document_chunks)
    return chunks


def _chunk_record(document: KnowledgeDocument, text: str, ordinal: int) -> dict[str, str]:
    digest = hashlib.sha1(f"{document.source_id}:{ordinal}:{text}".encode("utf-8")).hexdigest()[:12]
    return {
        "source_id": document.source_id,
        "chunk_id": f"{document.source_id}-chunk-{digest}",
        "source_type": document.source_type,
        "source_locator": f"{document.source_locator}#chunk-{digest}",
        "text": text,
    }


def embed_text(text: str) -> list[float]:
    """Deterministic, credential-free feature hashing for a small synthetic corpus."""
    vector = [0.0] * VECTOR_SIZE
    words = re.findall(r"[a-z0-9]+", text.lower())
    for token in words:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % VECTOR_SIZE
        vector[index] += 1.0 if digest[4] % 2 else -1.0
    norm = math.sqrt(sum(component * component for component in vector))
    return [component / norm for component in vector] if norm else vector


class LocalQdrantAdapter:
    """Qdrant local/in-memory index behind an embedding-neutral retrieval interface."""

    def __init__(
        self,
        documents: Iterable[KnowledgeDocument] | None = None,
        *,
        top_k: int = 4,
        similarity_threshold: float = 0.12,
        client: QdrantClient | None = None,
    ) -> None:
        if top_k < 1:
            raise ValueError("top_k must be positive")
        if not 0 <= similarity_threshold <= 1:
            raise ValueError("similarity_threshold must be between 0 and 1")
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        self.collection_name = "synthetic_knowledge"
        self.metadata = {
            "store": "qdrant-local",
            "collection": self.collection_name,
            "embedding_provider": "local",
            "embedding_model": EMBEDDING_MODEL,
            "dimensions": VECTOR_SIZE,
            "corpus_version": CORPUS_VERSION,
        }
        self._client = client or QdrantClient(":memory:")
        self._client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE),
        )
        records = chunk_documents(documents or [])
        if records:
            self._client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=index + 1,
                        vector=embed_text(record["text"]),
                        payload=record,
                    )
                    for index, record in enumerate(records)
                ],
            )

    def retrieve(
        self,
        query: str,
        *,
        top_k: int | None = None,
        embedding_model: str = EMBEDDING_MODEL,
    ) -> list[RetrievedChunk]:
        if embedding_model != self.metadata["embedding_model"]:
            raise ValueError(
                "Embedding model mismatch: query embeddings must use the model recorded by this index."
            )
        if top_k is not None and top_k < 1:
            raise ValueError("top_k must be positive")
        if not query.strip():
            return []
        result = self._client.query_points(
            collection_name=self.collection_name,
            query=embed_text(query),
            limit=top_k if top_k is not None else self.top_k,
            with_payload=True,
        )
        return [
            RetrievedChunk(
                source_id=str(point.payload["source_id"]),
                chunk_id=str(point.payload["chunk_id"]),
                source_locator=str(point.payload["source_locator"]),
                text=str(point.payload["text"]),
                score=float(point.score or 0),
            )
            for point in result.points
            if point.payload and float(point.score or 0) >= self.similarity_threshold
        ]

    def close(self) -> None:
        self._client.close()


def load_knowledge(directory: Path) -> list[KnowledgeDocument]:
    docs: list[KnowledgeDocument] = []
    for path in sorted(directory.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        kind = path.stem.split("-", 1)[0]
        docs.append(
            KnowledgeDocument(
                source_id=f"KNOW-{path.stem.upper()}",
                source_type=kind,
                source_locator=path.name,
                text=text,
            )
        )
    if len(docs) < 5:
        raise ValueError("The prototype knowledge corpus must contain at least five varied Markdown sources.")
    return docs
