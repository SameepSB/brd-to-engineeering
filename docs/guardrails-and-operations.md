# Guardrails and operational criteria

## Input, grounding, and approval guardrails

- Accept only non-empty UTF-8 Markdown/text up to 2 MB; reject unsupported files and null bytes before generating a run ID.
- Validate all role contracts at every handoff. Unknown requirement IDs, unresolved citation IDs, and invalid uncertainty references stop the run explicitly.
- Generated claims retain requirement references and citations. Unsupported claims appear as Critic findings; source-free claims must be explicit assumptions.
- Critic revisions are targeted to the originating artifact and stop after two cycles. Findings remain visible at the cap.
- Export requires explicit approval by a named EM for the exact run and artifact revisions. A changed revision, unapproved artifact, or different run is rejected. Approved exports preserve warnings and findings and omit source BRD content.
- The default mode is offline, deterministic, and uses fabricated BRDs. No raw BRD or secret enters operational records. OpenAI requires an optional dependency, API key, and affirmative endpoint-approval control.

## Safe operational records

Records are structured and local/ephemeral: run and agent IDs, input hash, artifact ID, provider/model, duration, retrieved chunk IDs, scores, guardrail events, and revision count. Raw BRD text, prompts, and credentials are not fields in the operational record schema. Model-assisted judge notes are separate from Critic findings.

## Success criteria

1. All product tests pass offline; input, contract, approval, retrieval, and revision-cap cases are covered.
2. The included synthetic BRD completes all seven roles with validated contracts and resolvable citations.
3. The sample plan revision improves at least two rubric metrics; the report retains before/after scores.
4. No operational record contains the BRD text or API credential values.
5. No artifact export succeeds without a matching approval record.

## Failure modes and mitigations

| Failure | Detection | Mitigation |
| --- | --- | --- |
| Schema-invalid agent output | Pydantic validation at handoff | Stop immediately with an explicit `WorkflowError`; do not route malformed data downstream. |
| No usable retrieval evidence | Empty adapter result or retrieval error | Preserve disclaimer and guardrail event; cap Green, retain uncertainty, require human review. |
| Critic findings survive the cap | Revision count reaches two | Stop revision, retain findings and badge for EM disposition. |
| Approval stale or absent | Exact revision comparison | Reject export; require approval of current revisions. |
| External API unavailable | Provider exception | Surface an explicit failure; offline provider remains default. |

## Release boundary

This prototype does not establish production readiness. Before real BRDs or production use, resolve approved provider/data boundaries, retention and deletion, identity, persistent run/approval storage, backup and recovery, network isolation, concurrency targets, and model/retrieval quality gates.
