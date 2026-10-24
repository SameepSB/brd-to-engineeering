# Synthetic engineering standards

- Use least privilege, encrypted transport, and runtime secret stores.
- Keep business logic behind typed interfaces and validate data at each handoff.
- Add unit and end-to-end tests for inputs, errors, and approval gates.
- Prefer a modular monolith until workload, ownership, or availability data justifies distribution.
- Log identifiers, hashes, timings, scores, and guardrail events; never log source BRD text or credentials.
- Require human approval before exporting plans or invoking external integrations.
