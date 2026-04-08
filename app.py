import queue
import threading
import streamlit as st
from main import _stream_delta_from_event, create_client
from pathlib import Path
from simple_agents_py.workflow_payload import workflow_execution_request_to_mapping
from simple_agents_py.workflow_request import (
    WorkflowExecutionFlags,
    WorkflowExecutionRequest,
    WorkflowMessage,
    WorkflowRole,
    WorkflowRunOptions,
    WorkflowTelemetryConfig,
)

_SENTINEL = object()

DEFAULT_MESSAGE = """Applicant: John Smith
Email: john.smith@email.com
Phone: (555) 123-4567
DOB: March 15, 1991 (Age 35)
Address: 123 Oak Street, Springfield, IL 62701

--- DOCUMENTS PROVIDED ---

1. ID (Driver's License):
Name: John Michael Smith
License #: DL-IL-88472910
DOB: 03/15/1991
Address: 123 Oak Street, Springfield, IL 62701
Expiration: 03/15/2028
Class: D

2. Proof of Income (Pay Stub):
Employer: TechCorp Inc.
Employee: John Smith
Pay Period: January 1-15, 2026
Gross Pay: $4,230.77
Net Pay: $3,184.42
YTD Earnings: $8,461.54
Position: Senior Software Engineer
Pay Rate: $55/hour

3. Medical History:
Patient: John Smith
DOB: 03/15/1991
Primary Care: Dr. Sarah Johnson
Conditions: None
Surgeries: None
Allergies: Penicillin
Last Physical: January 2026 - Excellent health
Blood Pressure: 118/76
BMI: 24.2

4. Bank Statement:
Account Holder: John Smith
Bank: First National Bank
Account #: ****4521
Statement Period: January 1-31, 2026
Opening Balance: $12,450.00
Direct Deposit: $6,384.84
Ending Balance: $18,200.35"""


def _run_agent_in_thread(message: str, token_queue: queue.Queue):
    """Run the workflow in a background thread, pushing deltas onto the queue."""

    def on_event(event):
        delta = _stream_delta_from_event(event)
        if delta is not None:
            token_queue.put(delta)

    try:
        client = create_client()
        req = WorkflowExecutionRequest(
            workflow_path=str(Path("workflow.yaml").resolve()),
            messages=[WorkflowMessage(role=WorkflowRole.USER, content=message)],
            execution=WorkflowExecutionFlags(
                node_llm_streaming=True,
                split_stream_deltas=False,
            ),
            workflow_options=WorkflowRunOptions(
                telemetry=WorkflowTelemetryConfig(enabled=True, nerdstats=True),
            ),
        )
        client.stream_workflow(
            workflow_execution_request_to_mapping(req),
            on_event=on_event,
        )
    except Exception as exc:
        token_queue.put(f"\n\n**Error:** {exc}")
    finally:
        token_queue.put(_SENTINEL)


def _token_generator(token_queue: queue.Queue):
    """Yield tokens from the queue until the sentinel is received."""
    while True:
        token = token_queue.get()
        if token is _SENTINEL:
            break
        yield token


# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Health Insurance Underwriting",
    page_icon="🏥",
    layout="wide",
)

st.title("🏥 Health Insurance Underwriting Agent")
st.markdown(
    "Paste an applicant document below and click **Run** to stream the underwriting analysis."
)

# ── Input area ────────────────────────────────────────────────────────────────
message = st.text_area(
    "Applicant Document",
    value=DEFAULT_MESSAGE,
    height=400,
    placeholder="Paste applicant details here…",
)

run_button = st.button("▶ Run", type="primary", use_container_width=True)

# ── Streaming output ──────────────────────────────────────────────────────────
if run_button:
    if not message.strip():
        st.warning("Please enter an applicant document before running.")
    else:
        st.divider()
        st.subheader("Agent Response")

        token_queue: queue.Queue = queue.Queue()

        thread = threading.Thread(
            target=_run_agent_in_thread,
            args=(message, token_queue),
            daemon=True,
        )
        thread.start()

        placeholder = st.empty()
        accumulated = ""
        for token in _token_generator(token_queue):
            accumulated += token
            # Two trailing spaces before \n make markdown respect line breaks
            placeholder.markdown(accumulated.replace("\n", "  \n"))

        thread.join()
        st.success("Analysis complete.")
