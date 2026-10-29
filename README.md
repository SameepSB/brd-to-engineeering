# BRD-to-engineering prototype

An offline-ready prototype that turns a synthetic Business Requirements Document (BRD) into cited engineering artifacts, reviews them with a bounded Critic loop, evaluates them, and requires explicit revision-bound Engineering Manager (EM) approval before Markdown export.

> **Prototype safety boundary:** Use synthetic or anonymized BRDs. The default provider is deterministic and offline. Do not send real/confidential BRDs to an external provider unless its endpoint and data boundary are approved. Evaluation of this small synthetic dataset is not evidence of production readiness.

## Quick start (local laptop)

Prerequisite: Python 3.13 or newer. Check with `python --version`; on Windows, `py -0` lists installed versions. Use the same interpreter for every command below (for example `py -3.14 -m ...` if the default `python` is older).

1. Open a terminal in the project root (the folder containing `pyproject.toml`).
2. Install the project and test tools (first time only):
   ```powershell
   python -m pip install -e ".[dev]"
   ```
3. Optional check that everything works:
   ```powershell
   python -m pytest
   ```
4. Start the app:
   ```powershell
   python -m streamlit run app/main.py
   ```
5. Open <http://localhost:8501> if the browser does not open automatically. Keep "Use included synthetic BRD" ticked (or upload a `.md`/`.txt` BRD), choose a provider, and click **Run review workflow**.
6. Stop the app with `Ctrl+C` in the terminal.

### Providers and the LLM

- **Deterministic local (offline), the default:** no LLM is called. Template text and a rule-based judge note are produced locally, with no key or internet needed.
- **OpenAI (opt-in):** each specialist agent (and each revision) makes one `narrative` call returning a single conservative sentence. The judge makes one call per artifact returning scores as JSON. Both use `gpt-4.1-mini` at `temperature=0`. Citations, requirement links, scoring, badges, and approvals stay deterministic, and any citation that was not retrieved in the run is rejected. To enable it:
  ```powershell
  python -m pip install -e ".[openai]"
  $env:OPENAI_API_KEY="<your key>"      # set in the same terminal; never commit it
  python -m streamlit run app/main.py
  ```
  In the UI choose **OpenAI (opt-in)** and tick the endpoint-approval box, which sets `BRD_ALLOW_EXTERNAL_CONTENT=1` for that process. Selected BRD text is then sent to OpenAI, so use synthetic or authorized data only.
- **Gemini (opt-in):** same behavior via Google's OpenAI-compatible endpoint (default model `gemini-2.5-flash`; override with `$env:BRD_MODEL`). Uses the same `openai` extra:
  ```powershell
  python -m pip install -e ".[openai]"
  $env:GEMINI_API_KEY="<your key>"
  python -m streamlit run app/main.py
  ```
  Choose **Gemini (opt-in)** in the UI and tick the approval box. BRD text is sent to Google, so use synthetic or authorized data only.

### Run in the notebook (VS Code or Colab)

Open `notebooks/demo.ipynb`, select a Python 3.13+ kernel, and run all cells. The first cell finds the repository root and installs the project into the kernel if dependencies are missing. In Colab, clone or upload the repository first.

### Troubleshooting

| Symptom | Fix |
|---|---|
| `No module named 'src'` or `'langgraph'` | Run from the repo root and install with `python -m pip install -e ".[dev]"` using the interpreter that runs the app or the notebook kernel. |
| `Python 3.13+ required` or pip refuses to install | Select or install Python 3.13 or newer and use that interpreter (`py -3.14 -m pip ...`). |
| `streamlit` is not recognized | Use `python -m streamlit run app/main.py`. |
| Port 8501 is busy | Add `--server.port 8502`. |
| OpenAI option errors | Set `OPENAI_API_KEY`, install the `openai` extra, and tick the endpoint-approval box. |

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
