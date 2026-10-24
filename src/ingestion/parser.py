from __future__ import annotations

import hashlib
import re
from pathlib import PurePosixPath

from src.contracts.schemas import NormalizedBRD, SourceRequirement, Uncertainty


class InputValidationError(ValueError):
    """Raised when an uploaded BRD cannot safely enter the workflow."""


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def parse_brd(
    content: str,
    filename: str = "requirements.md",
) -> tuple[NormalizedBRD, list[Uncertainty]]:
    suffix = PurePosixPath(filename.replace("\\", "/")).suffix.lower()
    if suffix not in {".md", ".txt"}:
        raise InputValidationError("Only Markdown (.md) and plain text (.txt) BRDs are supported.")
    if not isinstance(content, str) or not content.strip():
        raise InputValidationError("The BRD is empty. Provide non-empty Markdown or text.")
    if "\x00" in content:
        raise InputValidationError("The BRD contains a null byte and cannot be parsed.")
    if len(content.encode("utf-8")) > 2_000_000:
        raise InputValidationError("The BRD exceeds the 2 MB prototype limit.")

    input_hash = sha256_text(content)
    lines = content.splitlines()
    headings: list[tuple[int, str]] = []
    for number, line in enumerate(lines, start=1):
        match = re.match(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if match:
            headings.append((number, match.group(2).strip()))
    title = headings[0][1] if headings else PurePosixPath(filename).stem.replace("-", " ").title()

    section_for_line = "overview"
    section_ids: list[str] = []
    requirements: list[SourceRequirement] = []
    uncertainties: list[Uncertainty] = []
    ordinal = 0

    for number, line in enumerate(lines, start=1):
        match = re.match(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if match:
            section_for_line = _slug(match.group(2))
            if section_for_line not in section_ids:
                section_ids.append(section_for_line)
            continue
        text = _requirement_text(line)
        if not text:
            continue
        ordinal += 1
        req_id = f"REQ-{ordinal:03d}"
        requirements.append(
            SourceRequirement(
                requirement_id=req_id,
                text=text,
                section_id=section_for_line,
                source_locator=f"{filename}#L{number}",
                source_hash=input_hash,
            )
        )
        lowered = text.lower()
        kind = None
        if any(term in lowered for term in ("tbd", "to be determined", "maybe", "might", "unclear", "approximately")):
            kind = "ambiguity"
        elif "?" in text or lowered.startswith(("should we", "can we", "is it")):
            kind = "question"
        if kind:
            uncertainties.append(
                Uncertainty(
                    uncertainty_id=f"UNC-{len(uncertainties) + 1:03d}",
                    type=kind,
                    description=text,
                    source_requirement_ids=[req_id],
                    owner="Engineering Manager",
                )
            )

    if not headings and not requirements:
        raise InputValidationError("The BRD has no recognizable title, sections, or requirements.")
    if not requirements:
        raise InputValidationError("The BRD has sections but no requirements to process.")
    if not section_ids:
        section_ids = ["overview"]
    has_nfr_section = any(
        not section_id.startswith("missing-")
        and any(term in section_id for term in ("non-functional", "quality", "nfr"))
        for section_id in section_ids
    )
    if not has_nfr_section:
        uncertainties.append(
            Uncertainty(
                uncertainty_id=f"UNC-{len(uncertainties) + 1:03d}",
                type="question",
                description="No explicit non-functional requirements section was detected; confirm quality targets with the Engineering Manager.",
                source_requirement_ids=[],
                owner="Engineering Manager",
            )
        )
    uncertainties.extend(_find_contradictions(requirements, len(uncertainties)))

    try:
        normalized = NormalizedBRD(
            source_name=filename,
            source_hash=input_hash,
            title=title,
            section_ids=section_ids,
            requirements=requirements,
        )
    except ValueError as exc:
        raise InputValidationError(f"BRD validation failed: {exc}") from exc
    return normalized, uncertainties


def _requirement_text(line: str) -> str | None:
    stripped = line.strip()
    if not stripped:
        return None
    bullet = re.match(r"^(?:[-*+]\s+|\d+[.)]\s+)(.+)$", stripped)
    if bullet:
        value = bullet.group(1).strip()
        return value if len(value) >= 6 else None
    if stripped.startswith("#") or stripped.startswith("```") or stripped.startswith("|"):
        return None
    if len(stripped) >= 24 and not stripped.startswith(("<!--", ">")):
        return stripped
    return None


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "section"


def _find_contradictions(requirements: list[SourceRequirement], offset: int) -> list[Uncertainty]:
    opposing_pairs = (
        (
            ("only authenticated", "authenticated users only", "only for authenticated", "only to authenticated"),
            ("anonymous", "unauthenticated"),
        ),
        (("must not", "cannot"), ("must ", "must be", "must allow")),
        (("deny", "disable", "prohibit"), ("allow", "enable", "permit")),
    )
    found: list[Uncertainty] = []
    for left_index, left in enumerate(requirements):
        left_text = left.text.lower()
        for right in requirements[left_index + 1 :]:
            right_text = right.text.lower()
            for left_terms, right_terms in opposing_pairs:
                if any(term in left_text for term in left_terms) and any(
                    term in right_text for term in right_terms
                ):
                    found.append(
                        Uncertainty(
                            uncertainty_id=f"UNC-{offset + len(found) + 1:03d}",
                            type="contradiction",
                            description=f"Potential conflict between {left.requirement_id} and {right.requirement_id}.",
                            source_requirement_ids=[left.requirement_id, right.requirement_id],
                            owner="Engineering Manager",
                        )
                    )
                    break
    return found
