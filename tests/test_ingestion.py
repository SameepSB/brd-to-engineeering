import pytest

from src.ingestion.parser import InputValidationError, parse_brd
from pathlib import Path


def test_markdown_requirements_are_normalized_with_source_links_and_uncertainty():
    brd, uncertainties = parse_brd(
        "# Intake\n\n## Functional requirements\n- A reviewer approves each request.\n\n## Open questions\n- Retention is TBD.",
        "intake.md",
    )
    assert brd.title == "Intake"
    assert set(brd.section_ids) == {"intake", "functional-requirements", "open-questions"}
    assert [item.requirement_id for item in brd.requirements] == ["REQ-001", "REQ-002"]
    assert all(item.source_hash == brd.source_hash for item in brd.requirements)
    assert uncertainties[0].type == "ambiguity"
    assert uncertainties[0].source_requirement_ids == ["REQ-002"]


@pytest.mark.parametrize("content, filename", [("", "empty.md"), ("\x00bad", "bad.txt")])
def test_empty_or_malformed_brd_is_rejected(content, filename):
    with pytest.raises(InputValidationError):
        parse_brd(content, filename)


def test_unsupported_file_is_rejected_before_processing():
    with pytest.raises(InputValidationError, match="Only Markdown"):
        parse_brd("A valid-looking source requirement.", "requirements.pdf")


def test_section_only_document_is_invalid():
    with pytest.raises(InputValidationError, match="no requirements"):
        parse_brd("# Title\n\n## Scope\n", "scope.md")


def test_contradictory_source_requirements_are_carried_as_uncertainty():
    _, uncertainties = parse_brd(
        "# Access\n\n## Requirements\n- Access is only for authenticated users.\n- Anonymous users must be able to use the reviewer actions.",
        "access.md",
    )
    assert any(item.type == "contradiction" and len(item.source_requirement_ids) == 2 for item in uncertainties)


def test_size_limit_is_explicit():
    with pytest.raises(InputValidationError, match="2 MB"):
        parse_brd("x" * 2_000_001, "large.txt")


def test_versioned_edge_dataset_detects_missing_nfr_contradiction_and_ambiguity():
    root = Path(__file__).resolve().parents[1]
    brd_text = (root / "data" / "evaluation" / "edge-cases.md").read_text(encoding="utf-8")
    _, uncertainties = parse_brd(brd_text, "edge-cases.md")
    kinds = {item.type for item in uncertainties}
    assert {"question", "contradiction", "ambiguity"}.issubset(kinds)
