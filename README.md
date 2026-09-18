# AI SOC Analyst Agent

An agentic AI threat-hunting copilot for SOC analysts. You describe what you're worried about in plain English (*"I'm worried windows-target-1 might have been maliciously logged into in the last few days"*), and the agent decides which Microsoft Defender for Endpoint / Azure AD / Azure Activity table to query, runs a scoped KQL query against an Azure Log Analytics Workspace, and uses an LLM to analyze the returned logs for suspicious activity — mapping findings to MITRE ATT&CK, extracting indicators of compromise, and recommending next steps.

The project is built as a series of progressively more capable implementations, from bare API calls up to a guardrailed, tool-using agent. Each stage lives in its own folder under `src/` so the reasoning behind each addition (tool calling, guardrails, automated remediation) stays visible rather than being buried in one final version.

## How it works

At a high level:

1. The analyst is prompted for a natural-language request.
2. The model is given a tool definition for querying Log Analytics and decides which table, fields, time range, and target entity (device / user / NSG) best answer the request — returning structured arguments instead of free text.
3. The chosen table and fields are validated against an explicit allow-list before anything is queried.
4. The agent runs the corresponding KQL query against the workspace via the Azure Monitor Query SDK.
5. The returned logs are packaged into a table-specific threat-hunting prompt (system role + user role, described below) and sent to the model for analysis.
6. The model returns structured findings (title, description, MITRE ATT&CK mapping, IOCs, confidence, recommendations), which are printed to the console and appended to a local `_threats.jsonl` log.

See `docs/How it works.pdf` for a diagram of the lab environment this agent operates against (a SOC/cyber range subscription with a member VNet of simulated hosts, sitting behind an NSG, feeding Log Analytics) and `docs/Copy of Baseline Agent Workflow.pdf` for a step-by-step flowchart of the code path above, annotated with the exact module/function responsible for each step.

### Prompt construction

Every threat hunt is built from three parts, combined into a single user-role message alongside a dedicated system-role message — see `docs/Prompt Engineering Diagram.pdf` for the full layout:

- **System message** — establishes the model's role as a threat-hunting AI trained on MDE, Azure AD, and Azure resource logs, and sets expectations around MITRE mapping, confidence scoring, and IOC extraction.
- **User message** — the analyst's original request, table-specific hunting instructions (tuned per log source, e.g. `DeviceProcessEvents` vs. `SigninLogs`), strict JSON output-formatting instructions, and the raw log data pulled from Log Analytics.

## Repository structure

```
.
├── docs/    Diagrams explaining the lab environment, agent workflow, and prompt design
└── src/     Five stages of the same project, from raw API calls to a guardrailed agent
```

### `docs/`

- **`How it works.pdf`** — diagram of the target environment: the SOC/cyber range Azure subscription, the member VNet of simulated hosts behind an NSG, and how the AI SOC Analyst sits between the analyst and the Log Analytics workspace.
- **`Copy of Baseline Agent Workflow.pdf`** — flowchart of the end-to-end request lifecycle, mapping each step (prompt user, get query context, validate tables/fields, query Log Analytics, build threat-hunt prompt, choose model, execute hunt, display results) to the exact module and function that implements it.
- **`Prompt Engineering Diagram.pdf`** — breakdown of the system/user message structure sent to the model for analysis, showing how the analyst's request, table-specific instructions, output-format instructions, and log data are assembled into one prompt.

### `src/`

The five folders below represent an incremental build-up of the same agent. Each one is a self-contained, runnable project with its own `EXECUTOR.py`, `GUARDRAILS.py`, `MODEL_MANAGEMENT.py`, `PROMPT_MANAGEMENT.py`, `UTILITIES.py`, and `_main.py` entry point (except `foundations`, which predates that structure).

| Folder | What it adds |
|---|---|
| **`foundations/`** | Standalone scripts from before the agent had a defined structure: raw OpenAI chat completions, JSON-mode output, a first pass at querying Log Analytics with the Azure SDK, KQL query optimization experiments, and sample log data (`logsshort.py`, `logslong.py`) used for early prompt testing. No agent logic here — just the building blocks. |
| **`tools_lesson/`** | Introduces OpenAI function/tool calling: instead of hardcoding a query, the model is given a `query_log_analytics_individual_device` tool and chooses the table, fields, time range, and entity to search based on the analyst's request. |
| **`guardrails/`** | Adds validation on top of tool calling: an explicit allow-list of queryable tables/fields (`GUARDRAILS.validate_tables_and_fields`) and an allow-list of usable OpenAI models with token/cost estimation and rate-limit checks (`MODEL_MANAGEMENT`, `GUARDRAILS.validate_model`) before any query or analysis runs. Also surfaces the model's rationale for its table/field/time-range choices to the analyst. |
| **`vm_isolation/`** | Builds on `guardrails/` with an automated remediation step: when a high-confidence host-related finding comes back, the agent can look up the corresponding Defender for Endpoint machine ID and isolate the VM (`EXECUTOR.get_mde_workstation_id_from_name`, `EXECUTOR.quarantine_virtual_machine`), with the analyst prompted to confirm before isolation happens. |
| **`baseline_agent/`** | The current reference implementation. Combines tool calling and guardrails with a much more developed prompt library — dedicated threat-hunting instructions per log table (`DeviceProcessEvents`, `DeviceNetworkEvents`, `DeviceLogonEvents`, `DeviceRegistryEvents`, `DeviceFileEvents`, `AlertEvidence`, `AzureActivity`, `SigninLogs`, `AuditLogs`, `AzureNetworkAnalytics_CL`) and a detailed "Aegis" system persona guiding tool-selection behavior. This is the best starting point for running or extending the project. |

Each folder's `_threats.jsonl` is a local, append-only log of findings from past runs of that version — useful for reviewing history, not something you need to edit by hand.

## Guardrails

Two allow-lists gate everything the agent can do, both defined in each version's `GUARDRAILS.py`:

- **Tables & fields** — the agent can only query the tables and fields explicitly listed (e.g. `DeviceProcessEvents`, `DeviceNetworkEvents`, `DeviceLogonEvents`, `DeviceFileEvents`, `AzureNetworkAnalytics_CL`, `AzureActivity`, `SigninLogs`). Any table or field outside that list is rejected before a query is ever run.
- **Models** — only explicitly allowlisted OpenAI models (`gpt-4.1-nano`, `gpt-4.1`, `gpt-5-mini`, `gpt-5`) can be used for analysis, each with known context limits, per-tier rate limits, and per-million-token pricing so the agent can estimate cost and warn before a call that would exceed a limit.

## Setup

These steps apply to `src/baseline_agent/` (and work the same way for any of the other `src/` folders).

1. **Install dependencies**

   ```bash
   cd src/baseline_agent
   pip install -r requirements.txt
   ```

2. **Authenticate to Azure** — the agent uses `DefaultAzureCredential`, so log in with the Azure CLI first:

   ```bash
   az login
   ```

3. **Add your credentials** — create a `_keys.py` file inside the same folder (it's intentionally not committed to the repo) containing:

   ```python
   OPENAI_API_KEY = "your-openai-api-key"
   LOG_ANALYTICS_WORKSPACE_ID = "your-log-analytics-workspace-id"
   ```

4. **Run it**

   ```bash
   python _main.py
   ```

   You'll be prompted for a request, e.g. *"Something is messed up in our AAD/Entra ID for the last 2 weeks or so, particularly about user arisa"*. The agent will show you the table/fields/time range it chose and why, run the query, and — if any records come back — walk through the analysis and print any findings.

## Planned Capabilities

- [x] Connect to an Azure Log Analytics Workspace via the Azure Python SDK
- [x] Run KQL queries against Sentinel / Defender for Endpoint tables (sign-in logs, alert tables, device events)
- [x] Parse and structure raw query results
- [x] Use AI to summarize findings and flag anomalies in analyst-readable language
- [x] Guardrail the tables, fields, and models the agent is allowed to use
- [x] Prototype automated remediation (VM isolation) for high-confidence host findings (`src/vm_isolation`)
- [ ] Bring automated remediation into the baseline agent
- [ ] Package the workflow into a distributable CLI/tool a SOC analyst can install and run against a live workspace

## Tech Stack

**Data Source:** Microsoft Sentinel • Azure Log Analytics Workspace • KQL

**Language:** Python (Azure SDK for Python)

**AI Layer:** OpenAI API (GPT-4.1 / GPT-5 family)

## Why This Project

Most of the manual effort in early-stage SOC triage is running the same handful of KQL queries and reading through raw results by hand. This project explores how much of that first pass — choosing the right query, pulling the relevant fields, and summarizing what's notable — can be handed to an AI layer, so an analyst starts their investigation with a structured summary instead of a blank query window.

---

Part of a broader portfolio of AI and security automation projects — see [github.com/hossnfeffa](https://github.com/hossnfeffa).
