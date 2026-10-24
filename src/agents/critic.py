from __future__ import annotations

from src.contracts.schemas import (
    AgentArtifact,
    ArtifactScore,
    CriticFinding,
    CriticResult,
)
from src.evaluation.rubric import score_artifact


REQUIRED_UPSTREAM = {
    "schedule": ("engineering_plan",),
    "solution_architect": ("engineering_plan", "schedule"),
    "poc_planner": ("engineering_plan", "solution_architect"),
    "tech_stack": ("engineering_plan", "solution_architect", "poc_planner"),
}


def review_artifacts(
    run_id: str,
    artifacts: dict[str, AgentArtifact],
    section_ids: list[str],
    retrieved_chunk_ids: set[str],
    revision_cycles: dict[str, int],
) -> tuple[CriticResult, dict[str, ArtifactScore]]:
    scores: dict[str, ArtifactScore] = {}
    findings: list[CriticFinding] = []
    by_artifact_id = {artifact.artifact_id: artifact for artifact in artifacts.values()}
    for role, artifact in artifacts.items():
        issues = _consistency_issues(role, artifact, artifacts, by_artifact_id)
        score = score_artifact(artifact, section_ids, retrieved_chunk_ids, issues)
        scores[artifact.artifact_id] = score
        if score.groundedness < 0.75:
            findings.append(
                CriticFinding(
                    originating_artifact_id=artifact.artifact_id,
                    dimension="groundedness",
                    issue=f"Only {score.groundedness:.0%} of non-trivial claims cite retrieved evidence.",
                    correction="Cite retrieved evidence for each non-trivial claim or label it as an assumption.",
                )
            )
        if score.completeness < 1:
            findings.append(
                CriticFinding(
                    originating_artifact_id=artifact.artifact_id,
                    dimension="completeness",
                    issue="One or more BRD sections are not covered.",
                    correction="Cover each source BRD section or record why it is out of scope.",
                )
            )
        if score.consistency < 1:
            findings.append(
                CriticFinding(
                    originating_artifact_id=artifact.artifact_id,
                    dimension="consistency",
                    issue="A cross-artifact contradiction needs EM disposition.",
                    correction="Align this artifact with the validated upstream plan and schedule.",
                )
            )
        if score.actionability < 4:
            findings.append(
                CriticFinding(
                    originating_artifact_id=artifact.artifact_id,
                    dimension="actionability",
                    issue=f"Actionability is {score.actionability:.1f}/5.",
                    correction="Add actionable owners, deliverables, dependencies, or acceptance measures.",
                )
            )
    badges = [score.badge for score in scores.values()]
    aggregate_badge = max(badges, key={"Green": 0, "Amber": 1, "Red": 2}.get) if badges else "Red"
    result = CriticResult(
        run_id=run_id,
        artifact_id=f"{run_id}-critic",
        scores=scores,
        findings=findings,
        revision_cycles=revision_cycles,
        badge=aggregate_badge,
    )
    return result, scores


def _consistency_issues(
    role: str,
    artifact: AgentArtifact,
    artifacts: dict[str, AgentArtifact],
    by_artifact_id: dict[str, AgentArtifact],
) -> list[str]:
    expected_roles = REQUIRED_UPSTREAM.get(role, ())
    actual_ids = set(artifact.upstream_artifact_ids)
    issues = [
        f"Missing validated upstream artifact: {upstream_role}."
        for upstream_role in expected_roles
        if upstream_role not in artifacts
        or artifacts[upstream_role].artifact_id not in actual_ids
        or artifacts[upstream_role].artifact_id not in by_artifact_id
    ]
    for upstream_role in expected_roles:
        current = artifacts.get(upstream_role)
        if current is not None and artifact.upstream_artifact_revisions.get(upstream_role) != current.revision:
            issues.append(
                f"Artifact was built against stale {upstream_role} revision "
                f"{artifact.upstream_artifact_revisions.get(upstream_role)}; current revision is {current.revision}."
            )
    if role == "schedule" and "engineering_plan" in artifacts:
        plan = artifacts["engineering_plan"]
        schedule_text = " ".join(artifact.dependencies + artifact.timeline).lower()
        if "implementation" in " ".join(plan.phases).lower() and "implementation" not in schedule_text:
            issues.append("Schedule does not align with the plan's implementation phase.")
    return issues
