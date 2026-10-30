from __future__ import annotations

from typing import Any

from src.contracts.schemas import (
    AgentArtifact,
    ArchitectureArtifact,
    Claim,
    Citation,
    NormalizedBRD,
    PlanArtifact,
    PocArtifact,
    ScheduleArtifact,
    TechOption,
    TechStackArtifact,
    Uncertainty,
)
from src.providers.base import Provider
from src.retrieval.adapter import RetrievedChunk

SPECIALIST_ROLES = (
    "engineering_plan",
    "schedule",
    "solution_architect",
    "poc_planner",
    "tech_stack",
)


def build_artifact(
    role: str,
    run_id: str,
    brd: NormalizedBRD,
    uncertainties: list[Uncertainty],
    evidence: list[RetrievedChunk],
    provider: Provider,
    *,
    revision: int = 0,
    upstream_artifacts: dict[str, AgentArtifact] | None = None,
    critic_feedback: str | None = None,
) -> AgentArtifact:
    upstream_artifacts = upstream_artifacts or {}
    required_upstream = {
        "engineering_plan": (),
        "schedule": ("engineering_plan",),
        "solution_architect": ("engineering_plan", "schedule"),
        "poc_planner": ("engineering_plan", "solution_architect"),
        "tech_stack": ("engineering_plan", "solution_architect", "poc_planner"),
    }
    missing_upstream = set(required_upstream.get(role, ())) - set(upstream_artifacts)
    if missing_upstream:
        raise ValueError(f"{role} requires validated upstream artifacts: {sorted(missing_upstream)}")
    for upstream_role, artifact in upstream_artifacts.items():
        if artifact.role != upstream_role or artifact.run_id != run_id:
            raise ValueError(f"{role} received an invalid or cross-run {upstream_role} handoff.")
    evidence_citations = [_citation(chunk) for chunk in evidence[:3]]
    upstream_citations = [
        citation
        for artifact in upstream_artifacts.values()
        for citation in artifact.citations
    ]
    citations = list(
        {
            (item.source_id, item.chunk_id): item
            for item in [*evidence_citations, *upstream_citations]
        }.values()
    )[:3]
    requirement_ids = [item.requirement_id for item in brd.requirements]
    evidence_text = " ".join(chunk.text for chunk in evidence[:3])
    upstream_summary = "\n".join(
        f"{upstream_role}: {artifact.artifact_id} revision {artifact.revision}; "
        f"claims={'; '.join(claim.text for claim in artifact.claims)}; "
        f"plan_phases={getattr(artifact, 'phases', [])}; "
        f"schedule={getattr(artifact, 'timeline', [])}; "
        f"architecture_components={getattr(artifact, 'components', [])}"
        for upstream_role, artifact in upstream_artifacts.items()
    )
    if critic_feedback:
        upstream_summary += f"\nTargeted Critic correction: {critic_feedback}"
    narrative = provider.narrative(
        role,
        f"{brd.title}\n{evidence_text[:500]}\nValidated upstream context:\n{upstream_summary}",
    )
    claims = [
        Claim(
            text=f"{brd.title}: {narrative}",
            requirement_refs=requirement_ids[:2],
            citations=citations[:1],
        ),
        Claim(
            text=f"Scope remains limited to source requirements {', '.join(requirement_ids[:3])}.",
            requirement_refs=requirement_ids[:3],
            citations=citations[:1] if revision > 0 or role != "engineering_plan" else [],
        ),
    ]
    common: dict[str, Any] = {
        "run_id": run_id,
        "artifact_id": f"{run_id}-{role}",
        "revision": revision,
        "source_requirement_ids": requirement_ids,
        "upstream_artifact_ids": [item.artifact_id for item in upstream_artifacts.values()],
        "upstream_artifact_revisions": {
            role: item.revision for role, item in upstream_artifacts.items()
        },
        "citations": citations,
        "assumptions": sorted(
            {
                "All estimates and design choices are illustrative until approved by the Engineering Manager.",
                *(assumption for item in upstream_artifacts.values() for assumption in item.assumptions),
            }
        ),
        "uncertainties": _propagated_uncertainties(uncertainties, upstream_artifacts),
        "claims": claims,
        "covered_sections": brd.section_ids,
        "actionability": 3.0 if revision == 0 and role in {"engineering_plan", "solution_architect"} else 4.0,
        "retrieval_disclaimer": (
            "No usable knowledge evidence was retrieved; claims are provisional and cannot receive a Green badge."
            if not evidence
            else None
        ),
    }
    template = _template_body(role)
    generated = _generated_body(role, provider, brd, evidence, upstream_summary, template)
    body = {**template, **generated}
    if role == "engineering_plan":
        return PlanArtifact(**common, **body)
    if role == "schedule":
        return ScheduleArtifact(**common, **body)
    if role == "solution_architect":
        return ArchitectureArtifact(**common, **body)
    if role == "poc_planner":
        return PocArtifact(**common, **body)
    if role == "tech_stack":
        return TechStackArtifact(**common, **body)
    raise ValueError(f"Unsupported specialist role: {role}")


BODY_SPEC: dict[str, dict[str, str]] = {
    "engineering_plan": {
        "phases": "3-6 delivery phases specific to this BRD, each a short sentence",
        "milestones": "3-6 measurable milestones tied to the BRD",
        "risks": "3-6 concrete risks drawn from the BRD requirements and open questions",
        "team_composition": "roles with headcount, e.g. 'Backend engineer x2'",
        "reflection": "one sentence self-review of source coverage and assumptions",
    },
    "schedule": {
        "estimates": "effort per phase of the upstream plan, e.g. 'Discovery: 1-2 weeks'",
        "dependencies": "ordering constraints between phases or requirements",
        "timeline": "overall timeline statement, marked illustrative",
        "resource_allocation": "who is allocated to which phase",
    },
    "solution_architect": {
        "components": "system components specific to this BRD",
        "data_flows": "how data moves between the components",
        "nfr_mapping": "non-functional requirements from the BRD mapped to design choices",
    },
    "poc_planner": {
        "scope": "what the proof of concept includes and excludes",
        "modular_boundaries": "module boundaries matching the architecture components",
        "success_criteria": "measurable pass/fail criteria",
    },
    "tech_stack": {
        "options": (
            "2-3 stack options; each an object with string keys name, scalability, team_familiarity, "
            "integration_risk, cost, rationale"
        ),
    },
}


def _template_body(role: str) -> dict[str, Any]:
    if role == "engineering_plan":
        return {
            "phases": ["Discovery and validation", "Implementation", "Verification and rollout"],
            "milestones": ["Requirements approved", "Prototype validated", "Release readiness reviewed"],
            "risks": ["Unresolved requirements can change scope and estimates."],
            "team_composition": ["Engineering lead", "Application engineer", "Quality engineer"],
            "reflection": "Self-review confirms source requirement references and explicitly stated assumptions.",
        }
    if role == "schedule":
        return {
            "estimates": ["Discovery: 1–2 weeks", "Implementation: 2–4 weeks", "Validation: 1 week"],
            "dependencies": ["Requirements approval precedes implementation.", "Implementation precedes validation."],
            "timeline": ["Illustrative total: 4–7 weeks; re-estimate after scope approval."],
            "resource_allocation": ["Small cross-functional team; availability to be confirmed."],
        }
    if role == "solution_architect":
        return {
            "components": ["User interface", "Application service", "Data and integration boundary"],
            "data_flows": ["Validated requests flow through the application service to approved dependencies."],
            "nfr_mapping": ["Security: least privilege and secret management.", "Reliability: observable failures and recovery."],
        }
    if role == "poc_planner":
        return {
            "scope": ["Validate the highest-risk source-backed user journey.", "Use synthetic data and a local test environment."],
            "modular_boundaries": ["Presentation", "Core application logic", "External adapters"],
            "success_criteria": [
                "Complete the selected journey without a contract violation.",
                "Record reproducible results and unresolved risks for EM review.",
            ],
        }
    if role == "tech_stack":
        return {
            "options": [
                TechOption(
                    name="Python modular application",
                    scalability="Good for a bounded prototype; can split services later.",
                    team_familiarity="Confirm against the delivery team.",
                    integration_risk="Low with a small adapter surface.",
                    cost="Low prototype operating cost.",
                    rationale="Prioritizes the stated prototype workflow with minimal deployment overhead.",
                ),
                TechOption(
                    name="Managed cloud application",
                    scalability="Higher scale potential with more operational components.",
                    team_familiarity="Requires cloud platform expertise.",
                    integration_risk="Medium; provider and data-boundary review required.",
                    cost="Higher and usage-dependent.",
                    rationale="Consider only when scale and governance needs are validated.",
                ),
            ]
        }
    raise ValueError(f"Unsupported specialist role: {role}")


def _generated_body(
    role: str,
    provider: Provider,
    brd: NormalizedBRD,
    evidence: list[RetrievedChunk],
    upstream_summary: str,
    template: dict[str, Any],
) -> dict[str, Any]:
    """Ask the provider for the role's content; keep only fields that validate, else use the template."""
    generate = getattr(provider, "body", None)
    if generate is None:
        return {}
    requirements = "\n".join(f"{item.requirement_id}: {item.text}" for item in brd.requirements)
    evidence_text = "\n".join(f"[{chunk.chunk_id}] {chunk.text[:600]}" for chunk in evidence[:3])
    context = (
        f"BRD title: {brd.title}\nRequirements:\n{requirements}\n\n"
        f"Retrieved organizational evidence:\n{evidence_text}\n\nUpstream context:\n{upstream_summary}"
    )
    try:
        raw = generate(role, context, BODY_SPEC[role])
    except ValueError:
        return {}
    accepted: dict[str, Any] = {}
    for field, default in template.items():
        value = raw.get(field)
        if field == "reflection":
            if isinstance(value, str) and value.strip():
                accepted[field] = value.strip()
        elif field == "options":
            try:
                options = [TechOption.model_validate(item) for item in value]
            except (TypeError, ValueError):
                continue
            if 2 <= len(options) <= 3:
                accepted[field] = options
        elif isinstance(value, list) and value and all(isinstance(item, str) and item.strip() for item in value):
            accepted[field] = [item.strip() for item in value][:8]
    return accepted


def revise_artifact(
    artifact: AgentArtifact,
    evidence: list[RetrievedChunk],
    correction: str,
    *,
    provider: Provider | None = None,
    brd: NormalizedBRD | None = None,
    uncertainties: list[Uncertainty] | None = None,
    upstream_artifacts: dict[str, AgentArtifact] | None = None,
) -> AgentArtifact:
    """Apply a coordinator-directed, single-artifact revision."""
    if artifact.revision >= 2:
        return artifact
    if provider is None or brd is None:
        raise ValueError("A bounded specialist revision requires its provider and validated BRD input.")
    revised = build_artifact(
        artifact.role,
        artifact.run_id,
        brd,
        uncertainties or [],
        evidence,
        provider,
        revision=artifact.revision + 1,
        upstream_artifacts=upstream_artifacts,
        critic_feedback=correction,
    )
    if isinstance(revised, PlanArtifact):
        revised = revised.model_copy(
            update={"reflection": f"{revised.reflection} Revision addresses: {correction}"}
        )
    return revised


def _citation(chunk: RetrievedChunk) -> Citation:
    return Citation(
        source_id=chunk.source_id,
        chunk_id=chunk.chunk_id,
        source_locator=chunk.source_locator,
    )


def _propagated_uncertainties(
    source_uncertainties: list[Uncertainty],
    upstream_artifacts: dict[str, AgentArtifact],
) -> list[Uncertainty]:
    combined = [
        *source_uncertainties,
        *(item for artifact in upstream_artifacts.values() for item in artifact.uncertainties),
    ]
    return list({item.uncertainty_id: item for item in combined}.values())
