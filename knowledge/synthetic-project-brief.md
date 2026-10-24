# Synthetic project brief: team intake

An internal team wants a lightweight intake service to standardize requests and provide a traceable review path. This is fabricated material for prototype evaluation only.

## Requirements
- A requester can submit an intake with a title, description, and desired completion window.
- The service validates required fields and returns clear errors for invalid submissions.
- Reviewers can see status changes and the owner assigned to each request.
- The system records status history with timestamps for audit and troubleshooting.

## Quality and constraints
- Access must be restricted to authenticated team members.
- The prototype must run locally without external services or credentials.
- A reviewer must approve any export of generated planning artifacts.
- Retention requirements are unclear and need Engineering Manager review.
