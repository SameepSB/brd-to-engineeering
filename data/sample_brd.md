# Synthetic BRD: engineering request review prototype

## Business goal
- Engineering managers need one traceable path from request intake to reviewed technical planning artifacts.
- The prototype should reduce repeated clarification work while keeping decisions visible to the Engineering Manager.

## Functional requirements
- A requester can submit a title, summary, and desired outcome using a Markdown or text BRD.
- The workflow validates input and maps each generated artifact claim to a source requirement or retrieved evidence.
- The Engineering Manager can review assumptions, uncertainties, citations, and revision history.
- Exports include only artifact revisions explicitly approved for the current run.

## Quality requirements
- Logs may contain identifiers, hashes, scores, and timings but must not contain raw BRD content or secrets.
- The demo must run offline with synthetic data and no cloud services.
- Local retrieval must show a clear disclaimer when no usable knowledge evidence is found.

## Constraints and open questions
- Use a coordinator-owned workflow and local Qdrant behind a retrieval adapter.
- The target retention period for real BRDs is TBD and requires Engineering Manager disposition.
