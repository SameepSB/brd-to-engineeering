# Synthetic technology decision records

## Local-first prototype
Choose a local deterministic provider and local Qdrant for reproducibility. Trade-off: hash embeddings are a transparent test baseline, not semantic embeddings or a production model catalog.

## Vector-store boundary
Use a retrieval adapter and persist store, collection, embedding provider/model, dimensions, and corpus version. Rebuild and pass a fixed regression suite before changing the embedding space or store.

## Evaluation and approval
Keep deterministic rubric checks separate from model-assisted judge notes. Bind approval to exact artifact revisions and preserve unresolved findings in any approved export.
