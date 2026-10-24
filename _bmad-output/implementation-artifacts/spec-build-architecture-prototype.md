---
title: 'Offline-ready BRD-to-engineering prototype'
type: 'feature'
created: '2026-10-23'
status: 'done'
route: 'full'
route_source: 'auto'
review: 'thorough'
review_source: 'auto'
lenses_ran: ['blind-hunter', 'edge-case-hunter', 'verification-gap', 'intent-alignment']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-brd-to-engineeering-2026-10-20/ARCHITECTURE-SPINE.md'
  - '{project-root}/multi-agent-brd-to-engineeering-system.md'
baseline_commit: '71a5ccaa35e5218f4814cde9bd8a5f7245cbc1d1'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The repository currently contains the system brief and architecture, but no runnable application, tests, or reproducible setup. Engineering managers cannot validate the proposed BRD-to-engineering workflow end to end.

**Approach:** Build a lightweight Python prototype that follows the architecture from BRD ingestion through retrieval-grounded artifacts, critic review, evaluation, human approval, and export. Default to a deterministic local provider so the full demo runs without credentials; keep real OpenAI inference opt-in. It must be runnable in Google Colab and locally in VS Code; production deployment and scale remain future work.

## Boundaries & Constraints

**Always:** Use a coordinator-owned LangGraph workflow and validated, versioned Pydantic contracts for all seven roles. Preserve source requirements, citation IDs, assumptions, uncertainty, artifact revisions, and explicit errors across handoffs. Use local Qdrant behind a retrieval adapter. Limit critic revisions to two cycles per artifact. Keep BRD text and secrets out of logs and source control. Require approval for the exact artifact revisions before export.

**Never:** Add cloud infrastructure, production multi-user persistence, Azure deployment, ChromaDB, real confidential BRD data, or stretch features to this prototype. Do not imply that evaluation of synthetic data establishes production readiness.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Valid BRD | Synthetic Markdown or text BRD and knowledge corpus | Normalized requirements, retrieved evidence, seven validated artifacts, scores, and citations | Surface parser or contract errors; do not continue invalid handoffs |
| Invalid BRD | Empty, malformed, or unsupported file | No workflow run or export | Return a clear input-validation error |
| No usable retrieval | Valid BRD, zero relevant chunks | Continue with an explicit evidence disclaimer; artifact badge cannot exceed Amber | Record the retrieval failure without logging BRD content |
| Critic cap reached | Artifact still has findings after two revisions | Preserve findings and final badge for EM disposition | Stop the loop; do not silently accept or discard findings |
| Approval and export | Approved run and artifact revisions | Export only those approved revisions through the typed exporter/mock integration | Reject export if approval is missing or revisions changed |

</frozen-after-approval>

## Code Map

- `_bmad-output/planning-artifacts/architecture/architecture-brd-to-engineeering-2026-10-20/ARCHITECTURE-SPINE.md` — authoritative architecture, decisions AD-1 through AD-13, structural seed, and production deferrals.
- `multi-agent-brd-to-engineeering-system.md` — agent responsibilities, prototype deliverables, RAG and evaluation requirements, guardrails, and acceptance rubric.
- `README.md` — currently only a project title/use-case note; replace with reproducible setup, run, notebook, architecture, and safety instructions.
- No product source, package manifest, notebook, fixtures, or product tests exist yet. Establish the package and test structure; do not treat BMAD runtime tests as product coverage.

## Tasks & Acceptance

**Execution:**
- [x] `pyproject.toml`, `src/`, `tests/` — establish a pinned, minimal Python package and reusable local/Colab install path; include only prototype dependencies.
- [x] `src/contracts/` — define shared evidence, uncertainty, artifact, run-state, and versioned per-role Pydantic contracts with validation tests.
- [x] `src/ingestion/`, `knowledge/`, `src/retrieval/` — validate Markdown/text BRDs, normalize source-linked requirements, include varied synthetic knowledge sources, and implement documented chunking and local Qdrant retrieval behind an adapter.
- [x] `src/agents/`, `src/providers/`, `src/orchestration/` — implement the seven roles and reflection; keep provider calls behind an adapter and make dependency-ordered handoffs, targeted revisions, and the two-cycle cap coordinator-owned.
- [x] `src/evaluation/`, `src/storage/`, `src/tools/` — implement deterministic rubric checks and model-assisted evaluation, badges, safe structured operational records, revision metrics, approval-bound export, and a mock external integration.
- [x] `app/`, `notebooks/`, `data/` — provide an EM review/demo flow, a runnable Colab notebook, and a synthetic end-to-end BRD with reproducible local data.
- [x] `README.md`, `docs/`, `tests/` — document contracts, retrieval, evaluation, guardrails, operational criteria, and setup; cover unit, guardrail, and end-to-end behavior.

**Acceptance Criteria:**
- Given the documented setup in Colab or VS Code, when a developer installs the project and runs its test command, then product tests pass without cloud services or committed credentials.
- Given the synthetic BRD and sample corpus, when the prototype runs end to end, then the seven role outputs validate, respect dependency order, and carry resolvable citations, assumptions, uncertainty, and revision identities.
- Given malformed input, invalid handoff data, empty retrieval, and persistent critic findings, when each condition occurs, then it surfaces explicitly, follows the edge-case matrix, and cannot produce a success-shaped approved export.
- Given a run with critic feedback, when an artifact is revised, then no more than two cycles occur and evaluation records comparable before/after results with measurable improvement on at least two metrics for the documented synthetic example.
- Given a run that has not been approved, or whose approved revisions have changed, when export is attempted, then export is blocked; explicit approval permits only the approved revisions.
- Given any execution, when operational records are inspected, then they contain useful run/agent IDs, model/config metadata, scores, timings, retrieval IDs, guardrail events, and revision counts, but no raw BRD content or secrets.

## Implementation Notes

Implemented the seven-role LangGraph prototype with Pydantic contracts, Markdown/text ingestion, synthetic local Qdrant corpus, offline deterministic provider, opt-in OpenAI adapter, critic revisions capped at two, deterministic and provider-judge evaluations, revision-bound EM approvals, Markdown export, mock issue tracking, Streamlit review UI, and Colab walkthrough.

Handoff checks now resolve the full citation identity (source, chunk, and locator). Approval records are immutable and bind both the artifact revision and a content digest, so edits without a revision increment also invalidate export. Expected validation errors are surfaced; unexpected exceptions are not converted to generic success-shaped fallbacks. Documentation calls out the API-key boundary and synthetic-only evaluation.

Validation on Python 3.14: editable install with dev dependencies succeeded; all 30 pytest tests pass; `compileall` passes; all notebook code cells execute locally; Streamlit health endpoint returns HTTP 200.

## Spec Change Log

## Review Triage Log

| Finding | Verdict | Route | Evidence / disposition |
|---|---|---|---|
| BH-1 approval error logging | false | rejected | Approval validation raises `ApprovalError`, which the UI displays; approval failures do not need persistence or a separate operational record in this single-user, ephemeral prototype. |
| BH-2 feature-hash collision risk | low | rejected | The 96-dimensional hash is explicitly documented as a local baseline, and the fixed retrieval regression test passes on the small synthetic corpus; semantic embeddings are outside this lightweight prototype. |
| BH-3 empty corpus documents | low | rejected | The checked-in corpus has seven populated sources; a no-hit corpus is visibly handled with an evidence disclaimer and non-Green badge. Empty custom documents are not an everyday path requiring more guards here. |
| BH-4 non-monotonic revision numbers | false | rejected | Workflow revisions are created through `revise_artifact`, which increments the current revision and stops at two; the public run path does not accept a caller-supplied prior revision. |
| BH-5 Qdrant collection-name collision | false | rejected | Each default adapter owns a separate `QdrantClient(":memory:")`; a caller reusing the same client encounters Qdrant's explicit duplicate-collection error rather than silent overwrite. |
| BH-6 multiline assumption formatting | false | rejected | Export preserves the assumption string, including embedded newlines; current generated assumptions are single-line, so no content-loss case was shown. |
| BH-7 truncated SHA-1 chunk-ID collision | low | rejected | IDs are used in a small synthetic corpus with a fixed collision-free retrieval regression set; collision handling at production corpus scale is outside this prototype. |
| BH-8 missing orchestration timeout | low | rejected | The coordinator's revision queue is bounded at two cycles; external OpenAI use is opt-in and failures propagate. Production latency/resource limits are deferred by the intent. |
| BH-9 approval JSON can be forged | false | rejected | Approval is an in-process local prototype record, not a persisted or externally trusted credential. Its tuple fields and artifact hashes prevent accidental post-approval mutation; authentication/signing is a production concern. |
| BH-10 retrieval disclaimer mismatch | false | rejected | Empty retrieval sets artifact/run disclaimers and rubric `retrieval_empty`; tests assert the UI-facing result has no Green artifacts. |
| BH-11 invalid `ExportRequest` mappings | false | rejected | `export_markdown` verifies selected IDs are a subset of the immutable approval before constructing the internal `ExportRequest`. |
| BH-12 critic cap absent from coordinator | false | rejected | The Critic only queues findings whose cycle count is below two; workflow tests assert cycles reach two at most and remain visible at the cap. |
| EC-1 retriever initialization guard | false | rejected | `load_knowledge` and Qdrant construction exceptions propagate before graph execution; they are not silently converted into a successful run. |
| EC-2 dynamic unknown specialist role | false | rejected | Graph nodes are registered from the five fixed role names; `_upstream_roles` is only called with those constants. |
| EC-3 revision history overwrites scores | false | rejected | History is a list per artifact ID and is appended only when the artifact revision changes; final score lookup is keyed by revision. |
| EC-4 upstream handoff revalidation | false | rejected | Every artifact is validated when created, its IDs are checked by the Critic, and approval now rejects stale upstream revision references. |
| EC-5 retrieval failure event conflated with no hits | low | patch | The retrieval operational record now distinguishes `retrieval_error` from `no_usable_evidence`; `test_retrieval_failure_is_visible_without_logging_source_text` verifies the event and surfaced run error. |
| EC-6 dangling critic queue IDs | false | rejected | Queue entries are derived from findings on current artifacts, not external input; the revise node resolves the artifact before changing state. |
| EC-7 score aggregation division by zero | false | rejected | All score averages guard empty collections with `max(1, len(...))`. |
| EC-8 unknown provider model fallback | low | patch | Operational records now read required `Provider` protocol attributes directly instead of silently writing `"unknown"`; the full suite passes. |
| EC-claim-1 critic cap not enforced | false | rejected | The cycle `< 2` filter runs before the revise route; both the cap unit test and empty-evidence end-to-end case verify no third revision. |
| EC-claim-2 malformed input unhandled | false | rejected | `parse_brd` raises `InputValidationError` (a `ValueError`); the app surfaces it, and tests verify malformed input is rejected before any run result is created. |
| EC-claim-3 retrieval failure swallowed | false | rejected | Retrieval failure is represented in `RunResult.orchestrator.errors`, the evidence disclaimer, and a `retrieval_error` operational event; it cannot become an unmarked Green run. |
| VG-1 revision-cap boundary untested | false | rejected | End-to-end tests assert all revisions are at most two and a persistent no-evidence finding reaches exactly two cycles; a third cycle would violate the bounded revision field and fail the run. |
| VG-2 stale upstream revision at approval | medium | patch | `approve_run` now checks each selected artifact's upstream artifact ID and revision against the current run; `test_approval_rejects_stale_upstream_artifact_revision` verifies rejection. |
| VG-3 empty retrieval Green-badge check | false | rejected | The rubric scores empty retrieval as zero groundedness, records `retrieval_empty`, and the no-hit workflow test asserts every artifact is non-Green. |
| VG-4 cap documentation concern | false | rejected | Documentation and tests agree: reaching two cycles is allowed, a third is not. |
| IA-1 hosted Colab run not performed | low | rejected | All notebook code cells execute locally; the notebook targets Python 3.13 and the current Colab default is Python 3.13. A hosted Colab account/session was unavailable, but no incompatibility was evidenced. |
| IA-2 retrieval regression test absent | false | rejected | `test_fixed_retrieval_regression_queries_meet_the_versioned_threshold` executes the versioned fixed-query suite. |
| IA-3 guardrail event coverage absent | false | rejected | Workflow tests assert both no-usable-evidence and retrieval-error guardrail events. |
| IA-4 upstream revision coverage absent | medium | patch | Approval-time upstream revision validation and a stale-dependency test were added as noted in VG-2. |
| IA-5 optional provider failure path untested | low | rejected | Remote calls are opt-in; an unexpected provider exception is no longer caught as a generic fallback and therefore cannot yield a success-shaped result. |
| IA-S1 coverage table suggestion | low | rejected | No correctness defect was identified; the focused test suite names the behaviors it covers. |
| IA-S2 notebook setup-marker suggestion | low | rejected | Notebook setup is documented in its introductory cell and README; extra markers would be presentational only. |
| IA-S3 revision history not visible in UI | false | rejected | The Critic & evaluation tab renders revision-history scores by artifact and revision. |

## Design Notes

Keep the prototype's storage local and ephemeral, and expose providers and retrieval behind narrow adapters so production choices can be revisited without changing agent contracts. The documented architecture's Qdrant prototype target and ChromaDB security gate remain in force.

## Verification

**Commands:**
- `python -m pip install -e ".[dev]"` — expected: package and development dependencies install in a clean local environment.
- `python -m pytest` — expected: all project tests pass without API credentials or cloud services.
- `streamlit run app/main.py` — expected: the EM demo opens and can process the included synthetic BRD using the selected default provider mode.

**Manual checks (if no CLI):**
- Run every notebook cell from a fresh Colab runtime and verify the documented demo outputs, citations, badges, guardrails, and approval-gated export.
