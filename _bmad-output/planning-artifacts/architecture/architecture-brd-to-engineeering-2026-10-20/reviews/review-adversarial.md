---
title: Adversarial Architecture Review — BRD-to-Engineering Spine
type: architecture-review
intent: attack-compliance
reviewer: Critic Agent (Devil's Advocate)
review_date: 2026-10-20
spine_version: draft (2026-10-20)
---

# Adversarial Architecture Review: Divergence Holes and Minimal Fixes

## Executive Summary

**Verdict:** The spine establishes strong governance patterns (hub-and-spoke orchestration, versioned contracts, bounded revision loops) but contains **5 Blocking Issues** where multiple independent teams could literally comply with every AD and still produce incompatible, non-interoperable implementations. Each issue stems from ambiguous boundaries, unspecified ownership of intermediate state, or deferred schema decisions that permit silent format divergence.

**Severity Breakdown:**
- **Blocking Issues:** 5 (implementation would fail at handoff, citation, or retrieval)
- **Non-Blocking Issues:** 3 (would reduce quality but not break execution)
- **Suggestions:** 2 (marginal improvements)

---

## Blocking Issues

### B1: Citation ID Format and Storage Adapter Divergence

**Issue:** AD-4 requires "Citation IDs must resolve to the run's retrieved source set," but AD-7 defers vector-store adapter details (Qdrant vs. ChromaDB) and permits embedding-model changes. Two agents could independently implement the retrieval adapter:

- **Agent A (Team 1):** Stores citation IDs as `qdrant-{collection}:{offset}:{chunk_hash}`, assumes Qdrant persistent offsets within a collection.
- **Agent B (Team 2):** Stores citation IDs as `chroma-{collection_uuid}:{vector_id}:{timestamp}`, uses UUID and vector IDs because ChromaDB collection UUIDs are opaque and vector IDs may rotate with re-indexing.

**Concrete Failure Scenario:**
1. Planning Agent (Team 1) generates plan, cites `qdrant-brd-requirements:42:a3f9e2`. 
2. Critic Agent (Team 2) receives the plan, attempts to retrieve source with `qdrant-brd-requirements:42:a3f9e2`.
3. Qdrant adapter raises schema error: citation ID format unrecognized (expects `chroma-*` prefix).
4. Critic cannot validate citation claims; EM badge downgrade or artifact rejection.

**Impact:** Cross-team artifact handoff fails silently until discovered by Critic or EM review; requires emergency re-run or manual citation mapping.

**Severity:** Blocking.

**Root Cause:** AD-4 specifies citation *semantics* (must resolve) but not *format* or *storage contract*; AD-7 defers retrieval schema without requiring a shared citation interface.

**Minimal Fix:**

Add to AD-7 (Explicit vector-store migration boundary):
> **New sub-rule:** Define a `RetrievalCitationContract` enum and storage-agnostic citation format: `{source_id}#{chunk_index}#{embedding_model}`. All retrieval adapters must map their internal IDs (Qdrant offset, ChromaDB UUID, etc.) to this canonical format at query time and at index-rebuild time. Citation validation must reconstruct the canonical ID; mismatches trigger a validation error, not a silent skip.

**Estimated Effort to Implement:** 2–4 hours (add enum, adapter contract methods, validation tests).

---

### B2: Unresolved Requirement Representation and Assumption Ownership Conflict

**Issue:** AD-4 requires "Flag ambiguous or contradictory requirements; do not silently invent a resolution," but does not define who owns the "unresolved questions" field or how contradictions are propagated.

**Concrete Failure Scenario:**
1. BRD Parser identifies requirement "Performance: sub-200ms API latency" but also "Cost: minimize cloud spend." Flags as contradictory (low latency ↔ cost trade-off unresolved).
2. Engineering Plan Generator reads BRD, sees unresolved contradiction, assumes trade-off favors cost, includes "recommendation: edge caching to reduce API calls" in the plan without re-flagging.
3. Schedule Estimator receives plan, sees recommendation, allocates 3 sprints for edge infrastructure; misses that the underlying contradiction is unresolved.
4. EM review reveals artifact contradicts itself: plan assumes cost-first; Critic badge is Amber, but cost and latency requirements are still unresolved by export time.

**Impact:** Unresolved contradictions silently propagate downstream; Critic catches it late, but the planning effort is wasted. Unclear whether each agent independently re-flags or relies on inherited flags.

**Severity:** Blocking.

**Root Cause:** AD-4 mandates flagging ambiguities but does not define a propagation contract, ownership of unresolved-questions field, or decision points for agents when an unresolved requirement is encountered.

**Minimal Fix:**

Add to AD-4 (Shared evidence and uncertainty envelope):
> **New sub-rule:** Define an `UncertaintyItem` schema (type: `ambiguous_requirement|contradictory_requirement|missing_context`, source_requirement_ID, description, proposed_resolution_options[]). Each artifact inherits unresolved items from upstream and appends new findings; do not resolve or assume without re-flagging. If an agent must make a choice given unresolved uncertainty, emit a new UncertaintyItem with `type: assumption`, cite the inherited item, and document the assumption explicitly in the artifact. Critic validation: all assumptions must be traceable to an unresolved item; unresolved items with no assumptions inferred → Critic feedback loop.

**Estimated Effort to Implement:** 3–5 hours (define schema, add inheritance logic, Critic validation rules).

---

### B3: Model Context and Embedding Mismatch Between Retrieval Rebuild and Agent Execution

**Issue:** AD-6 establishes "EM selects generation and embedding models only from an evaluation-passed catalog," but AD-7 defers the migration boundary and does not specify when embedding-model changes invalidate a retrieval index or how agents bind to a specific embedding context.

**Concrete Failure Scenario:**
1. Initial prototype run: Embedding model = `text-embedding-3-small`, index built on 1,536 dimensions, Qdrant collection `brd-context-v1`.
2. Week later, EM upgrades to `text-embedding-3-large` (3,072 dimensions) from catalog; coordinator records new model in run config.
3. Retrieval Adapter (Team 1) interprets AD-7 as requiring index migration but assumes *no query re-embedding needed*; queries the new model against old index → dimension mismatch, Qdrant error.
4. Retrieval Adapter (Team 2) interprets AD-6 as requiring automatic re-embedding of all queries; rebuilds the index from scratch, takes 2 hours, plan agent times out.

**Impact:** Different implementations of "embedding-model change" lead to deadlock, timeout, or schema error; artifact export blocked.

**Severity:** Blocking.

**Root Cause:** AD-6 and AD-7 establish the principle (model catalog, migration boundary) but do not contractually bind agents to a specific embedding model for a run or define when query re-embedding vs. index rebuild is triggered.

**Minimal Fix:**

Add to AD-6 (Provider-neutral model access and evaluated model catalog):
> **New sub-rule:** Each run records `generation_model_id`, `embedding_model_id`, and `embedding_model_dimensions` in run metadata at initialization. Agents and retrieval adapters must not change the embedding model mid-run; the EM selects embedding models only at run start. If index is stale or dimensions mismatch query, the retrieval adapter raises a `RetrievalMigrationRequired` error to the coordinator, which routes to manual rebuild before re-attempting retrieval.

And to AD-7:
> **New sub-rule:** Persist metadata: `{store: 'qdrant'|'chromadb', collection_id, embedding_model_id, embedding_dimensions, corpus_version, last_rebuild_timestamp}`. Query contract: adapter accepts vector from query embedding with recorded embedding_model_id and dimensions; mismatch raises a validation error, not a silent re-embedding. Index rebuild requires coordinator approval and must pass retrieval regression checks before handoff to agents.

**Estimated Effort to Implement:** 4–6 hours (metadata storage, query validation, regression test framework).

---

### B4: Critic Rubric Interpretation and Badge Assignment Drift

**Issue:** AD-5 specifies thresholds (75% citation rate, 100% BRD coverage, zero contradictions, 4/5 actionability) and badge assignment (Green/Amber/Red), but does not define how the Critic *interprets* ambiguous claims, what "cited" means when a source is flagged as ambiguous, or how the Critic weights contradictions found in different artifacts.

**Concrete Failure Scenario:**
1. Solution Architect generates 20 design components; 15 are cited with chunks from knowledge base, 5 are standard patterns not in corpus (e.g., "use REST API" — industry default).
2. Critic (Team 1) counts citation rate as 15/20 = 75%, includes the 5 standard patterns as implicitly assumed valid, assigns Green badge (all thresholds met).
3. Critic (Team 2) counts only the 15 explicit citations as "cited"; the 5 standard patterns are design decisions without evidence anchor, cites them as unresolved assumptions. Citation rate 15/20 = 75%, but adds 5 unresolved assumptions → overall score 3.2 → Amber badge.
4. EM receives the same artifact with two different badges from parallel runs (e.g., if both teams' versions are cached or shared); credibility and export readiness are ambiguous.

**Impact:** Same artifact receives different badges depending on Critic implementation; EM approval becomes inconsistent; quality interpretation is not measurable or repeatable.

**Severity:** Blocking.

**Root Cause:** AD-5 defines numerical thresholds but not the decision rules for what counts as "cited" (explicit chunk ↔ industry standard), how to handle assumptions that augment cited claims, or how to aggregate contradictions across multiple artifacts.

**Minimal Fix:**

Add to AD-5 (Bounded Critic loop and common quality outcomes):
> **New sub-rule:** Define a `CitationEvidenceLevel` enum: 
> - `explicit_chunk`: cited with a source chunk ID that resolves. 
> - `assumption`: a design choice justified by inherited uncertainty or trade-off analysis; must name the assumption and its justification (e.g., "Assumed REST over gRPC because of prior context X").
> - `unresolved`: a claim with no evidence anchor. 
> 
> Citation rate threshold (75%) counts only `explicit_chunk` and `assumption` (where the assumption is justified in the artifact). `unresolved` claims are flagged as Critic feedback. Contradictions: a Critic finding applies only to pairs of claims within the same artifact or across same-run artifacts with the same run_id; cross-run comparisons are noted but do not affect badge. Rubric scoring: define a Critic rubric matrix (completeness 0–5, groundedness 0–5, actionability 0–5, consistency 0–5); aggregate as arithmetic mean; Green ≥ 4.0 and all thresholds met, Amber 3.0–3.9 or one threshold missed, Red < 3.0 or two+ thresholds missed.

**Estimated Effort to Implement:** 5–8 hours (define rubric schema, scoring logic, Critic prompt/agent refinement, rubric test cases).

---

### B5: Retrieval Regression Test Gate Definition and Corpus Versioning Divergence

**Issue:** AD-7 requires "Migration or embedding-model change requires rebuilding the index from source documents and passing retrieval regression checks before cutover," but does not define the regression test suite, how corpus versions are identified, or what "passing" means.

**Concrete Failure Scenario:**
1. Prototype corpus version `v1`: 50 representative BRD sections, 200 expected queries and ideal retrieved chunks.
2. Team 1 interprets "regression checks" as: if top-1 retrieval accuracy on v1 queries ≥ 98%, the new index passes.
3. Team 2 interprets "regression checks" as: test suite must include edge cases (misspellings, synonyms, domain terminology), run all 200 queries, top-k recall must be ≥ 95%, and latency < 500ms.
4. Prototype indices are rebuilt by both teams; Team 1's index has 98% top-1 accuracy but fails Team 2's latency and recall checks.
5. Coordinator receives conflicting signals: is the new index safe or not? Agents depend on retrieval quality but do not know which threshold to trust.

**Impact:** Retrieval migrations proceed without consistent validation; artifact quality degrades silently or deployments are blocked indefinitely because "regression checks" is not operationally defined.

**Severity:** Blocking.

**Root Cause:** AD-7 mandates regression checks but defers their definition; teams independently define thresholds without a shared, version-controlled test harness.

**Minimal Fix:**

Add to AD-7 (Explicit vector-store migration boundary):
> **New sub-rule:** Define a `RetrievalRegressionSuite` (version `{date}`, corpus_version, test_queries: [{query_text, expected_chunk_ids[], expected_rank_for_each[]}], thresholds). Store the suite in version control and reference it in run metadata. Regression gate logic: rebuild the index on the new vector store and embedding model, run the regression suite, report per-query NDCG and MRR scores; pass if mean NDCG ≥ 0.85 and mean latency ≤ 1000ms. Log results and record pass/fail in the retrieval adapter state. Only proceed to agent handoff if regression passes; otherwise emit a retrieval-migration-failed event and route to EM for manual investigation.

**Estimated Effort to Implement:** 6–10 hours (define suite schema, load/version in repo, implement regression runner, add EM reporting).

---

## Non-Blocking Issues

### N1: Run-State Serialization and Notebook Checkpoint Compatibility

**Issue:** AD-1 specifies "one LangGraph coordinator as the sole owner of run state," and AD-11 includes "Develop and evaluate in Python notebooks," but does not define the serialization format for run state or how notebook checkpoints interact with LangGraph's built-in checkpointing.

**Implication:** Notebooks may pickle run state, while LangGraph uses JSON; a notebook may save a checkpoint, a developer may resume in LangGraph, and the state formats diverge. Agents retrieve incompatible state objects.

**Severity:** Non-Blocking (impacts dev workflow, not production artifacts).

**Recommended Fix:** Add to AD-1: "Run state serialization is JSON; any checkpoint (notebook or LangGraph) must be JSON-serializable Pydantic models. Notebook checkpointing must use the same serialization format as the coordinator; define a `RunStateSnapshot` Pydantic model and serialize via `.model_dump_json()`. Any resume operation must deserialize via `.model_validate_json()`, raising a validation error if the snapshot is stale or incompatible."

**Estimated Effort:** 2–3 hours.

---

### N2: EM Approval Idempotency and Export Artifact Versioning

**Issue:** AD-9 mandates "Export only after an explicit EM approval," but does not define what happens if the EM approves, export fails, and the EM reapproves without re-running the Critic loop.

**Implication:** Export artifact versioning could diverge: one team bumps artifact version on every EM approval, another only on Critic revision. Downstream systems or audit trails may see duplicate export versions or orphaned approvals.

**Severity:** Non-Blocking (affects audit trail clarity, not core functionality).

**Recommended Fix:** Add to AD-9: "EM approval is idempotent; re-approving the same artifact does not create a new version. An export event includes the run_id, artifact_id, version, EM approval timestamp, and export timestamp. If export fails and EM reapproves, the coordinator re-attempts export without incrementing the artifact version; if a new Critic revision occurs, the artifact version is incremented and the EM must re-approve before export."

**Estimated Effort:** 1–2 hours.

---

### N3: Evaluation Dataset Versioning and Cross-Run Comparability

**Issue:** AD-10 requires "Use the same versioned evaluation dataset and rubric when comparing models," but does not specify how evaluation-dataset versions are recorded in run metadata or how stale datasets are detected.

**Implication:** A team may test Model A with eval-dataset v1, then test Model B with eval-dataset v2 (updated with new edge cases), and compare scores; another team uses eval-dataset v1 for both. Model selection recommendations diverge.

**Severity:** Non-Blocking (affects model comparison reliability, not artifact generation).

**Recommended Fix:** Add to AD-10: "Record evaluation_dataset_version and evaluation_rubric_version in run metadata. Evaluation comparison queries must filter runs by the same eval-dataset-version and eval-rubric-version; comparisons across different versions are flagged as non-comparable and require separate reporting."

**Estimated Effort:** 1–2 hours.

---

## Suggestions

### S1: Explicit Prompt Versioning and Agent Determinism Contract

**Issue:** AD-3 specifies "versioned Pydantic contract per role" but does not include prompt versions. Two agents with the same model/contract but different prompts could produce different outputs; determinism is implicit.

**Suggestion:** Add a `prompt_version` field to each agent's contract metadata. For reproducible artifact generation, log `{agent_name, contract_version, prompt_version, model_id, temperature}` in every agent's output. This enables audit trails and root-cause analysis if artifacts diverge.

**Estimated Effort:** 1–2 hours.

---

### S2: Explicit Knowledge-Corpus Versioning and Retrieval Staleness Detection

**Issue:** AD-7 mentions "corpus version" but AD-4 and AD-6 do not specify how to detect stale retrieval indices or warn agents if the corpus has been updated since the index was built.

**Suggestion:** Add a `corpus_version` field to the retrieval adapter's index metadata and a query-time check: if the current corpus version > index corpus version, emit a retrieval-staleness warning to the Critic. Agents can choose to rebuild or proceed with a caveat; the Critic notes staleness in the badge rationale.

**Estimated Effort:** 2–3 hours.

---

## Summary Table

| ID | Issue | Category | Impact | Minimal Fix Effort | Dependencies |
| --- | --- | --- | --- | --- | --- |
| B1 | Citation ID format and storage adapter divergence | Blocking | Handoff failure; Critic cannot validate | 2–4h | AD-4, AD-7 |
| B2 | Unresolved requirement propagation and assumption ownership | Blocking | Silent contradiction propagation | 3–5h | AD-4, contracts |
| B3 | Embedding model binding and retrieval migration | Blocking | Dimension mismatch or timeout | 4–6h | AD-6, AD-7, contracts |
| B4 | Critic rubric interpretation and badge drift | Blocking | Non-repeatable quality assessment | 5–8h | AD-5, Critic agent |
| B5 | Retrieval regression test definition and corpus versioning | Blocking | Unvalidated migrations; silent quality loss | 6–10h | AD-7, test framework |
| N1 | Run-state serialization and notebook checkpointing | Non-Blocking | Dev workflow friction; state divergence | 2–3h | AD-1, notebooks |
| N2 | EM approval idempotency and export versioning | Non-Blocking | Audit trail ambiguity | 1–2h | AD-9 |
| N3 | Evaluation dataset versioning and comparability | Non-Blocking | Model selection unreliability | 1–2h | AD-10 |
| S1 | Prompt versioning and agent determinism | Suggestion | Reproducibility; root-cause analysis | 1–2h | AD-3, contracts |
| S2 | Corpus versioning and retrieval staleness detection | Suggestion | Detection of outdated indices | 2–3h | AD-7, retrieval adapter |

---

## Recommendations for Next Steps

1. **Immediate (Critical Path):** Prioritize B1, B3, B5 — these are retrieval and contract boundaries that will cause failures at handoff if not defined. Expect 12–20 hours to define schemas and add validation.
2. **Early Sprint:** B2 and B4 determine artifact quality and consistency; expect 8–13 hours for Critic rubric definition and uncertainty propagation logic.
3. **Polish:** N1, N2, N3 improve robustness and audit trails; interleave with implementation.
4. **Documentation:** Update deferred section to cross-reference these minimal fixes by AD.

---

## Conclusion

The spine is strong in principle but leaves critical handoff boundaries unspecified. Five blocking issues stem from:
- **Deferred schema decisions** (citation format, uncertainty representation) that permit incompatible implementations.
- **Ambiguous ownership** (who propagates unresolved requirements? who validates regression checks?) that leads to silent divergence.
- **Underspecified binding** (embedding models mid-run, Critic thresholds) that permits conflicting interpretations of the same AD.

Each minimal fix is straightforward and typically requires 1–3 new sub-rules or schema definitions. Implementing all five blocking fixes and the three non-blocking refinements is estimated at **28–40 hours** and will make the spine implementation-ready and resilient to multi-team divergence.
