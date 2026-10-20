# Stack verification — Architecture Spine

**Review date:** 2026-10-20  
**Scope:** Currentness, fit, version precision, and deployment/region assumptions for every named runtime, service, vector store, and model in `ARCHITECTURE-SPINE.md`. No changes were made to the spine.

## Verdict

The listed Python package releases are current as of the review date, and LangGraph, Streamlit, Qdrant, and Chroma are plausible choices for the stated prototype. The stack is **not ready to be frozen as an implementation/deployment baseline**: ChromaDB 1.5.9 has unresolved security advisories reported against it, the proposed Azure model path does not establish model/deployment equivalence or regional/data-residency fit, and several listed package versions are not the server/runtime versions implied by the architecture.

## Verified stack

| Spine entry | Currentness at 2026-10-20 | Fit / version interpretation |
| --- | --- | --- |
| Python `3.13` | Still supported; Python 3.13.16 is the latest 3.13 maintenance release. Python 3.14 is the newest feature series. | Suitable if dependencies are tested on 3.13. The spine names a minor series, not a reproducible interpreter patch/build. |
| LangGraph `1.2.16` | Current PyPI release as of the review date; released Oct. 16, 2026. | Good fit for the declared stateful, dependency-ordered coordinator and bounded human-review flow. Pin this as the Python distribution, not as a deployment/server version. |
| Streamlit `1.66.0` | Current PyPI release as of the review date; released Oct. 14, 2026. | Suitable for the expressly low-concurrency EM demo. The architecture correctly does not present it as the production availability design. |
| `qdrant-client` `1.19.1` | Current PyPI client release as of the review date. | Suitable for prototype access, but this is a **Python client package**. It does not pin a separately run Qdrant server or container. |
| `chromadb` `1.5.9` | Current PyPI release as of the review date. | The Python distribution can run a client or launch Chroma’s server; the spine does not identify which artifact is deployed. The release also has unresolved security concerns (see findings). |
| OpenAI `gpt-4.1-mini` | Valid OpenAI API model ID. OpenAI lists default snapshot `gpt-4.1-mini-2025-04-14`; its current model page recommends starting with GPT-5 Mini for more complex tasks. | A model ID/alias, not a Python package version. For the Microsoft target, its Azure lifecycle and availability need separate treatment. |
| OpenAI `text-embedding-3-small` | Valid OpenAI API embedding model ID; the official page lists the same ID as its default snapshot. | A model ID, not a package/server version. Keep model and dimensions recorded per index as the spine already requires; validate the Azure counterpart and deployment before migration. |
| Pydantic | Named as a required contract technology, but absent from the Stack table and unversioned. | A runtime dependency that needs a declared supported version range and compatibility test. |
| Azure AI Foundry | The current Microsoft product name is **Microsoft Foundry** (formerly Azure AI Foundry). | A service/platform name, not a model ID or server version. The spine defers actual Azure deployment IDs, regions, and model choices, so Azure fit is not yet verified. |
| Azure VM / Chroma service | No VM SKU, region, OS/image, Chroma server artifact, or immutable image/package build is specified. | A topology, not a version pin. Sizing and availability cannot be validated without workload, region, and resource choices. |

## Findings

### 1. ChromaDB 1.5.9 is not a safe “current stable” default without an advisory gate

**Location:** AD-7, AD-11, Stack — `ChromaDB (Azure target) | 1.5.9`

Although 1.5.9 is the latest PyPI release at the review cutoff, the upstream Chroma repository has issue [#7909](https://github.com/chroma-core/chroma/issues/7909) reporting that a fresh install of 1.5.9 triggers five advisory entries representing four CVEs, with no fixed release identified in the issue as of Oct. 20. This is distinct from release freshness: “latest” does not establish “safe to deploy.”

**Recommendation:** Treat 1.5.9 as blocked pending an upstream-fixed release and vulnerability scan of the exact resolved dependency tree/image. If a prototype must use it, explicitly scope it to synthetic data and isolate the service; do not imply that the version is production-approved.

### 2. The Azure model migration conflicts with the selected generation model’s lifecycle

**Location:** AD-6, AD-11, Deferred — Azure deployment/model IDs

`gpt-4.1-mini` is a valid OpenAI API model ID, but the Microsoft Foundry model lifecycle/retirement materials currently list the GPT-4.1 family as deprecated for Azure and give an Apr. 14, 2027 retirement date. This does not invalidate the initial OpenAI API prototype; it makes this named default a poor unqualified assumption for the later Azure target. OpenAI’s model page also identifies `gpt-4.1-mini-2025-04-14` as the default snapshot and recommends starting with GPT-5 Mini for more complex tasks.

**Recommendation:** Separate the OpenAI prototype default from the Azure target model. Select an Azure-supported model/deployment after checking the live retirement and region tables, then run the versioned evaluation suite against it. Do not treat the OpenAI alias as a cross-provider Azure deployment ID.

### 3. “Azure AI Foundry” and the provider target are underspecified for a 2026 deployment

**Location:** AD-6, AD-8, AD-11, Deferred — Azure model IDs and regional availability

Microsoft’s current product naming is **Microsoft Foundry**. More importantly, “Foundry” alone does not fix a model deployment, endpoint, deployment type, processing geography, or quota. Microsoft’s official deployment guidance explains that Global deployments can process in any Azure region, Data Zone deployments are bounded to a defined zone, and geography-based deployments are region/geography-bound. Availability differs by model and region. Those choices are material to the stated confidentiality boundary for BRDs.

**Recommendation:** Name the current service/platform in the provider plan, then define the deployment category, model/deployment ID and version, resource region, data-processing boundary, and availability check as release-time prerequisites. Keep the existing provider adapter and model catalog abstractions, but do not mark Azure migration validated while these remain deferred.

### 4. The Qdrant pin identifies a client library, not the prototype vector-store server

**Location:** Stack — `Qdrant Python client (prototype) | 1.19.1`; AD-7

The pinned PyPI project is `qdrant-client`, a Python client. Its official package documentation distinguishes local mode (embedded local storage) from connecting to a Qdrant server. “Local Qdrant” in the spine does not state which mode is intended, and the package pin does not pin a Qdrant server/container release.

**Recommendation:** Say explicitly whether the prototype uses Qdrant client local mode or a separate Qdrant server. If server mode is intended, pin the server image/version (preferably immutable digest) separately from `qdrant-client`, and test the client/server compatibility pair.

### 5. The Chroma Python package pin does not unambiguously pin the deployed server artifact

**Location:** Stack — `ChromaDB (Azure target) | 1.5.9`; AD-11

Chroma’s official package/docs describe `chromadb` as a Python client and provide `chroma run` for client-server mode. The architecture says ChromaDB is a service on an Azure VM but does not say whether that VM installs this wheel, runs the official container, or uses another artifact. A PyPI version alone cannot verify an independently built/deployed image.

**Recommendation:** State the deployment mode and pin its actual artifact: package version and lockfile if installed directly, or a versioned container image plus digest if containerized. Confirm the client and server versions are aligned.

### 6. Required contract and provider dependencies are not all versioned in the stack

**Location:** AD-3, AD-6; Stack table

Pydantic is a required runtime contract technology but has no version entry. The initial OpenAI API/provider path also does not identify the Python `openai` SDK/version (if that SDK is intended). As written, the table does not provide enough information to build and reproduce the named runtime.

**Recommendation:** Add Pydantic and any intended provider SDK as explicit runtime dependencies, with supported version ranges or exact lockfile resolutions. If using raw HTTP instead of an SDK, make that an explicit implementation choice. Validate the chosen versions on the declared Python runtime.

### 7. Python is specified only to the minor series while the dependency pins are exact

**Location:** Stack — `Python | 3.13`

Python 3.13 remains a valid supported target, but the current maintenance release is 3.13.16 and Python 3.14 is now the latest feature series. `3.13` is a compatibility line, not an exact runtime build; no patch/update policy is specified.

**Recommendation:** Keep Python 3.13 if it is the tested compatibility target, but define the tested support range and lock/CI runtime patch policy (for example, supported `3.13.x`, with the deployment image pinned to an exact patch). Test Python 3.14 separately before changing the target; do not infer compatibility from package metadata alone.

### 8. The single-VM Chroma target has no workload sizing basis

**Location:** AD-11; Deferred — production concurrency and scale

Calling the VM a low-concurrency starting topology is appropriately cautious, but no collection size, embedding dimensions, document/metadata size, VM memory, or disk budget is defined. Chroma’s own single-node guide states that its HNSW index must fit in RAM and provides sizing/latency measurements tied to particular workloads and instance sizes. Consequently, the current topology cannot be validated even as a capacity estimate.

**Recommendation:** Before selecting a VM SKU, estimate corpus/vector count and record sizes, run representative ingestion/query tests, and size RAM and persistent disk with headroom. Revisit the deployment decision when the expected corpus or concurrent usage changes.

### 9. Model names are not immutable model snapshots or Azure deployment names

**Location:** AD-6, consistency conventions — Model selection

`gpt-4.1-mini` is an OpenAI model alias whose documented snapshot is `gpt-4.1-mini-2025-04-14`; `text-embedding-3-small` is an embedding model ID rather than a package version. Azure deployments introduce separate deployment naming and model/version/region choices. The run metadata stores provider and model IDs, which is useful, but the spine does not say whether IDs are aliases or immutable snapshots and does not capture Azure deployment identity/version.

**Recommendation:** Define separate fields for provider, API model ID, immutable model snapshot/version where available, Azure deployment name/ID and deployment type, and catalog/evaluation version. Make alias changes an explicit evaluated catalog update. Continue recording the embedding model/dimension per index and rebuilding on embedding changes as AD-7 requires.

## Recommendations with no currentness blocker

- **LangGraph 1.2.16:** Current and well matched to a single coordinator owning state, routing and bounded agent cycles. Preserve a separate decision for checkpoint persistence/durability before multi-user runs.
- **Streamlit 1.66.0:** Current and suitable for the demo UI described. The stated low-concurrency, non-HA limitation is an appropriate boundary, not a production guarantee.
- **`text-embedding-3-small`:** Current supported OpenAI model ID and a reasonable cost-conscious starting point. Keep it provisional until retrieval regression and quality evaluation confirm fit for the BRD corpus and Azure target.

## Sources checked

Official vendor/package references reviewed on 2026-10-20:

- [Python 3.13.16 release](https://www.python.org/downloads/release/python-31316/) — latest 3.13 maintenance release and note that 3.14 is the latest feature series.
- [LangGraph on PyPI](https://pypi.org/project/langgraph/) and [LangGraph releases](https://github.com/langchain-ai/langgraph/releases).
- [Streamlit on PyPI](https://pypi.org/project/streamlit/) and [official release notes](https://docs.streamlit.io/develop/quick-reference/release-notes).
- [`qdrant-client` on PyPI](https://pypi.org/project/qdrant-client/) — client/local-mode/server distinction.
- [ChromaDB on PyPI](https://pypi.org/project/chromadb/); upstream [Chroma issue #7909](https://github.com/chroma-core/chroma/issues/7909) — reports advisories for 1.5.9.
- Chroma docs: [run a server](https://docs.trychroma.com/docs/cli/run), [client-server mode](https://docs.trychroma.com/docs/run-chroma/client-server), and [single-node performance](https://docs.trychroma.com/guides/performance/single-node).
- OpenAI model pages: [`gpt-4.1-mini`](https://developers.openai.com/api/docs/models/gpt-4.1-mini) and [`text-embedding-3-small`](https://developers.openai.com/api/docs/models/text-embedding-3-small).
- Microsoft Learn: [Foundry model deployment types](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/deployment-types), [models sold by Azure and regional availability](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure), [model retirement schedule](https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/model-retirement-schedule), and [current Foundry naming/migration guidance](https://learn.microsoft.com/en-us/azure/foundry/how-to/navigate-from-classic).

The release-currentness statements above are cutoff-specific; re-check PyPI, Microsoft model availability/retirement, and advisory status immediately before implementation and deployment.
