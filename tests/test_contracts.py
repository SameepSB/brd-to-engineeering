import pytest
from pydantic import ValidationError

from src.contracts.schemas import Citation, TechOption, TechStackArtifact
from src.ingestion.parser import parse_brd
from src.tools.contracts import ParseRequest
from src.tools.parser import parse_request


def test_shared_contracts_are_versioned_and_preserve_source_provenance():
    brd, _ = parse_brd("# Intake\n\n## Requirements\n- Keep an audit history.", "sample.md")
    requirement = brd.requirements[0]
    assert brd.contract_version == "1.0"
    assert requirement.requirement_id == "REQ-001"
    assert requirement.source_hash == brd.source_hash
    assert requirement.source_locator.endswith("#L4")


def test_citation_requires_resolvable_identity_fields():
    citation = Citation(source_id="KNOW-STD", chunk_id="KNOW-STD-1", source_locator="standards.md")
    assert citation.chunk_id == "KNOW-STD-1"
    with pytest.raises(ValidationError):
        Citation(source_id="KNOW-STD", chunk_id="KNOW-STD-1")


def test_tech_stack_contract_requires_two_or_three_comparable_options():
    option = TechOption(
        name="Python",
        scalability="bounded",
        team_familiarity="unknown",
        integration_risk="low",
        cost="low",
        rationale="prototype",
    )
    common = {
        "run_id": "run-test",
        "artifact_id": "artifact-test",
        "source_requirement_ids": ["REQ-001"],
        "claims": [{"text": "Claim", "requirement_refs": ["REQ-001"]}],
        "covered_sections": ["goal"],
        "actionability": 4,
        "options": [option],
    }
    with pytest.raises(ValidationError):
        TechStackArtifact(**common)


def test_contract_rejects_unexpected_fields():
    with pytest.raises(ValidationError):
        Citation(source_id="a", chunk_id="b", source_locator="c", raw_brd="must not be a contract field")


def test_typed_parser_tool_returns_normalized_contracts():
    response = parse_request(
        ParseRequest(filename="demo.md", content="# Goal\n\n- Approve each synthetic request.")
    )
    assert response.brd.requirements[0].requirement_id == "REQ-001"
