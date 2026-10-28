# Presenter guide: BRD-to-engineering prototype

## Pitch (30 seconds)
An Engineering Manager (EM) submits a BRD. Five specialist agents produce a plan, schedule, architecture, POC plan and tech stack. Every claim cites retrieved knowledge and a source requirement. A Critic scores the artifacts and sends weak ones back for revision (max 2 cycles). Nothing is exported unless the EM approves it. The message is **traceable and governed**, not "AI writes your plan".

## Pipeline
```
BRD (.md/.txt) -> parse_brd (REQ-ids, sections, TBD uncertainties)
  -> retrieve (local Qdrant over knowledge/*.md)
  -> engineering_plan -> schedule -> solution_architect -> poc_planner -> tech_stack
  -> critic --findings--> revise --> critic   |  clear --> evaluate (rules + judge)
  -> RunResult -> EM approval -> export (approved revisions only)
```

| Stage | Code | Key point |
|---|---|---|
| Ingestion | `src/ingestion/parser.py` | Rejects empty, non-text, null-byte or >2 MB input |
| Retrieval | `src/retrieval/adapter.py` | Adapter pattern: swap in hosted Qdrant for production |
| Specialists | `src/agents/roles.py` | Each runs only after its upstream artifacts exist |
| Handoff check | `_validate_handoff` in `src/orchestration/graph.py` | Rejects citations not retrieved in this run |
| Critic and badge | `src/agents/critic.py`, `src/evaluation/rubric.py` | Green = all 4 dimensions pass; Amber = 1 fails; Red = 2+ fail or overall < 3; empty retrieval is never Green |
| Approval | `src/storage/approval.py` | Immutable, hashed; stale revisions rejected |
| Ops log | `OperationalRecord` | Ids, hashes, scores, timings only; no raw BRD text |

## Demo script (about 8 minutes)
1. Show `data/sample_brd.md` and its TBD retention item (1 min).
2. Run `notebooks/demo.ipynb` on a Python 3.13+ kernel. Show the badge, then trace one claim to its citation and knowledge file (2 min).
3. Run `py -3.14 -m streamlit run app\main.py`. Show badges, assumptions, uncertainties and revisions. Approve one artifact, export, and show that unapproved ones are excluded (3 min).
4. Show the operational records and note there is no raw BRD text in them (1 min).
5. Run a BRD that matches no knowledge. The disclaimer appears and the badge is capped at Amber (1 min).

## Custom use cases from the board
| Request | Response |
|---|---|
| Try our BRD | Upload a `.md` or `.txt` in the UI, or `run_workflow(text, "name.md")`. Requirements should be bullets or lines under headings |
| Use our standards | Add markdown to `knowledge/`; it is re-indexed every run |
| Add a deliverable (for example security review) | Add the role in `roles.py`, `critic.py` and `graph.py`, plus a schema in `contracts/schemas.py` |
| Stricter or looser quality bar | Edit thresholds in `rubric.py` (groundedness 0.75, badge rules) |
| Real LLM | Set `OPENAI_API_KEY` in the environment and choose OpenAI in the UI |
| Different vector DB | Implement the same `retrieve()` interface as `LocalQdrantAdapter` |
| Confidential data | OpenAI mode needs an explicit endpoint-approval checkbox; logs hold hashes only |

## Be upfront
The default provider is **deterministic and offline**; its narrative text is template-based. The prototype proves the architecture (orchestration, contracts, grounding, critic loop, scoring, approval, logging), not LLM output quality. Production swaps in a real LLM, vector DB and durable storage behind the existing adapters.

## Likely questions
- **Is it using AI?** Not in the default mode; OpenAI is opt-in.
- **How is hallucination controlled?** Handoff validation, the groundedness score and the Critic loop.
- **How does it scale?** Replace the adapters; the graph and contracts stay the same.
- **Who is accountable?** The EM, through the approval gate.
