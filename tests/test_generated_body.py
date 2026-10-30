from __future__ import annotations

from src.orchestration.graph import run_workflow
from src.providers.deterministic import DeterministicProvider


class FakeLLMProvider(DeterministicProvider):
    name = "fake-llm"

    def body(self, role: str, context: str, fields: dict[str, str]) -> dict:
        assert "REQ-001" in context
        if role == "tech_stack":
            option = {
                "name": "FastAPI + Postgres",
                "scalability": "Horizontal",
                "team_familiarity": "High",
                "integration_risk": "Low",
                "cost": "Low",
                "rationale": "Fits REQ-001.",
            }
            return {"options": [option, {**option, "name": "Django"}]}
        if role == "schedule":
            return {"estimates": "not a list"}  # invalid, must fall back to the template
        return {name: [f"generated {role} {name}"] for name in fields}


def test_generated_body_is_used_and_invalid_fields_fall_back():
    sample = open("data/sample_brd.md", encoding="utf-8").read()
    result = run_workflow(sample, "sample_brd.md", provider=FakeLLMProvider())
    assert result.artifacts["engineering_plan"].phases == ["generated engineering_plan phases"]
    assert [o.name for o in result.artifacts["tech_stack"].options] == ["FastAPI + Postgres", "Django"]
    assert result.artifacts["schedule"].estimates[0].startswith("Discovery")
