# Synthetic evaluation report

## Dataset and methods

The versioned evaluation inputs are listed in `data/evaluation/dataset.json` (dataset and rubric version 1.0), with `data/sample_brd.md` as the end-to-end demo. They cover scope complexity, missing NFRs, contradictory access requirements, and ambiguity. The same rubric (version 1.0) is used for all revisions.

Two separate methods are recorded: deterministic rule scoring (groundedness, section coverage, consistency, actionability, badge) and provider judge assessments with scores for the same four dimensions. Offline the judge is an explicitly heuristic, deterministic local implementation; selecting OpenAI opts into a remote JSON-scored judge only after endpoint approval. Judge assessments do not alter rule scores or Critic feedback.

## Demonstration comparison

The offline example intentionally starts the plan with a missing evidence citation and low actionability. Its first Critic revision attaches evidence to the unsupported claim and adds actionable detail. `tests/test_workflow.py` asserts the same plan's before/after groundedness and actionability scores improve, and that no role exceeds two revision cycles.

| Plan revision | Groundedness | Completeness | Consistency | Actionability (1–5) |
| --- | ---: | ---: | ---: | ---: |
| Initial (0) | 0.50 | 1.00 | 1.00 | 3.0 |
| After Critic (1) | 1.00 | 1.00 | 1.00 | 4.0 |

These are deterministic synthetic acceptance results, not a production benchmark. Retrieval relevance, embedding quality, judge calibration, and evaluation across real projects are not established by this small fixture set.
