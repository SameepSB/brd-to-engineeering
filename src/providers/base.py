from __future__ import annotations

from typing import Protocol

from src.contracts.schemas import ArtifactScore, JudgeAssessment


class Provider(Protocol):
    name: str
    generation_model: str
    evaluation_model: str

    def narrative(self, role: str, context: str) -> str: ...

    def judge(self, artifact_summary: str, deterministic_score: ArtifactScore) -> JudgeAssessment: ...
