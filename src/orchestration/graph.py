from __future__ import annotations

import hashlib
import time
import uuid
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from src.agents.critic import review_artifacts
from src.agents.orchestrator import route
from src.agents.roles import build_artifact, revise_artifact
from src.contracts.schemas import (
    AgentArtifact,
    ArtifactScore,
    CriticResult,
    OperationalRecord,
    RunResult,
)
from src.evaluation.rubric import aggregate_badge
from src.ingestion.parser import parse_brd
from src.providers.base import Provider
from src.providers.deterministic import DeterministicProvider
from src.retrieval.adapter import LocalQdrantAdapter, RetrievedChunk, load_knowledge

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class WorkflowError(RuntimeError):
    """Raised when a validated handoff or coordinator transition fails."""


class WorkflowState(TypedDict, total=False):
    run_id: str
    filename: str
    brd_content: str
    normalized: Any
    uncertainties: list[Any]
    input_hash: str
    evidence: list[RetrievedChunk]
    retrieval_error: str | None
    artifacts: dict[str, AgentArtifact]
    completed_roles: list[str]
    transition_order: list[str]
    operational_records: list[OperationalRecord]
    revision_cycles: dict[str, int]
    revision_queue: list[str]
    critic: CriticResult
    revision_history: dict[str, list[ArtifactScore]]
    evaluation: dict[str, object]
    orchestrator: Any
    aggregate_badge: str


def run_workflow(
    content: str,
    filename: str = "synthetic-brd.md",
    *,
    provider: Provider | None = None,
    retriever: LocalQdrantAdapter | None = None,
) -> RunResult:
    """Validate, execute, evaluate, and return a complete local prototype run."""
    normalized, uncertainties = parse_brd(content, filename)
    workflow_started = time.perf_counter()
    active_provider = provider or DeterministicProvider()
    own_retriever = retriever is None
    active_retriever = retriever or LocalQdrantAdapter(
        load_knowledge(PROJECT_ROOT / "knowledge")
    )
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    initial_state: WorkflowState = {
        "run_id": run_id,
        "filename": filename,
        "brd_content": content,
        "normalized": normalized,
        "uncertainties": uncertainties,
        "input_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "evidence": [],
        "retrieval_error": None,
        "artifacts": {},
        "completed_roles": ["orchestrator"],
        "transition_order": ["input_validation", "retrieval"],
        "operational_records": [],
        "revision_cycles": {},
        "revision_queue": [],
        "revision_history": {},
        "evaluation": {},
    }
    try:
        state = _compile(active_provider, active_retriever).invoke(initial_state)
    finally:
        if own_retriever:
            active_retriever.close()

    artifacts = state["artifacts"]
    critic = state["critic"]
    records = state["operational_records"]
    score_by_role = {
        role: critic.scores[artifact.artifact_id]
        for role, artifact in artifacts.items()
    }
    score_by_artifact_revision = {
        artifact_id: {score.revision: score for score in scores}
        for artifact_id, scores in state["revision_history"].items()
    }
    records = [
        record.model_copy(
            update={
                "score": score_by_artifact_revision.get(record.output_id, {}).get(
                    record.revision_count,
                    score_by_role[record.agent_id],
                ).overall,
            }
        )
        if record.agent_id in score_by_role
        else record
        for record in records
    ]
    if state.get("retrieval_error"):
        records.append(
            OperationalRecord(
                run_id=run_id,
                agent_id="retrieval",
                input_hash=state["input_hash"],
                output_id="retrieval-empty",
                provider=active_provider.name,
                model=active_provider.generation_model,
                duration_ms=0,
                guardrail_events=["retrieval_error"],
            )
        )
    orchestrator_result = route(
        run_id,
        list(state["completed_roles"]),
        list(state["transition_order"]),
        guardrail_events=(
            ["retrieval_error"] if state.get("retrieval_error") else
            ["no_usable_evidence"] if not state["evidence"] else []
        ),
        errors=[state["retrieval_error"]] if state.get("retrieval_error") else [],
    )
    evidence_disclaimer = (
        "No usable knowledge evidence was retrieved. Treat all outputs as provisional; no artifact may be Green."
        if not state["evidence"]
        else None
    )
    records.append(
        OperationalRecord(
            run_id=run_id,
            agent_id="orchestrator",
            input_hash=state["input_hash"],
            output_id=orchestrator_result.artifact_id,
            provider=active_provider.name,
            model=active_provider.generation_model,
            duration_ms=_elapsed(workflow_started),
            retrieved_chunk_ids=[chunk.chunk_id for chunk in state["evidence"]],
            score=sum(score.overall for score in critic.scores.values())
            / max(1, len(critic.scores)),
            guardrail_events=orchestrator_result.guardrail_events,
            revision_count=max(state["revision_cycles"].values(), default=0),
        )
    )
    return RunResult(
        run_id=run_id,
        input_hash=state["input_hash"],
        normalized_brd=state["normalized"],
        artifacts=artifacts,
        critic=critic,
        orchestrator=orchestrator_result,
        operational_records=records,
        revision_history=state["revision_history"],
        evaluation=state["evaluation"],
        retrieval_metadata=dict(
            getattr(
                active_retriever,
                "metadata",
                {"store": "custom-adapter", "adapter": type(active_retriever).__name__},
            )
        ),
        aggregate_badge=aggregate_badge(
            list(critic.scores.values()), retrieval_empty=not state["evidence"]
        ),
        evidence_disclaimer=evidence_disclaimer,
    )


def _compile(provider: Provider, retriever: LocalQdrantAdapter):
    def retrieve(state: WorkflowState) -> dict[str, Any]:
        start = time.perf_counter()
        brd = state["normalized"]
        query = f"{brd.title} " + " ".join(item.text for item in brd.requirements)
        retrieval_error = None
        try:
            evidence = retriever.retrieve(query)
        except (ValueError, RuntimeError) as exc:
            evidence = []
            retrieval_error = f"{type(exc).__name__}: retrieval adapter failed"
        elapsed = _elapsed(start)
        record = _operational_record(
            state,
            "retrieval",
            "retrieval-result",
            provider,
            elapsed,
            [chunk.chunk_id for chunk in evidence],
            ["retrieval_error"] if retrieval_error else (
                ["no_usable_evidence"] if not evidence else []
            ),
        )
        return {
            "evidence": evidence,
            "retrieval_error": retrieval_error,
            "operational_records": [*state["operational_records"], record],
            "transition_order": [*state["transition_order"], "retrieve_evidence"],
        }

    def specialist(role: str):
        def run(state: WorkflowState) -> dict[str, Any]:
            start = time.perf_counter()
            artifact = build_artifact(
                role,
                state["run_id"],
                state["normalized"],
                state["uncertainties"],
                state["evidence"],
                provider,
                upstream_artifacts={
                    upstream_role: state["artifacts"][upstream_role]
                    for upstream_role in _upstream_roles(role)
                },
            )
            _validate_handoff(artifact, state["normalized"].requirements, state["evidence"])
            event = ["no_usable_evidence"] if not state["evidence"] else []
            record = _operational_record(
                state,
                role,
                artifact.artifact_id,
                provider,
                _elapsed(start),
                [chunk.chunk_id for chunk in state["evidence"]],
                event,
                artifact.revision,
            )
            return {
                "artifacts": {**state["artifacts"], role: artifact},
                "completed_roles": [*state["completed_roles"], role],
                "operational_records": [*state["operational_records"], record],
                "transition_order": [*state["transition_order"], role],
            }

        return run

    def critic(state: WorkflowState) -> dict[str, Any]:
        start = time.perf_counter()
        result, scores = review_artifacts(
            state["run_id"],
            state["artifacts"],
            state["normalized"].section_ids,
            {chunk.chunk_id for chunk in state["evidence"]},
            state["revision_cycles"],
        )
        history = {key: list(value) for key, value in state["revision_history"].items()}
        for score in scores.values():
            artifact = next(a for a in state["artifacts"].values() if a.artifact_id == score.artifact_id)
            previous = history.setdefault(score.artifact_id, [])
            if not previous or previous[-1].revision != artifact.revision:
                previous.append(score)

        findings_by_artifact = {finding.originating_artifact_id for finding in result.findings}
        queue = [
            artifact_id
            for artifact_id in findings_by_artifact
            if state["revision_cycles"].get(artifact_id, 0) < 2
        ]
        result.revision_cycles = dict(state["revision_cycles"])
        critic_record = _operational_record(
            state,
            "critic",
            result.artifact_id,
            provider,
            _elapsed(start),
            [chunk.chunk_id for chunk in state["evidence"]],
            ["critic_findings_remaining" if result.findings else "critic_clear"],
            max(state["revision_cycles"].values(), default=0),
        ).model_copy(
            update={
                "model": provider.evaluation_model,
                "score": sum(score.overall for score in scores.values()) / max(1, len(scores)),
            }
        )
        return {
            "critic": result,
            "revision_queue": sorted(queue),
            "revision_history": history,
            "completed_roles": list(dict.fromkeys([*state["completed_roles"], "critic"])),
            "operational_records": [*state["operational_records"], critic_record],
            "transition_order": [*state["transition_order"], "critic_review"],
        }

    def revise(state: WorkflowState) -> dict[str, Any]:
        start = time.perf_counter()
        queue = list(state["revision_queue"])
        artifact_id = queue.pop(0)
        role, artifact = next(
            (role, item)
            for role, item in state["artifacts"].items()
            if item.artifact_id == artifact_id
        )
        feedback = next(
            finding.correction
            for finding in state["critic"].findings
            if finding.originating_artifact_id == artifact_id
        )
        updated = revise_artifact(
            artifact,
            state["evidence"],
            feedback,
            provider=provider,
            brd=state["normalized"],
            uncertainties=state["uncertainties"],
            upstream_artifacts={
                upstream_role: state["artifacts"][upstream_role]
                for upstream_role in _upstream_roles(role)
            },
        )
        _validate_handoff(updated, state["normalized"].requirements, state["evidence"])
        cycles = dict(state["revision_cycles"])
        cycles[artifact_id] = cycles.get(artifact_id, 0) + 1
        record = _operational_record(
            state,
            role,
            updated.artifact_id,
            provider,
            _elapsed(start),
            [chunk.chunk_id for chunk in state["evidence"]],
            ["critic_revision"],
            updated.revision,
        )
        return {
            "artifacts": {**state["artifacts"], role: updated},
            "revision_cycles": cycles,
            "revision_queue": queue,
            "operational_records": [*state["operational_records"], record],
            "transition_order": [*state["transition_order"], f"revise:{role}"],
        }

    def evaluate(state: WorkflowState) -> dict[str, Any]:
        start = time.perf_counter()
        judge_notes: dict[str, str] = {}
        judge_scores: dict[str, dict[str, object]] = {}
        final_artifacts: dict[str, AgentArtifact] = {}
        for role, artifact in state["artifacts"].items():
            score = state["critic"].scores[artifact.artifact_id]
            assessment = provider.judge(artifact.model_dump_json(), score)
            judge_notes[artifact.artifact_id] = assessment.note
            judge_scores[artifact.artifact_id] = assessment.model_dump(mode="json")
            final_artifacts[role] = artifact.model_copy(update={"badge": score.badge})
        evaluation: dict[str, object] = {
            "rubric_version": "1.0",
            "methods": ["deterministic_rules", "provider_judge"],
            "rule_scores": {
                key: score.model_dump(mode="json") for key, score in state["critic"].scores.items()
            },
            "judge_scores": judge_scores,
            "judge_notes": judge_notes,
            "judge_model": provider.evaluation_model,
        }
        record = _operational_record(
            state,
            "evaluation",
            f"{state['run_id']}-evaluation",
            provider,
            _elapsed(start),
            [chunk.chunk_id for chunk in state["evidence"]],
            [],
            score=sum(score.overall for score in state["critic"].scores.values())
            / max(1, len(state["critic"].scores)),
        ).model_copy(update={"model": provider.evaluation_model})
        return {
            "artifacts": final_artifacts,
            "evaluation": evaluation,
            "operational_records": [*state["operational_records"], record],
            "transition_order": [*state["transition_order"], "evaluation"],
        }

    graph = StateGraph(WorkflowState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("engineering_plan", specialist("engineering_plan"))
    graph.add_node("schedule", specialist("schedule"))
    graph.add_node("solution_architect", specialist("solution_architect"))
    graph.add_node("poc_planner", specialist("poc_planner"))
    graph.add_node("tech_stack", specialist("tech_stack"))
    graph.add_node("critic", critic)
    graph.add_node("revise", revise)
    graph.add_node("evaluate", evaluate)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "engineering_plan")
    graph.add_edge("engineering_plan", "schedule")
    graph.add_edge("schedule", "solution_architect")
    graph.add_edge("solution_architect", "poc_planner")
    graph.add_edge("poc_planner", "tech_stack")
    graph.add_edge("tech_stack", "critic")
    graph.add_conditional_edges("critic", _review_route, {"revise": "revise", "evaluate": "evaluate"})
    graph.add_edge("revise", "critic")
    graph.add_edge("evaluate", END)
    return graph.compile()


def _review_route(state: WorkflowState) -> str:
    return "revise" if state.get("revision_queue") else "evaluate"


def _upstream_roles(role: str) -> tuple[str, ...]:
    return {
        "engineering_plan": (),
        "schedule": ("engineering_plan",),
        "solution_architect": ("engineering_plan", "schedule"),
        "poc_planner": ("engineering_plan", "solution_architect"),
        "tech_stack": ("engineering_plan", "solution_architect", "poc_planner"),
    }[role]


def _validate_handoff(artifact: AgentArtifact, requirements: list[Any], evidence: list[RetrievedChunk]) -> None:
    requirement_ids = {item.requirement_id for item in requirements}
    evidence_citations = {
        (item.source_id, item.chunk_id, item.source_locator)
        for item in evidence
    }
    if not set(artifact.source_requirement_ids).issubset(requirement_ids):
        raise WorkflowError(f"{artifact.role} referenced an unknown source requirement.")
    for claim in artifact.claims:
        if not set(claim.requirement_refs).issubset(requirement_ids):
            raise WorkflowError(f"{artifact.role} claim referenced an unknown requirement.")
        if any(
            (citation.source_id, citation.chunk_id, citation.source_locator) not in evidence_citations
            for citation in claim.citations
        ):
            raise WorkflowError(f"{artifact.role} cited evidence that is not in this run's retrieved set.")
    for citation in artifact.citations:
        if (citation.source_id, citation.chunk_id, citation.source_locator) not in evidence_citations:
            raise WorkflowError(f"{artifact.role} included an unresolved citation.")
    for uncertainty in artifact.uncertainties:
        if not set(uncertainty.source_requirement_ids).issubset(requirement_ids):
            raise WorkflowError(f"{artifact.role} propagated an uncertainty with an invalid requirement reference.")


def _operational_record(
    state: WorkflowState,
    agent: str,
    output_id: str,
    provider: Provider,
    duration_ms: int,
    retrieved_ids: list[str],
    events: list[str],
    revision_count: int = 0,
    score: float | None = None,
) -> OperationalRecord:
    return OperationalRecord(
        run_id=state["run_id"],
        agent_id=agent,
        input_hash=state["input_hash"],
        output_id=output_id,
        provider=provider.name,
        model=provider.generation_model,
        duration_ms=duration_ms,
        retrieved_chunk_ids=retrieved_ids,
        score=score,
        guardrail_events=events,
        revision_count=revision_count,
    )


def _elapsed(start: float) -> int:
    return max(0, round((time.perf_counter() - start) * 1000))
