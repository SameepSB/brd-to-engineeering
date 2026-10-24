from __future__ import annotations

import hashlib

from src.tools.contracts import MockIntegrationRequest, MockIntegrationResponse


class MockIssueTracker:
    """No network access: demonstrate a typed integration with synthetic metadata."""

    destination = "mock-issue-tracker"

    def create_issue(self, request: MockIntegrationRequest) -> MockIntegrationResponse:
        digest = hashlib.sha256(
            f"{request.run_id}:{request.artifact.artifact_id}:{request.artifact.revision}".encode()
        ).hexdigest()[:10]
        return MockIntegrationResponse(
            external_id=f"MOCK-{digest.upper()}",
            destination=self.destination,
            status="created",
        )
