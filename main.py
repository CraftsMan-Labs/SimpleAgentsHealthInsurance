import os
import json
import base64
from pathlib import Path
from typing import Callable
from dotenv import load_dotenv
from simple_agents_py import Client
from simple_agents_py.workflow_payload import workflow_execution_request_to_mapping
from simple_agents_py.workflow_request import (
    WorkflowExecutionFlags,
    WorkflowExecutionRequest,
    WorkflowMessage,
    WorkflowRole,
    WorkflowRunOptions,
    WorkflowTelemetryConfig,
)
from simple_agents_py.workflow_stream import WorkflowStreamEvent

load_dotenv()


TERMINATION_NODE_IDS = [
    "terminate_missing_docs",
    "terminate_underwriting",
    "terminate_risk_assessment",
    "terminate_premium",
    "terminate_approval",
]


def _stream_delta_from_event(event: WorkflowStreamEvent) -> str | None:
    if "delta" in event:
        return event["delta"]
    if "event_type" in event:
        if event["event_type"] == "workflow_completed":
            return json.dumps(event["metadata"], indent=2)
    return None


def default_on_event(
    event: WorkflowStreamEvent,
    emit_delta: Callable[[str], None] | None = None,
) -> None:
    delta = _stream_delta_from_event(event)
    if delta is None:
        return
    if emit_delta is None:
        print(delta, end="", flush=True)
        return
    emit_delta(delta)


def _is_real_langfuse_key(value: str, prefix: str) -> bool:
    value = value.strip()
    return (
        bool(value) and value.startswith(prefix) and "placeholder" not in value.lower()
    )


def setup_langfuse():
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "")
    base_url = os.environ.get("LANGFUSE_BASE_URL", "http://localhost:3000").rstrip("/")

    # Inside Docker on Linux, localhost is the container — reach the host via host.docker.internal
    # (docker-compose should map host.docker.internal). Do not rewrite when running on the host.
    if "localhost" in base_url and os.path.exists("/.dockerenv"):
        import platform

        if platform.system() == "Linux":
            base_url = base_url.replace("localhost", "host.docker.internal")

    if _is_real_langfuse_key(public_key, "pk-lf") and _is_real_langfuse_key(
        secret_key, "sk-lf"
    ):
        token = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode("ascii")
        os.environ["SIMPLE_AGENTS_TRACING_ENABLED"] = "true"
        os.environ["OTEL_EXPORTER_OTLP_PROTOCOL"] = "http/protobuf"
        os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = f"{base_url}/api/public/otel"
        os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = (
            f"Authorization=Basic {token},x-langfuse-ingestion-version=4"
        )
        os.environ["OTEL_SERVICE_NAME"] = "health-insurance-pipeline"


setup_langfuse()


def create_client():
    return Client(
        os.environ["WORKFLOW_PROVIDER"],
        api_base=os.environ["WORKFLOW_API_BASE"],
        api_key=os.environ["WORKFLOW_API_KEY"],
    )


def run_agent(message: str, on_event=default_on_event):
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

    return client.stream_workflow(
        workflow_execution_request_to_mapping(req),
        on_event=on_event,
    )


def extract_response(result: dict) -> str:
    terminal_output = result.get("terminal_output")
    return json.dumps(terminal_output, indent=2)


def format_email(email_data: dict) -> str:
    return f"""
TO: {email_data.get("to", "N/A")}
FROM: {email_data.get("from", "N/A")}
SUBJECT: {email_data.get("subject", "N/A")}

{email_data.get("body", "")}

ACTION REQUIRED: {email_data.get("action_required", "N/A")}
STAGE FAILED: {email_data.get("stage_failed", "N/A")}
REASON: {email_data.get("reason", "N/A")}
"""


def main():
    message: str = """Applicant: John Smith
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
    run_agent(message=message)


if __name__ == "__main__":
    main()
