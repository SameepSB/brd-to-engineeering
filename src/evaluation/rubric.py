from __future__ import annotations

from src.contracts.schemas import AgentArtifact, ArtifactScore


def score_artifact(
    artifact: AgentArtifact,
    section_ids: list[str],
    retrieved_chunk_ids: set[str],
    cross_artifact_issues: list[str] | None = None,
) -> ArtifactScore:
    non_trivial = [claim for claim in artifact.claims if claim.non_trivial]
    supported = [
        claim
        for claim in non_trivial
        if any(citation.chunk_id in retrieved_chunk_ids for citation in claim.citations)
    ]
    groundedness = len(supported) / len(non_trivial) if non_trivial else 0.0
    covered = set(artifact.covered_sections)
    missing = sorted(set(section_ids) - covered)
    completeness = (len(set(section_ids) & covered) / len(set(section_ids))) if section_ids else 1.0
    issues = cross_artifact_issues or []
    consistency = 1.0 if not issues else 0.0
    overall = round((groundedness * 5 + completeness * 5 + consistency * 5 + artifact.actionability) / 4, 2)
    failed_dimensions = sum(
        (
            groundedness < 0.75,
            completeness < 1,
            consistency < 1,
            artifact.actionability < 4,
        )
    )
    if failed_dimensions >= 2 or overall < 3:
        badge = "Red"
    elif failed_dimensions == 1 or overall < 4:
        badge = "Amber"
    else:
        badge = "Green"
    if artifact.retrieval_disclaimer and not retrieved_chunk_ids and badge == "Green":
        badge = "Amber"
    return ArtifactScore(
        artifact_id=artifact.artifact_id,
        revision=artifact.revision,
        groundedness=round(groundedness, 3),
        completeness=round(completeness, 3),
        consistency=round(consistency, 3),
        actionability=artifact.actionability,
        overall=overall,
        badge=badge,
        unsupported_claims=[claim.text for claim in non_trivial if claim not in supported],
        missing_sections=missing,
        cross_artifact_issues=issues,
        retrieval_empty=not retrieved_chunk_ids,
    )


def aggregate_badge(scores: list[ArtifactScore], retrieval_empty: bool = False) -> str:
    if not scores:
        return "Red"
    rank = {"Green": 0, "Amber": 1, "Red": 2}
    badge = max((score.badge for score in scores), key=rank.get)
    if retrieval_empty and badge == "Green":
        return "Amber"
    return badge
