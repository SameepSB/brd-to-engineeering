# Architecture and agent contracts

## Coordinator-owned flow

LangGraph owns a single run state and executes one dependency-ordered graph:

`validate/normalize → retrieve → engineering plan → schedule → solution architecture → PoC plan → technology comparison → critic/revision loop → evaluation`.

Schedule consumes the validated plan; architecture consumes the plan; PoC and technology options consume the validated upstream artifacts. The Critic reviews all five specialist outputs. Agents are pure role-specific builders: they do not call other agents or write shared state. The Critic can request targeted revisions, at most two per artifact; at the cap, findings remain attached for EM disposition.

## Contract version 1.0

All handoffs are Pydantic models with unknown fields rejected:

| Role | Contract | Principal output |
| --- | --- | --- |
| Orchestrator | `OrchestratorResult` | Run ID, completed roles, transition order, status, errors and guardrails |
| Engineering Plan Generator | `PlanArtifact` | Phases, milestones, risks, team, required self-reflection |
| Schedule Estimator | `ScheduleArtifact` | Estimates, dependencies, timeline, resource allocation |
| Solution Architect | `ArchitectureArtifact` | Components, data flows, NFR mapping |
| PoC Planner | `PocArtifact` | Scope, modular boundaries, measurable success criteria |
| Tech Stack Recommender | `TechStackArtifact` | Two options compared on scalability, familiarity, integration risk and cost |
| Critic | `CriticResult` | Versioned rubric scores, specific findings, origin artifact and revision counts |

Every artifact carries stable run/artifact IDs, source requirement IDs, citations, assumptions, uncertainties, section coverage, badge, upstream artifact revision identities, and its own revision. The run retains normalized source requirements for ID resolution. A citation is the triple `source_id`, `chunk_id`, `source_locator`; the coordinator rejects unresolved citation and requirement IDs at every handoff. Uncertainty types are ambiguity, contradiction, assumption, and question.

## Tool and provider boundaries

`src/tools` exposes typed parser, retrieval, export, and mock issue-tracker boundaries. `LocalQdrantAdapter` hides the vector store and records store, collection, embedding model/dimensions, and corpus version. The offline feature-hash embedding is a reproducibility baseline, not a semantic embedding model or production catalog candidate. The default provider is deterministic and credential-free. OpenAI is optional, selected explicitly, and requires both an API key and explicit confirmation that the configured endpoint is approved for the data.

## Production boundary

This is an ephemeral single-user prototype, not a production service. It does not implement Azure deployment, multi-user persistence, confidential data retention, identity/access management, or scale guarantees. ChromaDB is not included or deployed.
