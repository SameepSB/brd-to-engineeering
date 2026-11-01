---
title: 'Make generated artifact content easy to find'
type: 'feature'
created: '2026-11-01'
status: 'done'
route: 'oneshot'
route_source: 'auto'
review: 'quick'
review_source: 'auto'
lenses_ran: ['quick']
review_loop_iteration: 0
context: []
baseline_commit: 'a7868a3ed8cf4e6f59f65c4558c5b8c01ab053d1'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Generated plans, schedules, architecture, PoC scope, and stack recommendations are currently buried in the raw artifact JSON, so users cannot readily find the useful content in the Artifacts tab.

**Approach:** Render each artifact's role-specific fields as clearly labeled, readable sections in the UI while retaining the raw JSON view and downloadable report.

</frozen-after-approval>

## Implementation Notes

Oneshot route: added role-specific, labeled content sections to each artifact expander and moved the full JSON behind a collapsed "Raw artifact JSON" expander. Kept report downloads unchanged. Changed `app/main.py`. Syntax compilation succeeded and all 31 tests passed.

## Verification

**Commands:**
- `.\.venv\Scripts\python.exe -m py_compile app\main.py` — expected: success.
- `.\.venv\Scripts\python.exe -m pytest` — expected: all tests pass.

**Manual checks:**
- Run a workflow and inspect every artifact role in the Artifacts tab.
- Verify plan, schedule, architecture, PoC, and tech-stack content is visible without interpreting a JSON blob.
- Verify the existing JSON detail and artifacts download remain available.
