# Retrieval design

## Corpus and metadata

`knowledge/` contains seven synthetic sources: historical BRDs, plan templates, architecture patterns, timeline examples, engineering standards, decision records, and synthetic organizational history. Each chunk keeps a stable source ID, chunk ID, source type, locator, and text. IDs derive from the source and a content digest. The source collection is deliberately synthetic.

## Chunking and index

The chunker splits at Markdown headings and paragraph boundaries, limits chunks to 850 characters, and splits oversized paragraphs. It preserves source locators and source-type metadata. The local Qdrant adapter uses a 96-dimensional deterministic signed feature hash with cosine distance. It defaults to `top_k=4` and a cosine threshold of `0.12`; `local-hash-v1` is not interchangeable with model-generated embeddings. The ephemeral in-memory Qdrant index avoids cloud services or persistent user-data storage.

## Query and evidence behavior

The retrieval query combines the BRD title and normalized requirement text. Retrieved IDs are passed into each agent contract and cited claim, and the coordinator verifies they resolve against this run's evidence. No evidence (or adapter failure) is explicit: the run continues with a disclaimer; no artifact can be Green. The deterministic rubric checks citation coverage and all section coverage.

## Regression and migration

`data/evaluation/retrieval-regression.json` pins fixed queries, expected chunk IDs, the recall@k metric, and a threshold of 1.0, including a deliberately poor match. `tests/test_retrieval.py` runs that suite and verifies source diversity, top-k behavior, empty retrieval, and embedding-model mismatch rejection. Before changing stores or embeddings, rebuild from source documents and pass the versioned regression suite before cutover. No ChromaDB/Azure migration is part of this prototype.
