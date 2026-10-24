from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from src.orchestration.graph import run_workflow
from src.providers.openai_adapter import OpenAIProvider
from src.storage.approval import ApprovalError, approve_run
from src.tools.export import export_markdown

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_BRD = ROOT / "data" / "sample_brd.md"

st.set_page_config(page_title="BRD-to-engineering prototype", layout="wide")
st.title("BRD → engineering review")
st.caption("Synthetic-first prototype. Review evidence, assumptions, uncertainty, badges, and revisions before export.")

provider_mode = st.selectbox("Generation and evaluation provider", ["Deterministic local (offline)", "OpenAI (opt-in)"])
if provider_mode == "OpenAI (opt-in)":
    approved_endpoint = st.checkbox(
        "I confirm the configured OpenAI endpoint is approved for this BRD and I am using synthetic or authorized data."
    )
    st.warning("Selected BRD text will be sent to the configured OpenAI endpoint. Do not use confidential data without approval.")
else:
    approved_endpoint = False

use_sample = st.checkbox("Use included synthetic BRD", value=True)
uploaded = st.file_uploader("Or upload a Markdown or text BRD", type=["md", "txt"])
if use_sample:
    brd_content = SAMPLE_BRD.read_text(encoding="utf-8")
    brd_filename = SAMPLE_BRD.name
    input_error = None
elif uploaded is not None:
    brd_filename = uploaded.name
    try:
        brd_content = uploaded.getvalue().decode("utf-8", errors="strict")
        input_error = None
    except UnicodeDecodeError:
        brd_content = ""
        input_error = "The uploaded file is not valid UTF-8 text."
else:
    brd_content = ""
    brd_filename = "requirements.md"
    input_error = None

if st.button("Run review workflow", type="primary"):
    try:
        if input_error:
            st.error(input_error)
            st.stop()
        if provider_mode == "OpenAI (opt-in)":
            if not approved_endpoint:
                st.error("Explicit endpoint approval is required before sending BRD content.")
                st.stop()
            if not os.environ.get("OPENAI_API_KEY"):
                st.error("Set OPENAI_API_KEY in the application environment before selecting OpenAI.")
                st.stop()
            os.environ["BRD_ALLOW_EXTERNAL_CONTENT"] = "1"
            provider = OpenAIProvider()
        else:
            from src.providers.deterministic import DeterministicProvider

            provider = DeterministicProvider()
        st.session_state["run_result"] = run_workflow(brd_content, brd_filename, provider=provider)
        st.session_state.pop("run_approval", None)
    except (UnicodeDecodeError, ValueError, RuntimeError) as exc:
        st.error(str(exc))

result = st.session_state.get("run_result")
if result is not None:
    st.subheader(f"Run {result.run_id}")
    badge_color = {"Green": "green", "Amber": "orange", "Red": "red"}[result.aggregate_badge]
    st.markdown(f"**Aggregate quality:** :{badge_color}[{result.aggregate_badge}]")
    st.caption(f"Input SHA-256: `{result.input_hash}`")
    if result.evidence_disclaimer:
        st.warning(result.evidence_disclaimer)
    with st.expander("Normalized source requirements"):
        for requirement in result.normalized_brd.requirements:
            st.markdown(
                f"- **{requirement.requirement_id}** ({requirement.section_id}; "
                f"{requirement.source_locator}): {requirement.text}"
            )

    tabs = st.tabs(["Artifacts", "Critic & evaluation", "Operations"])
    with tabs[0]:
        for role, artifact in result.artifacts.items():
            with st.expander(f"{role.replace('_', ' ').title()} — {artifact.badge}, revision {artifact.revision}", expanded=True):
                st.write(f"**Artifact ID:** `{artifact.artifact_id}` · Contract `{artifact.contract_version}`")
                st.write("**Claims**")
                for claim in artifact.claims:
                    st.markdown(f"- {claim.text}")
                    for citation in claim.citations:
                        st.caption(
                            f"Citation: {citation.source_id} / {citation.chunk_id} "
                            f"({citation.source_locator})"
                        )
                st.write("**Assumptions**")
                st.write(artifact.assumptions)
                st.write("**Uncertainties**")
                st.write([item.model_dump(mode="json") for item in artifact.uncertainties])
                st.write("**Artifact details**")
                st.json(artifact.model_dump(mode="json"))

    with tabs[1]:
        st.write("**Critic findings**")
        st.json([finding.model_dump(mode="json") for finding in result.critic.findings])
        st.write("**Rule scores by artifact and revision**")
        st.json({key: [score.model_dump(mode="json") for score in value] for key, value in result.revision_history.items()})
        st.write("**Evaluation methods and judge notes**")
        st.json(result.evaluation)

    with tabs[2]:
        st.json([item.model_dump(mode="json") for item in result.operational_records])

    st.subheader("Approval-gated export")
    selected_ids = st.multiselect(
        "Select exact artifact revisions for export",
        options=[artifact.artifact_id for artifact in result.artifacts.values()],
        default=[artifact.artifact_id for artifact in result.artifacts.values()],
    )
    approver = st.text_input("Engineering Manager name")
    if st.button("Approve selected revisions"):
        try:
            st.session_state["run_approval"] = approve_run(result, approver, selected_ids)
            st.success("Approval is bound to the selected revisions shown above.")
        except ApprovalError as exc:
            st.error(str(exc))
    approval = st.session_state.get("run_approval")
    if approval is not None:
        try:
            export = export_markdown(result, approval, selected_ids)
            st.download_button(
                "Download approved Markdown",
                export.markdown,
                file_name=f"{result.run_id}-approved.md",
                mime="text/markdown",
            )
        except ApprovalError as exc:
            st.error(f"Export blocked: {exc}")
