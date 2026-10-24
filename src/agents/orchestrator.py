from src.contracts.schemas import OrchestratorResult, Role


def route(
    run_id: str,
    completed_roles: list[Role],
    transition_order: list[str],
    guardrail_events: list[str] | None = None,
    errors: list[str] | None = None,
) -> OrchestratorResult:
    return OrchestratorResult(
        run_id=run_id,
        artifact_id=f"{run_id}-orchestrator",
        completed_roles=completed_roles,
        transition_order=transition_order,
        status="completed",
        errors=errors or [],
        guardrail_events=guardrail_events or [],
    )
