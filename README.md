# SimpleAgentsHealthInsurance

Health insurance underwriting workflow built with [Simple Agents](https://github.com/CraftsMan-Labs/SimpleAgents) (`simple-agents-py`). The pipeline is defined in `workflow.yaml`; `main.py` runs it from the CLI with streaming output, and `app.py` provides a Streamlit UI.

## Requirements

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** — install dependencies and run commands
- **Docker** (optional) — only if you want local [Langfuse](https://langfuse.com/) for OpenTelemetry tracing

## Setup

1. **Environment variables**

   ```bash
   cp .example.env .env
   ```

   Edit `.env` and set at least:

   - `WORKFLOW_API_KEY` — your LLM API key  
   - `WORKFLOW_API_BASE` — provider base URL (e.g. `https://api.openai.com/v1` or your gateway)  
   - `WORKFLOW_PROVIDER` — e.g. `openai`

   Langfuse keys are optional; leave the placeholder values if you are not using local tracing.

2. **Install dependencies** (from the repo root):

   ```bash
   uv sync
   ```

## Run the workflow (CLI)

Run from the **repository root** so `workflow.yaml` resolves correctly:

```bash
uv run main.py
```

Output streams to the terminal. With real Langfuse keys and a running Langfuse stack, traces are sent via OpenTelemetry (see below).

## Run the Streamlit app

```bash
uv run streamlit run app.py
```

Open the URL Streamlit prints (by default **http://localhost:8501**). To use another port:

```bash
uv run streamlit run app.py --server.port 8502
```

## Optional: Langfuse (Docker) for tracing

The repo includes a **Langfuse v3** stack (Postgres, ClickHouse, Redis, MinIO) for local OTEL ingestion.

1. **Create the Postgres volume once** (required by `docker-compose.yml`):

   ```bash
   docker volume create simpleagentshealthinsurance_langfuse_db_data
   ```

2. **Start services**:

   ```bash
   docker compose up -d
   ```

3. Open **http://localhost:3000**, create an account/project, and copy **public** and **secret** keys into `.env` as `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY`.

4. Run `uv run main.py` or the Streamlit app again; traces should show up in Langfuse.

MinIO is exposed for debugging at **http://localhost:9010** (API) and **http://localhost:9011** (console), with credentials `minio` / `miniosecret` as defined in `docker-compose.yml`.

---

## Workflow diagram

```mermaid

flowchart TD
  extract_documents["extract_documents\n(custom_worker)"]
  class extract_documents nodeFunction;
  validate_documents["validate_documents\n(llm_call)"]
  class validate_documents nodeLlm;
  route_doc_validation["route_doc_validation\n(switch)"]
  class route_doc_validation nodeSwitch;
  terminate_missing_docs["terminate_missing_docs\n(llm_call)"]
  class terminate_missing_docs nodeLlm;
  process_underwriting_coverage["process_underwriting_coverage\n(llm_call)"]
  class process_underwriting_coverage nodeLlm;
  route_underwriting["route_underwriting\n(switch)"]
  class route_underwriting nodeSwitch;
  terminate_underwriting["terminate_underwriting\n(llm_call)"]
  class terminate_underwriting nodeLlm;
  process_risk_assessment["process_risk_assessment\n(llm_call)"]
  class process_risk_assessment nodeLlm;
  route_risk_assessment["route_risk_assessment\n(switch)"]
  class route_risk_assessment nodeSwitch;
  terminate_risk_assessment["terminate_risk_assessment\n(llm_call)"]
  class terminate_risk_assessment nodeLlm;
  process_premium_calculation["process_premium_calculation\n(llm_call)"]
  class process_premium_calculation nodeLlm;
  route_premium_calc["route_premium_calc\n(switch)"]
  class route_premium_calc nodeSwitch;
  terminate_premium["terminate_premium\n(llm_call)"]
  class terminate_premium nodeLlm;
  process_final_approval["process_final_approval\n(llm_call)"]
  class process_final_approval nodeLlm;
  route_final_approval["route_final_approval\n(switch)"]
  class route_final_approval nodeSwitch;
  terminate_approval["terminate_approval\n(llm_call)"]
  class terminate_approval nodeLlm;
  process_policy_issuance["process_policy_issuance\n(llm_call)"]
  class process_policy_issuance nodeLlm;
  finalize_success["finalize_success\n(llm_call)"]
  class finalize_success nodeLlm;
  extract_documents --> validate_documents
  validate_documents --> route_doc_validation
  route_doc_validation --> terminate_missing_docs
  route_doc_validation --> process_underwriting_coverage
  process_underwriting_coverage --> route_underwriting
  route_underwriting --> terminate_underwriting
  route_underwriting --> process_risk_assessment
  process_risk_assessment --> route_risk_assessment
  route_risk_assessment --> terminate_risk_assessment
  route_risk_assessment --> process_premium_calculation
  process_premium_calculation --> route_premium_calc
  route_premium_calc --> terminate_premium
  route_premium_calc --> process_final_approval
  process_final_approval --> route_final_approval
  route_final_approval --> terminate_approval
  route_final_approval --> process_policy_issuance
  process_policy_issuance --> finalize_success
  route_doc_validation -- "route1" --> terminate_missing_docs
  route_doc_validation -- "default" --> process_underwriting_coverage
  route_underwriting -- "route1" --> terminate_underwriting
  route_underwriting -- "default" --> process_risk_assessment
  route_risk_assessment -- "route1" --> terminate_risk_assessment
  route_risk_assessment -- "default" --> process_premium_calculation
  route_premium_calc -- "route1" --> terminate_premium
  route_premium_calc -- "default" --> process_final_approval
  route_final_approval -- "route1" --> terminate_approval
  route_final_approval -- "default" --> process_policy_issuance
  classDef nodeSet fill:#163124,stroke:#3f9f71,color:#ddf8ea,stroke-width:1px;
  classDef nodeLlm fill:#152735,stroke:#51a7e6,color:#d7efff,stroke-width:1px;
  classDef nodeOutput fill:#3a2e14,stroke:#d8ad42,color:#fff0c4,stroke-width:1px;
  classDef nodeSwitch fill:#1e2b35,stroke:#6e8da7,color:#deedf7,stroke-width:1px;
  classDef nodeFunction fill:#33241e,stroke:#c08457,color:#fde9dd,stroke-width:1px;

```
