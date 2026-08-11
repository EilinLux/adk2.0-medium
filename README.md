# ADK 2.0 101: Agent Developer Kit Implementation

This repository contains the codebase and architecture blueprints for the **ADK 101** tutorial series published on Medium by *Zelda Ailine Luconi*. 

You can access the full series list and updates directly on Medium:
📚 **[Medium Article Series List](https://medium.com/@ailluzdatascience/list/agent-developer-kit-adk-5d957c62e9a9)**

The project demonstrates how to move away from fragile, notebook-bound AI prototypes and build production-grade, event-driven AI agents using **Google's Agent Developer Kit (ADK) 2.0** and agentic architecture best practices.

---

## 🚀 Repository Structure & Branching Strategy

To keep the codebase clean, isolated, and easy to follow, **each article in the Medium series corresponds to a dedicated Git branch** (e.g., `01-first-agent`, `02b-multi-agent-workflow`, `02c-graph-agent-workflow`, `03a-session-state`, `03b-session-service`, `03c-memory-service`, `03d-session-state-sostaapp`, `04a-evaluating-with-adk`, etc.).

### Why Branches Instead of Folders?

1. **True Point-in-Time Codebases:** Folders require duplicating setup files (`pyproject.toml`, configuration, environment setups) across directories or forcing a single overarching structure that might break for early articles. Branches preserve the exact snapshot of the repository as it existed at each step of the tutorial.
2. **Realistic Developer Experience:** Working across git branches mirrors real-world software workflows—you clone, switch branches, run, and experiment within a self-contained root environment.
3. **Clean Dependency Management:** Tools like `uv` or `pip` remain centered at the project root (`./`) without needing nested virtual environments or path hacks.
4. **Focused Diffs:** You can easily run `git diff branch-A branch-B` to see precisely what code was added or changed between two consecutive Medium articles.

---

## 🛠️ Core Agent Architecture & Medium Articles

| Medium Article & Milestone | GitHub Code Branch / Package | Key Concept Implemented |
| :--- | :--- | :--- |
| **#0: [Introduction to the Series](https://medium.com/google-cloud/adk2-0-101-0-introduction-to-the-series-42a36f19b077)** | Just Theory | Series overview, architecture blueprints, and prerequisites. |
| **#1: [LlmAgent Class and How to Run Agents](https://medium.com/google-cloud/adk2-0-101-1-llmagent-class-and-how-to-run-agents-7908277a35ed)** | [`01-first-agent`](https://github.com/EilinLux/adk2.0-medium/tree/01-first-agent) | Setting up the declarative system environment and Google ADK 2.0 `LlmAgent`. |
| **#2a: [Digital Assembly Line - 1st Pillar](https://medium.com/google-cloud/adk2-0-101-2a-digital-assembly-line-1st-pillar-f43b082509bb)** | Just Theory | Architectural foundation and assembly line patterns for multi-agent execution. |
| **#2b: [Sosta App as Multi-Agent Workflow](https://medium.com/@ailluzdatascience/list/agent-developer-kit-adk-5d957c62e9a9)** | [`02b-multi-agent-workflow`](https://github.com/EilinLux/adk2.0-medium/tree/02b-multi-agent-workflow) | Implementing Sosta's hierarchical multi-agent workflow (`Gatekeeper`, `Registratore`, `Cameriere`) and scoped tools. |
| **#2c: [Sosta as GraphWorkflow and Nodes in Multi-Agent Workflow](https://medium.com/@ailluzdatascience/list/agent-developer-kit-adk-5d957c62e9a9)** | [`02c-graph-agent-workflow`](https://github.com/EilinLux/adk2.0-medium/tree/02c-graph-agent-workflow) <br> ([`tests/02c-graph-agent-workflows`](https://github.com/EilinLux/adk2.0-medium/tree/02c-graph-agent-workflow/tests/02c-graph-agent-workflows)) | Refactoring loose LLM orchestration into a rigid Directed Acyclic Graph (`Workflow`) across 3 progressive test implementations:<br>• [**1. `agent_basic_graphworkflow`**](https://github.com/EilinLux/adk2.0-medium/tree/02c-graph-agent-workflow/tests/02c-graph-agent-workflows/agent_basic_graphworkflow): Naive graph (`START -> gatekeeper_agent -> router`) without a HITL pause—demonstrates *"The Silence of the Graph"* where execution skips waiting for user input.<br>• [**2. `agent_with_requestinput`**](https://github.com/EilinLux/adk2.0-medium/tree/02c-graph-agent-workflow/tests/02c-graph-agent-workflows/agent_with_requestinput): Adds a Human-in-the-Loop pause via `yield RequestInput(...)` (`START -> ask_user_for_id -> router`), passing raw user text to a deterministic router (succeeds on exact ID `"usr_12345"`, fails on natural sentences).<br>• [**3. `agent_with_requestinput_and_extractor`**](https://github.com/EilinLux/adk2.0-medium/tree/02c-graph-agent-workflow/tests/02c-graph-agent-workflows/agent_with_requestinput_and_extractor): Hybrid production pipeline (`START -> ask_user_for_id -> extractor_agent -> router`) combining `RequestInput`, an LLM semantic parser (`output_schema=UserExtraction`), and a deterministic Python router (`Event(route=...)`). |
| **#3a: [Digital Assembly Line - 2nd Pillar (Session & Session States)](https://medium.com/@ailluzdatascience/list/agent-developer-kit-adk-5d957c62e9a9)** | [`03a-session-state`](https://github.com/EilinLux/adk2.0-medium/tree/03a-session-state) <br> ([`tests/03a-session-state`](https://github.com/EilinLux/adk2.0-medium/tree/03a-session-state/tests/03a-session-state)) | Deep-dive into ADK's state mechanics across 6 progressive test scripts:<br>• [**1. `session_test_1_output_key.py`**](https://github.com/EilinLux/adk2.0-medium/blob/03a-session-state/tests/03a-session-state/session_test_1_output_key.py): `output_key` *without* `output_schema` (stores raw unstructured LLM text into `session.state`).<br>• [**2. `session_test_2_output_key_with_output_schema.py`**](https://github.com/EilinLux/adk2.0-medium/blob/03a-session-state/tests/03a-session-state/session_test_2_output_key_with_output_schema.py): `output_key` paired with a Pydantic `output_schema` (saves validated structured JSON into `session.state`).<br>• [**3. `session_test_3_output_schema_without_output_key.py`**](https://github.com/EilinLux/adk2.0-medium/blob/03a-session-state/tests/03a-session-state/session_test_3_output_schema_without_output_key.py): `output_schema` *without* `output_key` (returns structured JSON in the turn response while leaving `session.state` untouched).<br>• [**4. `session_test_4_output_key_with_output_schema_dict.py`**](https://github.com/EilinLux/adk2.0-medium/blob/03a-session-state/tests/03a-session-state/session_test_4_output_key_with_output_schema_dict.py): Nested dictionary extraction (`preferences: dict[str, Any]`) into `session.state["user_information"]`.<br>• [**5. `session_test_5_variable_injection.py`**](https://github.com/EilinLux/adk2.0-medium/blob/03a-session-state/tests/03a-session-state/session_test_5_variable_injection.py): Dynamic prompt templating via `{variable}` injection (plain `{user_information}`, scoped `{user:user_preferred_language}`, and optional `{special_notes?}`).<br>• [**6. `session_test_6_state_layers.py`**](https://github.com/EilinLux/adk2.0-medium/blob/03a-session-state/tests/03a-session-state/session_test_6_state_layers.py): End-to-end verification of ADK's 4 persistence scopes (`session`, `user:`, `app:`, and ephemeral `temp:`) across multiple users and sessions. |
| **#3b: [Session Service & Persistence Backends](https://medium.com/@ailluzdatascience/list/agent-developer-kit-adk-5d957c62e9a9)** | [`03b-session-service`](https://github.com/EilinLux/adk2.0-medium/tree/03b-session-service) <br> ([`tests/03b-session-service`](https://github.com/EilinLux/adk2.0-medium/tree/03b-session-service/tests/03b-session-service)) | Managing the `SessionService` lifecycle (CRUD), writing directly to live session state inside tools via `ToolContext`, swapping backends (`InMemorySessionService`, `DatabaseSessionService`, `VertexAiSessionService`), and extending `BaseSessionService` for custom enterprise stores:<br>• [**1. `session_service_1_inmemory.py`**](https://github.com/EilinLux/adk2.0-medium/blob/03b-session-service/tests/03b-session-service/session_service_1_inmemory.py): `InMemorySessionService` CRUD lifecycle and `ToolContext` state updates.<br>• [**2. `session_service_2_db_sql.py`**](https://github.com/EilinLux/adk2.0-medium/blob/03b-session-service/tests/03b-session-service/session_service_2_db_sql.py): Relational persistence using `DatabaseSessionService` (SQLite / SQLAlchemy).<br>• [**3. `session_service_3_custom.py`**](https://github.com/EilinLux/adk2.0-medium/blob/03b-session-service/tests/03b-session-service/session_service_3_custom.py): Custom enterprise persistence backend extending `BaseSessionService` (e.g., Google Cloud Firestore). |
| **#3c: [Memory Service & Long-Term Semantic Recall](https://medium.com/@ailluzdatascience/list/agent-developer-kit-adk-5d957c62e9a9)** | [`03c-memory-service`](https://github.com/EilinLux/adk2.0-medium/tree/03c-memory-service) <br> ([`tests/03c-memory-service`](https://github.com/EilinLux/adk2.0-medium/tree/03c-memory-service/tests/03c-memory-service)) | Cross-session long-term recall using ADK's `MemoryService` across 3 progressive test scripts:<br>• [**1. `memory_test_1_inmemory.py`**](https://github.com/EilinLux/adk2.0-medium/blob/03c-memory-service/tests/03c-memory-service/memory_test_1_inmemory.py): `InMemoryMemoryService` keyword-based cross-session recall (`add_session_to_memory` + `search_memory`).<br>• [**2. `memory_test_2_VertexAiMemoryBankService_Manual.py`**](https://github.com/EilinLux/adk2.0-medium/blob/03c-memory-service/tests/03c-memory-service/memory_test_2_VertexAiMemoryBankService_Manual.py): Managed LLM-consolidated semantic memory with `VertexAiMemoryBankService` and explicit `search_memory()` injection into `user:prior_context`.<br>• [**3. `memory_test_3_VertexAiMemoryBankService_in_Runner.py`**](https://github.com/EilinLux/adk2.0-medium/blob/03c-memory-service/tests/03c-memory-service/memory_test_3_VertexAiMemoryBankService_in_Runner.py): Automated memory retrieval by wiring `VertexAiMemoryBankService` directly into `Runner(..., memory_service=memory_service)` with ADK's built-in `preload_memory` and `load_memory` tools. |
| **#3d: [Application DB & `user:` State in Sosta App](https://medium.com/@ailluzdatascience/list/agent-developer-kit-adk-5d957c62e9a9)** | [`03d-session-state-sostaapp`](https://github.com/EilinLux/adk2.0-medium/tree/03d-session-state-sostaapp) <br> ([`adk_agent_app`](https://github.com/EilinLux/adk2.0-medium/tree/03d-session-state-sostaapp/adk_agent_app) & [`terraform`](https://github.com/EilinLux/adk2.0-medium/tree/03d-session-state-sostaapp/terraform)) | Separating the primary Firestore Application Database (`adk-agent-dev-application-db-fs`) from ADK's working Session State (`user:` scope):<br>• [**`terraform/`**](https://github.com/EilinLux/adk2.0-medium/tree/03d-session-state-sostaapp/terraform): Infrastructure-as-Code provisioning for Firestore databases, BigQuery dataset, and GCS bucket, plus seeding scripts.<br>• [**`gatekeeper_tools.py`**](https://github.com/EilinLux/adk2.0-medium/blob/03d-session-state-sostaapp/adk_agent_app/tools/gatekeeper_tools.py): `is_registered_user` verifies user IDs against Firestore (`users` collection) and hydrates `user:` session state at login.<br>• [**`registratore_agent_tools.py`**](https://github.com/EilinLux/adk2.0-medium/blob/03d-session-state-sostaapp/adk_agent_app/tools/registratore_agent_tools.py): `save_new_user` writes new user profiles directly to the Firestore Application DB.<br>• [**`cameriere_agent_tools.py`**](https://github.com/EilinLux/adk2.0-medium/blob/03d-session-state-sostaapp/adk_agent_app/tools/cameriere_agent_tools.py): `extract_user_profile` (self-healing fallback hydration) and `update_dietary_preferences` (dual-write pattern updating both `tool_context.state["user:culinary_preferences"]` and Firestore). |
| **#4a: [Evaluating Your Agents](https://medium.com/@ailluzdatascience/list/agent-developer-kit-adk-5d957c62e9a9)** | [`04a-evaluating-with-adk`](https://github.com/EilinLux/adk2.0-medium/tree/04a-evaluating-with-adk) <br> ([`adk_agent_app/evals`](https://github.com/EilinLux/adk2.0-medium/tree/04a-evaluating-with-adk/adk_agent_app/evals)) | Evaluating both Final Response Quality (`response_match_score`) and Tool Trajectory (`tool_trajectory_avg_score`) using ADK `.evalset.json` datasets captured from the ADK Web UI:<br>• [**`eval_config.json`**](https://github.com/EilinLux/adk2.0-medium/blob/04a-evaluating-with-adk/adk_agent_app/evals/eval_config.json): Configures evaluation criteria thresholds (`tool_trajectory_avg_score: 1.0`, `response_match_score: 0.50`).<br>• [**`eval_set_1_new_user.evalset.json`**](https://github.com/EilinLux/adk2.0-medium/blob/04a-evaluating-with-adk/adk_agent_app/evals/eval_set_1_new_user.evalset.json): Multi-turn evaluation cases for new user onboarding (`Gatekeeper -> Registratore -> save_new_user -> Cameriere -> extract_user_profile`).<br>• [**`eval_set_2_existing_user.evalset.json`**](https://github.com/EilinLux/adk2.0-medium/blob/04a-evaluating-with-adk/adk_agent_app/evals/eval_set_2_existing_user.evalset.json): Multi-turn evaluation case for returning registered user (`usr_0a8f67`) verifying profile hydration and dietary preference clarification. |
| **#4b: [Running Evaluations with `adk eval`](https://medium.com/@ailluzdatascience/list/agent-developer-kit-adk-5d957c62e9a9)** | [`04b-evaluating-with-adk-run`](https://github.com/EilinLux/adk2.0-medium/tree/04b-evaluating-with-adk-run) <br> ([`adk_agent_app/evals`](https://github.com/EilinLux/adk2.0-medium/tree/04b-evaluating-with-adk-run/adk_agent_app/evals)) | Running and debugging multi-turn evaluation suites via the `adk eval` CLI (`--print_detailed_results` & `--config_file_path`), resolving relative imports, deterministic per-user ID hashing (`ADK_EVAL_MODE=true`), session isolation across parallel eval cases, and imperative handoff prompts. |
| **#5a: [Tools, Input/Output Schemas & `AgentTool`](https://medium.com/@ailluzdatascience/list/agent-developer-kit-adk-5d957c62e9a9)** | [`05a-tools-and-input-output-schemas`](https://github.com/EilinLux/adk2.0-medium/tree/05a-tools-and-input-output-schemas) <br> ([`adk_agent_app`](https://github.com/EilinLux/adk2.0-medium/tree/05a-tools-and-input-output-schemas/adk_agent_app) & [`tests/05a-tools-and-input-output-schemas`](https://github.com/EilinLux/adk2.0-medium/tree/05a-tools-and-input-output-schemas/tests/05a-tools-and-input-output-schemas)) | Production-grade tool design (`FunctionTool`, Google-style docstrings, type hints, and structured dictionary return payloads), Pydantic `input_schema` / `output_schema` contracts, introducing `Suggeritore` with `AgentTool` (`RoutePlannerAgent`, `SosteSearchAgent`, `MenuCheckerAgent`), full end-to-end evaluation ([`eval_set_3_full_workflow_suggeritore.evalset.json`](https://github.com/EilinLux/adk2.0-medium/blob/05a-tools-and-input-output-schemas/adk_agent_app/evals/eval_set_3_full_workflow_suggeritore.evalset.json)), and testing the `output_schema` + `tools` separation pattern:<br>• [**1. `schema_tools_test_1_single_agent_conflict.py`**](https://github.com/EilinLux/adk2.0-medium/blob/05a-tools-and-input-output-schemas/tests/05a-tools-and-input-output-schemas/schema_tools_test_1_single_agent_conflict.py): Anti-pattern showing how attaching `output_schema=RegistrationSummaryOutput` directly to a conversational tool-calling agent forces premature/fabricated JSON output before all required tool parameters are gathered.<br>• [**2. `schema_tools_test_2_two_agent_split.py`**](https://github.com/EilinLux/adk2.0-medium/blob/05a-tools-and-input-output-schemas/tests/05a-tools-and-input-output-schemas/schema_tools_test_2_two_agent_split.py): Production 2-station pipeline (`Workflow`) separating the Tool Agent (`save_new_user_tool` $\rightarrow$ `output_key="raw_registration_result"`) from the Schema Formatter Agent (`RegistrationFormatter` $\rightarrow$ `output_schema=RegistrationSummaryOutput`). |

---

## 🤖 Micro-Agent Directory

* **Gatekeeper:** Authentication guardrail and entry-point orchestrator. Validates user accounts and routes users to the appropriate flow.
* **Registratore:** Onboarding specialist. Collects culinary preferences, dietary restrictions, and vehicle specifications for new users.
* **Cameriere:** Session coordinator. Retrieves stored user profiles, gathers active trip context (companions, final destination), and prepares context for search.
* **Suggeritore:** Matching engine. Queries stop databases, filters by charging compatibility, and surfaces optimal stop suggestions.

---

## 📦 Installation & Setup

1a. **Clone the repository:**

```bash
git clone https://github.com/EilinLux/adk2.0-medium.git
cd adk2.0-medium
```

1b. **Fetch and list all available article branches:**

```bash
git fetch origin
git branch -a
```

1c. **Switch (checkout) to a specific remote article branch:**
To follow along with a specific Medium article, create and switch to a local branch tracking the remote branch:

```bash
git checkout -b <branch-name> origin/<branch-name>
```

Example for this article (`04b-evaluating-with-adk-run`):

```bash
git checkout -b 04b-evaluating-with-adk-run origin/04b-evaluating-with-adk-run
```

2. **Install dependencies:**

```bash
uv sync
```

3. **Configure environment variables:**
Create a `.env` file in the root directory and populate it with your GCP and database identifiers:

```env
# ============================================================================
# OPTION A: Vertex AI Configuration (Recommended for Google Cloud Production)
# ============================================================================
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=adk-workshop-sosta-app-dev
GOOGLE_CLOUD_LOCATION=europe-west1
APP_NAME=sosta_app
ADK_SUPPRESS_EXPERIMENTAL_FEATURE_WARNINGS=1

# ============================================================================
# GCP Infrastructure & Database Identifiers (used by adk_agent_app/config.py)
# ============================================================================
ENVIRONMENT=dev
FIRESTORE_APP_DB=adk-agent-dev-application-db-fs
FIRESTORE_SESSION_DB=adk-agent-dev-session-memory-fs
FIRESTORE_FOOD_KB_DB=adk-agent-dev-food-kb-fs
BIGQUERY_DATASET=soste_app_dev
BIGQUERY_TABLE=db_soste
GCS_BUCKET=adk-agent-dev-product-specs

# ============================================================================
# OPTION B: Google AI Studio Configuration (Alternative via API Key)
# ============================================================================
# GOOGLE_GENAI_USE_VERTEXAI=0
# GOOGLE_API_KEY=your_gemini_api_key_here
```

4. **Authenticate with Google Cloud & Provision Infrastructure:**
Follow the instructions in [`terraform/README.md`](file:///Users/zelda.luconi/Medium/adk2.0-testing-env/adk2.0-medium/terraform/README.md) to provision and seed the Firestore and BigQuery resources, then authenticate locally:

```bash
gcloud auth application-default login
```

5. **Run Pre-Flight Connectivity Checks, Launch the Sosta App & Run Evaluations:**

```bash
# 1. Verify connectivity to Firestore, BigQuery, and Cloud Storage
uv run python adk_agent_app/test_connections.py

# 2. Launch the interactive ADK Dev UI for the Sosta app (to inspect traces and create evalsets)
uv run adk web

# 3. Run the Sosta App evaluation suites from the CLI
ADK_EVAL_MODE=true uv run adk eval adk_agent_app adk_agent_app/evals/eval_set_1_new_user.evalset.json --config_file_path=adk_agent_app/evals/eval_config.json --print_detailed_results
ADK_EVAL_MODE=true uv run adk eval adk_agent_app adk_agent_app/evals/eval_set_2_existing_user.evalset.json --config_file_path=adk_agent_app/evals/eval_config.json --print_detailed_results
ADK_EVAL_MODE=true uv run adk eval adk_agent_app adk_agent_app/evals/eval_set_3_full_workflow_suggeritore.evalset.json --config_file_path=adk_agent_app/evals/eval_config.json --print_detailed_results
```
