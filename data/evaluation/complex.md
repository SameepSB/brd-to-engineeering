# Complex synthetic BRD

## Goal
- Validate an internal planning workflow that connects intake, knowledge retrieval, and approved exports.

## Functional requirements
- Normalize source requirements from Markdown and text inputs.
- Retrieve source-linked engineering guidance and preserve citation IDs.
- Generate dependency-ordered plans, estimates, architecture, PoC scope, and technology comparisons.
- Route bounded critic revisions to the originating specialist.
- Bind approval to the exact revisions being exported.

## Non-functional requirements
- Do not log source BRD content or secrets.
- Record structured operational metrics and make failed handoffs visible.
- Rebuild the local index when its embedding metadata changes.
