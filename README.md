# BRD-to-engineering prototype

An offline-ready prototype that turns a synthetic Business Requirements Document (BRD) into cited engineering artifacts, reviews them with a bounded Critic loop, evaluates them, and requires explicit revision-bound Engineering Manager (EM) approval before Markdown export.

> **Prototype safety boundary:** Use synthetic or anonymized BRDs. The default provider is deterministic and offline. Do not send real/confidential BRDs to an external provider unless its endpoint and data boundary are approved. Evaluation of this small synthetic dataset is not evidence of production readiness.

## Requirements and setup

- Python 3.13 or newer
- Git (only if cloning the repository)

From the project root in VS Code or a terminal:

```powershell
python -m pip install -e ".[dev]"
python -m pytest
streamlit run app/main.py
```

`pyproject.toml` pins the prototype runtime dependencies. No cloud service, API key, or committed secret is needed for the default workflow. The optional remote provider is installed separately with `python -m pip install -e ".[openai]"`; see [Guardrails and operations](docs/guardrails-and-operations.md) before opting in.

For an authorized OpenAI test, set `OPENAI_API_KEY` in the application process environment (for example, `$env:OPENAI_API_KEY="<your key>"` in PowerShell), install the `openai` extra, then select OpenAI in the UI and confirm the endpoint is approved for the data. Never commit the key or place it in a notebook.

## Run the end-to-end demo

1. Run `streamlit run app/main.py` and choose the included synthetic BRD.
2. Inspect the five specialist artifacts, their citations, source requirements, assumptions, uncertainties, badges, and Critic history.
3. Review the rule scores, separate judge notes, and safe operational records.
4. Select the exact artifact revisions, enter the EM approver name, and explicitly approve before downloading Markdown.

The same flow can run without a UI:

```python
from pathlib import Path
from src.orchestration.graph import run_workflow

brd = Path("data/sample_brd.md")
result = run_workflow(brd.read_text(encoding="utf-8"), brd.name)
print(result.aggregate_badge, result.critic.findings)
```

See [the Google Colab notebook](notebooks/demo.ipynb) for an interactive walkthrough. In Colab, upload or clone the repository, install with `%pip install -e ".[dev]"`, then run all cells. The notebook uses only the included fabricated BRD and local provider.

## Architecture

LangGraph owns run state and routes validated, versioned Pydantic outputs in dependency order:

`BRD validation → local Qdrant retrieval → Engineering Plan → Schedule → Solution Architect → PoC Planner → Tech Stack Recommender → Critic/revisions → evaluation → EM approval/export`.

The seven roles are Orchestrator, Engineering Plan Generator (includes reflection), Schedule Estimator, Solution Architect, PoC Planner, Tech Stack Recommender, and Critic. Five specialist artifact contracts share source IDs, citations, assumptions, uncertainty, section coverage, and revision identity. Every handoff rejects invalid requirement or citation references. The Critic sends targeted feedback to the originating role and permits no more than two cycles per artifact.

`knowledge/` contains seven varied synthetic sources. A retrieval adapter encapsulates local in-memory Qdrant, deterministic feature-hash embeddings, chunking, and index metadata. Empty retrieval continues with a disclaimer and caps Green; unresolved findings and lower badges remain visible. OpenAI is an opt-in provider adapter; Azure, ChromaDB deployment, persistent multi-user runs, confidential data processing, and production operations are outside this prototype.

More details:

- [Architecture and contracts](docs/architecture-and-contracts.md)
- [Retrieval and index design](docs/retrieval-design.md)
- [Evaluation report and metrics](docs/evaluation-report.md)
- [Guardrails and operational criteria](docs/guardrails-and-operations.md)

## Development

```powershell
python -m pytest
```

Tests cover contracts, parsing, Qdrant retrieval, the complete sample workflow, no-hit retrieval, citation integrity, revision caps, safe logs, and approval-bound export. All fixtures are synthetic. Avoid adding user BRDs, credentials, or generated operational data to the repository.
