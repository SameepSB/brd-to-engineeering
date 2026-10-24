from __future__ import annotations

from src.contracts.schemas import ArtifactScore, JudgeAssessment


class DeterministicProvider:
    """Offline provider with stable output for demos, tests, and Colab."""

    name = "deterministic-local"
    generation_model = "template-v1"
    evaluation_model = "heuristic-judge-v1"

    def narrative(self, role: str, context: str) -> str:
        return f"{role.replace('_', ' ').title()} grounded in the supplied requirements and retrieved evidence."

    def judge(self, artifact_summary: str, deterministic_score: ArtifactScore) -> JudgeAssessment:
        if deterministic_score.groundedness < 0.75:
            note = "Local heuristic judge flags an evidence gap; keep the decision provisional."
        elif deterministic_score.actionability < 4:
            note = "Local heuristic judge recommends a more actionable owner, deliverable, or acceptance measure."
        else:
            note = "Local heuristic judge finds the artifact reviewable against its cited evidence and rubric."
        return JudgeAssessment(
            artifact_id=deterministic_score.artifact_id,
            groundedness=deterministic_score.groundedness,
            completeness=deterministic_score.completeness,
            consistency=deterministic_score.consistency,
            actionability=deterministic_score.actionability,
            note=note,
        )
