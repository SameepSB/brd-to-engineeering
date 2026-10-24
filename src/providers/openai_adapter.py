from __future__ import annotations

import json
import os

from src.contracts.schemas import ArtifactScore, JudgeAssessment


class OpenAIProvider:
    """Opt-in adapter. The OpenAI SDK is installed via the [openai] extra."""

    name = "openai"

    def __init__(self, model: str = "gpt-4.1-mini") -> None:
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY is required only when OPENAI mode is explicitly selected.")
        if os.getenv("BRD_ALLOW_EXTERNAL_CONTENT") != "1":
            raise ValueError(
                "Set BRD_ALLOW_EXTERNAL_CONTENT=1 only after confirming the configured endpoint "
                "is approved for the BRD data being processed."
            )
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError('Install the optional dependency with `pip install -e ".[openai]"`.') from exc
        self._client = OpenAI()
        self.generation_model = model
        self.evaluation_model = model

    def narrative(self, role: str, context: str) -> str:
        response = self._client.chat.completions.create(
            model=self.generation_model,
            messages=[
                {
                    "role": "system",
                    "content": "Return one concise, conservative sentence. Do not invent requirements or citations.",
                },
                {"role": "user", "content": f"Role: {role}\nContext:\n{context}"},
            ],
            temperature=0,
        )
        return response.choices[0].message.content or ""

    def judge(self, artifact_summary: str, deterministic_score: ArtifactScore) -> JudgeAssessment:
        response = self._client.chat.completions.create(
            model=self.evaluation_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Act as an independent evaluator for this artifact. Assess groundedness, completeness, "
                        "consistency, and actionability from the supplied artifact and evidence metadata. "
                        "Return a JSON object with numeric groundedness/completeness/consistency in [0,1], "
                        "actionability in [1,5], and a concise note. Do not invent evidence or change the rule score."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {"artifact": artifact_summary, "rule_score": deterministic_score.model_dump()},
                        ensure_ascii=False,
                    ),
                },
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        result = JudgeAssessment.model_validate_json(content)
        if result.artifact_id != deterministic_score.artifact_id:
            raise ValueError("LLM judge returned a score for the wrong artifact.")
        return result
