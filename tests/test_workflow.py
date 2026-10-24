from pathlib import Path

import pytest

from src.agents.critic import review_artifacts
from src.agents.roles import build_artifact, revise_artifact
from src.contracts.schemas import Claim, Citation, PlanArtifact
from src.ingestion.parser import InputValidationError, parse_brd
from src.orchestration.graph import WorkflowError, _validate_handoff, run_workflow
from src.providers.deterministic import DeterministicProvider
from src.retrieval.adapter import LocalQdrantAdapter, RetrievedChunk, load_knowledge
from src.storage.approval import ApprovalError, approve_run
from src.storage.run_store import RunStore
from src.tools.export import export_markdown
from src.tools.contracts import MockIntegrationRequest
from src.tools.integration import MockIssueTracker

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = (ROOT / "data" / "sample_brd.md").read_text(encoding="utf-8")


class EmptyRetriever:
    def retrieve(self, query: str, *, top_k: int | None = None):
        return []


class BrokenRetriever:
    def retrieve(self, query: str, *, top_k: int | None = None):
        raise RuntimeError("local index unavailable")


def test_end_to_end_order_citations_revisions_and_two_metric_improvement():
    result = run_workflow(SAMPLE, "sample_brd.md")
    assert set(result.artifacts) == {
        "engineering_plan",
        "schedule",
        "solution_architect",
        "poc_planner",
        "tech_stack",
    }
    assert result.orchestrator.status == "completed"
    assert len(result.orchestrator.completed_roles) == 7
    assert {record.agent_id for record in result.operational_records} >= set(result.orchestrator.completed_roles)
    requirement_ids = {item.requirement_id for item in result.normalized_brd.requirements}
    expected = [
        "engineering_plan",
        "schedule",
        "solution_architect",
        "poc_planner",
        "tech_stack",
    ]
    positions = [result.orchestrator.transition_order.index(role) for role in expected]
    assert positions == sorted(positions)
    assert result.artifacts["schedule"].upstream_artifact_ids == [
        result.artifacts["engineering_plan"].artifact_id
    ]
    assert set(result.artifacts["solution_architect"].upstream_artifact_ids) == {
        result.artifacts["engineering_plan"].artifact_id,
        result.artifacts["schedule"].artifact_id,
    }
    assert set(result.artifacts["tech_stack"].upstream_artifact_ids) == {
        result.artifacts["engineering_plan"].artifact_id,
        result.artifacts["solution_architect"].artifact_id,
        result.artifacts["poc_planner"].artifact_id,
    }
    for role, artifact in result.artifacts.items():
        expected_upstream = artifact.upstream_artifact_revisions
        assert all(
            result.artifacts[upstream_role].revision == upstream_revision
            for upstream_role, upstream_revision in expected_upstream.items()
        )
    assert not result.critic.findings
    retrieved_ids = {chunk for record in result.operational_records for chunk in record.retrieved_chunk_ids}
    for artifact in result.artifacts.values():
        assert artifact.contract_version == "1.0"
        assert artifact.source_requirement_ids
        assert set(artifact.source_requirement_ids).issubset(requirement_ids)
        assert all(
            set(claim.requirement_refs).issubset(requirement_ids)
            for claim in artifact.claims
        )
        assert all(
            citation.chunk_id in retrieved_ids
            for claim in artifact.claims
            for citation in claim.citations
        )
        assert artifact.revision <= 2
    plan = result.artifacts["engineering_plan"]
    scores = result.revision_history[plan.artifact_id]
    assert scores[0].revision == 0 and scores[-1].revision == plan.revision
    assert scores[-1].groundedness > scores[0].groundedness
    assert scores[-1].actionability > scores[0].actionability
    assert result.evaluation["methods"] == ["deterministic_rules", "provider_judge"]
    assert set(result.evaluation["judge_scores"]) == {
        artifact.artifact_id for artifact in result.artifacts.values()
    }
    assert all("note" in item for item in result.evaluation["judge_scores"].values())
    assert result.retrieval_metadata["store"] == "qdrant-local"
    assert all(record.input_hash == result.input_hash for record in result.operational_records)
    serialized_records = str([record.model_dump(mode="json") for record in result.operational_records])
    assert "engineering request review prototype" not in serialized_records
    assert all(record.score is not None for record in result.operational_records if record.agent_id in result.artifacts)


def test_invalid_input_produces_no_run_result():
    with pytest.raises(InputValidationError):
        run_workflow("", "empty.md")
    with pytest.raises(InputValidationError):
        run_workflow(SAMPLE, "sample.pdf")


def test_no_usable_retrieval_continues_with_disclaimer_and_no_green_artifact():
    result = run_workflow(SAMPLE, "sample.md", retriever=EmptyRetriever())
    assert result.evidence_disclaimer
    assert all(artifact.retrieval_disclaimer for artifact in result.artifacts.values())
    assert all(artifact.badge != "Green" for artifact in result.artifacts.values())
    assert any("no_usable_evidence" in record.guardrail_events for record in result.operational_records)
    assert "no_usable_evidence" in result.orchestrator.guardrail_events
    assert result.orchestrator.status == "completed"
    assert all(artifact.revision <= 2 for artifact in result.artifacts.values())
    assert result.critic.findings
    assert any(cycles == 2 for cycles in result.critic.revision_cycles.values())


def test_retrieval_failure_is_visible_without_logging_source_text():
    result = run_workflow(SAMPLE, "sample.md", retriever=BrokenRetriever())
    assert result.evidence_disclaimer
    assert result.orchestrator.errors == ["RuntimeError: retrieval adapter failed"]
    retrieval_record = next(
        record for record in result.operational_records if record.agent_id == "retrieval"
    )
    assert retrieval_record.guardrail_events == ["retrieval_error"]
    assert SAMPLE not in str(retrieval_record.model_dump(mode="json"))


def test_invalid_citation_handoff_is_blocked():
    brd, uncertainties = parse_brd("# Goal\n\n- Approve every synthetic request.", "source.md")
    artifact = PlanArtifact(
        run_id="run-test",
        artifact_id="run-test-plan",
        source_requirement_ids=["REQ-001"],
        claims=[
            Claim(
                text="Unsupported claim",
                requirement_refs=["REQ-001"],
                citations=[Citation(source_id="missing", chunk_id="missing-chunk", source_locator="missing.md")],
            )
        ],
        covered_sections=brd.section_ids,
        actionability=4,
        phases=["Plan"],
        milestones=["Approval"],
        risks=["Scope"],
        team_composition=["Engineer"],
        reflection="Reviewed.",
    )
    with pytest.raises(WorkflowError, match="not in this run"):
        _validate_handoff(artifact, brd.requirements, [])


def test_citation_must_match_full_retrieved_evidence_identity():
    brd, _ = parse_brd("# Goal\n\n- Approve every synthetic request.", "source.md")
    evidence = [
        RetrievedChunk(
            source_id="KNOW-STANDARD",
            chunk_id="chunk-1",
            source_locator="standards.md#chunk-1",
            text="Use least privilege.",
            score=0.9,
        )
    ]
    artifact = PlanArtifact(
        run_id="run-test",
        artifact_id="run-test-plan",
        source_requirement_ids=["REQ-001"],
        claims=[
            Claim(
                text="A source-linked claim.",
                requirement_refs=["REQ-001"],
                citations=[
                    Citation(
                        source_id="ATTACKER-SOURCE",
                        chunk_id="chunk-1",
                        source_locator="standards.md#chunk-1",
                    )
                ],
            )
        ],
        covered_sections=brd.section_ids,
        actionability=4,
        phases=["Plan"],
        milestones=["Approval"],
        risks=["Scope"],
        team_composition=["Engineer"],
        reflection="Reviewed.",
    )
    with pytest.raises(WorkflowError, match="not in this run's retrieved set"):
        _validate_handoff(artifact, brd.requirements, evidence)


def test_critic_revision_cap_retains_findings_without_a_third_revision():
    brd, uncertainties = parse_brd("# Goal\n\n- Review each submitted request.", "source.md")
    artifact = build_artifact(
        "engineering_plan",
        "run-cap",
        brd,
        uncertainties,
        [],
        DeterministicProvider(),
        revision=2,
    ).model_copy(update={"actionability": 1.0})
    critic, _ = review_artifacts(
        "run-cap",
        {"engineering_plan": artifact},
        brd.section_ids,
        set(),
        {artifact.artifact_id: 2},
    )
    revised = revise_artifact(artifact, [], critic.findings[0].correction)
    assert revised.revision == 2
    assert revised.actionability == 1.0
    assert critic.findings
    assert critic.revision_cycles[artifact.artifact_id] == 2


def test_export_requires_approval_and_rejects_stale_or_unselected_revisions():
    result = run_workflow(SAMPLE, "sample.md")
    with pytest.raises(ApprovalError, match="explicit"):
        export_markdown(result, None)
    with pytest.raises(ApprovalError, match="different run"):
        from src.storage.approval import ApprovalRecord

        export_markdown(
            result,
            ApprovalRecord(
                run_id="other-run",
                approver="EM",
                artifact_revisions=(),
                artifact_hashes=(),
            ),
        )
    with pytest.raises(ApprovalError, match="identified"):
        approve_run(result, "")
    with pytest.raises(ApprovalError, match="one or more"):
        approve_run(result, "EM", [])
    approval = approve_run(result, "EM")
    export = export_markdown(result, approval)
    assert export.run_id == result.run_id
    assert "Approval is bound" not in export.markdown
    assert "does not include the original BRD" in export.markdown

    plan = result.artifacts["engineering_plan"].model_copy(update={"revision": result.artifacts["engineering_plan"].revision + 1})
    changed_artifacts = {**result.artifacts, "engineering_plan": plan}
    changed = result.model_copy(update={"artifacts": changed_artifacts})
    with pytest.raises(ApprovalError, match="stale"):
        export_markdown(changed, approval)

    with pytest.raises(ApprovalError, match="not explicitly approved"):
        export_markdown(result, approval, ["unknown-artifact"])
    with pytest.raises(ApprovalError, match="one or more"):
        export_markdown(result, approval, [])
    result.artifacts["engineering_plan"].claims[0].text = "Edited after approval without a revision change."
    with pytest.raises(ApprovalError, match="stale"):
        export_markdown(result, approval)


def test_approval_record_cannot_be_mutated_after_creation():
    result = run_workflow(SAMPLE, "sample.md")
    approval = approve_run(result, "EM")
    with pytest.raises(TypeError):
        approval.artifact_revisions[0] = ("unapproved", 0)
    with pytest.raises((TypeError, AttributeError)):
        approval.artifact_revisions.append(("unapproved", 0))


def test_approval_rejects_stale_upstream_artifact_revision():
    result = run_workflow(SAMPLE, "sample.md")
    schedule = result.artifacts["schedule"]
    plan = result.artifacts["engineering_plan"]
    result.artifacts["engineering_plan"] = plan.model_copy(
        update={"revision": plan.revision + 1}
    )
    with pytest.raises(ApprovalError, match="dependency is stale"):
        approve_run(result, "EM", [schedule.artifact_id])


def test_operations_store_contains_only_typed_metadata_and_returns_copies():
    result = run_workflow(SAMPLE, "sample.md")
    store = RunStore()
    for record in result.operational_records:
        store.append(record)
    records = store.list_records(result.run_id)
    assert records
    assert all(record.run_id == result.run_id for record in records)
    assert all("brd_content" not in record.__class__.model_fields for record in records)


def test_mock_external_integration_uses_typed_metadata_without_network_calls():
    result = run_workflow(SAMPLE, "sample.md")
    artifact = result.artifacts["engineering_plan"]
    response = MockIssueTracker().create_issue(
        MockIntegrationRequest(run_id=result.run_id, artifact=artifact)
    )
    assert response.status == "created"
    assert response.destination == "mock-issue-tracker"
    assert response.external_id.startswith("MOCK-")
