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

    def body(self, role: str, context: str, fields: dict[str, str]) -> dict:
        spec = "\n".join(f"- {name}: {description}" for name, description in fields.items())
        response = self._client.chat.completions.create(
            model=self.generation_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are the {role.replace('_', ' ')} agent in an engineering-planning workflow. "
                        "Return one JSON object with exactly the requested keys. Every list value must be a "
                        "list of short strings (except where an object list is specified). Base content only "
                        "on the supplied BRD requirements, retrieved evidence, and upstream context; be specific "
                        "to this BRD and reference requirement IDs where useful. Do not invent citations, "
                        "facts, or requirements. Mark estimates as illustrative and unknowns as TBD."
                    ),
                },
                {"role": "user", "content": f"Keys to return:\n{spec}\n\n{context}"},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        data = _parse_json(response.choices[0].message.content)
        if not isinstance(data, dict):
            raise ValueError("Provider body response was not a JSON object.")
        return data

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
        content = response.choices[0].message.content
        data = _parse_json(content)
        data["artifact_id"] = deterministic_score.artifact_id
        return JudgeAssessment.model_validate(data)


def _parse_json(content: str | None):
    text = (content or "{}").strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    return json.loads(text)
