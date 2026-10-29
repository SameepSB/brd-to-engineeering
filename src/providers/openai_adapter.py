from __future__ import annotations

import json
import os

from src.contracts.schemas import ArtifactScore, JudgeAssessment


class OpenAIProvider:
    """Opt-in adapter. The OpenAI SDK is installed via the [openai] extra."""

    name = "openai"
    api_key_env = "OPENAI_API_KEY"
    base_url: str | None = None
    default_model = "gpt-4.1-mini"

    def __init__(self, model: str | None = None) -> None:
        model = model or os.getenv("BRD_MODEL") or self.default_model
        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise ValueError(f"{self.api_key_env} is required only when {self.name} mode is explicitly selected.")
        if os.getenv("BRD_ALLOW_EXTERNAL_CONTENT") != "1":
            raise ValueError(
                "Set BRD_ALLOW_EXTERNAL_CONTENT=1 only after confirming the configured endpoint "
                "is approved for the BRD data being processed."
            )
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError('Install the optional dependency with `pip install -e ".[openai]"`.') from exc
        self._client = OpenAI(api_key=api_key, base_url=self.base_url)
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
        content = (response.choices[0].message.content or "{}").strip()
        if content.startswith("```"):
            content = content.strip("`").removeprefix("json").strip()
        data = json.loads(content)
        data["artifact_id"] = deterministic_score.artifact_id
        return JudgeAssessment.model_validate(data)
