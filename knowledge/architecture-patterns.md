# Architecture patterns

## Modular monolith
Prefer explicit internal boundaries and a single deployable unit when the team is small and scale is unproven. It limits operational overhead; split services only when ownership, load, or isolation requirements justify it.

## Event-driven integration
Use asynchronous events for independently owned work that tolerates eventual consistency. Include idempotency, retries, dead-letter handling, and traceable event identifiers.

## Retrieval-grounded application
Place a retrieval adapter between business logic and the vector store. Preserve source IDs and locators, record index metadata, and reject embedding-model mismatches rather than silently rebuilding.
