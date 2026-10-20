# Architecture Spine Rubric Review

**Verdict: Needs revision before handoff.** The spine makes useful feature-altitude decisions about orchestration, handoffs, provenance, model/vector-store boundaries, approval, and an initial Azure topology. The mechanical spine linter passes, but the semantic review finds unresolved mandatory seams and scope requirements that can still produce incompatible or incomplete builds.

## Scope and validation

Reviewed `ARCHITECTURE-SPINE.md` against the BMad good-spine checklist and its source, `multi-agent-brd-to-engineering-system.md`. The spine linter returned **0 findings**. The pinned PyPI package versions matched the current official PyPI versions at review time: LangGraph 1.2.16, Streamlit 1.66.0, qdrant-client 1.19.1, and ChromaDB 1.5.9. Python 3.13 is an explicit supported minor selection. No implementation exists in this repository to contradict the greenfield decisions; no inherited parent spine is identified.

## Checklist result

| Checklist area | Result | Assessment |
| --- | --- | --- |
| Fixes real divergence points at feature altitude | **Partial** | Orchestration, dependencies, provider/vector-store boundaries, and approval are specified; required integration, safety, and operating seams remain open. |
| Each AD Rule is enforceable and prevents its divergence | **Partial** | Most rules are concrete. AD-5's badge thresholds overlap without precedence or a scoring formula; AD-6/10 do not define model-catalog pass criteria; AD-4 leaves “non-trivial” undefined. |
| Deferred work cannot permit incompatible builds | **Fail** | Agent contract fields/fixtures, normalized BRD and retrieval interfaces, and the required external integration remain deferred. |
| Named technology/version currency | **Pass, with a compatibility caveat** | Four pinned package versions match current PyPI releases. Python 3.13 is stated only at minor-version level; runtime compatibility should be checked for the target notebook/hosting environment. |
| Ratifies brownfield code | **Not applicable** | The repository has no application implementation to reconcile against. |
| Covers source capabilities | **Fail** | The map omits or weakly governs mandatory external integration, hallucination/scope-creep controls, measurable evaluation improvement, and monitoring/operationalization. |
| Preserves inherited decisions | **Not applicable** | No parent spine is identified (`companions: []`). |
| Addresses dimensions owned at this altitude, including operations/deployment | **Partial** | Prototype and initial Azure topology are stated and production hardening is deferred, but required success/failure criteria and operational monitoring decisions are absent. |

## Findings

### R-1 — High: Contract interfaces are deferred past the point of parallel implementation

**Location:** AD-3; Deferred, first bullet (approximately lines 70–71, 208)

AD-3 requires seven role-specific Pydantic contracts and validation at every handoff, but the exact schemas and fixtures are postponed until implementation. The source specification requires an agent contract reference that identifies schemas and consumers. Role-level descriptions do not settle required/optional fields, identifiers, error results, or who consumes each field. Separate agent implementers can satisfy the prose while producing incompatible contracts.

**Recommendation:** Decide the minimum versioned input/output shape and producer-consumer matrix for each handoff in the spine (or a binding companion); defer only implementation details and fixtures. Make schema change/versioning policy explicit.

### R-2 — High: The required external integration is explicitly deferred

**Location:** Deferred, external integrations bullet (approximately line 214); Capability → Architecture Map

The source's submission checklist requires tool calling demonstrated through export plus at least one external integration using mock data. The spine instead says integrations are implemented only when the EM workflow selects a target, and the capability map has no integration row. This is a direct scope conflict, not merely an optional future extension; it also leaves integration ownership, approval boundary, and payload shape open.

**Recommendation:** Select one minimal integration for the initial scope (a mock-backed adapter is sufficient if that is the intended demonstration), define its contract and approval/export boundary, and map it to a governing AD. Defer additional destinations only.

### R-3 — High: Required hallucination and scope-creep controls are not specified as guardrails

**Location:** AD-4, AD-8; Capability → Architecture Map

AD-4 requires citations and ambiguity handling, and AD-8 addresses confidentiality, but neither states how to detect and block or flag claims unsupported by the BRD/retrieved evidence or requirements introduced beyond the BRD. The source explicitly requires both hallucination detection and scope-creep prevention as implemented guardrails. Citation presence alone does not ensure claim support or prevent a generated requirement from being cited to unrelated context.

**Recommendation:** Add enforceable claim-to-BRD/RAG support checks and a requirement-coverage/scope-creep check, including the failure outcome (flag, revise, block export, or explicit EM disposition). Map the controls to an AD and evaluation cases.

### R-4 — High: BRD normalization and retrieval boundaries remain open across teams

**Location:** AD-2, AD-4, AD-7; Deferred, second bullet (approximately line 209)

The spine defers supported BRD formats, parser, extraction/chunk boundaries, metadata fields, retrieval parameters, and refresh policy. AD-2 nevertheless requires agents to consume a normalized BRD and AD-4 relies on stable requirement and citation identifiers. Without a minimum normalized-requirement and indexed-chunk schema, ingestion, retrieval, and agent teams can make incompatible assumptions about IDs, source locations, chunk references, and refresh/version behavior.

**Recommendation:** Define the stable normalized BRD and indexed-evidence envelopes plus source/chunk identity and corpus-version rules. Keep parser choice and empirically tuned chunking/top-k thresholds open if desired, but require compatible interfaces and regression gates.

### R-5 — Medium: Badge rules can yield different outcomes for the same scores

**Location:** AD-5 (approximately line 82)

Amber is defined as one missed threshold or an overall score of 3.0–3.9; Red is two or more missed thresholds or an overall score below 3.0. A result with one missed threshold and a score below 3.0 qualifies for both descriptions. The overall-score aggregation/rounding method is also unspecified, so independent evaluators can assign different badges.

**Recommendation:** Define score aggregation and rounding, and specify precedence (for example, Red overrides Amber), including behavior at exact boundaries and for missing evaluator results.

### R-6 — Medium: Evaluation requirements do not enforce the required improvement evidence

**Location:** AD-10; Capability → Architecture Map evaluation row

AD-10 requires rule-based checks and LLM-as-Judge and says comparisons use a common versioned dataset/rubric. It does not require the source's representative BRD/edge-case coverage, expert-scored Critic calibration, or measurable improvement on at least two metrics across revisions. “Evaluation methods are explicit and comparable” therefore does not ensure the required evaluation capability is delivered.

**Recommendation:** Specify the minimum dataset composition and calibration set, require at least two named improvement metrics with baseline/revision comparisons, and make that evidence a release/demo gate.

### R-7 — Medium: Operationalization lacks the source's required success/failure and monitoring decisions

**Location:** AD-8, AD-11, Consistency Conventions; Deferred, production Azure bullet

The spine defines a prototype and initial Azure topology, metadata-only logging, and defers production hardening. It does not decide prototype success criteria, failure modes/mitigations, or how failures and service health are monitored. The source requires success/failure defined upfront, structured execution logging, and an operationalization plan with monitoring. Deployment topology alone does not make those operating behaviors consistent.

**Recommendation:** Add the minimum prototype operational envelope: measurable success/failure conditions, handling for parse/schema/no-retrieval/model/export failures, health and quality signals, and where/how operators see them. Keep production-scale availability and disaster recovery deferred.

### R-8 — Medium: Model-catalog admission rule has no defined pass threshold

**Location:** AD-6 and AD-10 (approximately lines 88, 112)

“Evaluation-passed catalog” and “configured quality gates” do not say which versioned results or thresholds admit a generation/embedding model. AD-5's artifact badge thresholds do not directly define model admission. Two teams can expose different models as selectable while both claiming to follow the rule.

**Recommendation:** Define the model admission criteria, evaluation dataset/rubric version, minimum score/guardrail constraints, and catalog invalidation/re-evaluation conditions. Keep the actual model IDs configurable.

### R-9 — Low: The source reference in front matter does not resolve

**Location:** Front matter `sources` (approximately line 15)

The listed relative source is `../../../../multi-agent-brd-to-engineeering-system.md`, but the repository source file is `multi-agent-brd-to-engineering-system.md`. The extra `e` prevents the provenance link from resolving and makes the basis for this spine harder to reproduce.

**Recommendation:** Correct the path and verify it resolves from the spine's directory.

## Consolidated disposition

Address R-1 through R-4 before handing parallel implementation to separate contributors. Resolve R-5 through R-8 before treating quality badges, evaluation, model selection, and operations as shared system behavior. Correct R-9 as a small traceability fix. The existing stack pins and linter result do not offset these semantic gaps.
