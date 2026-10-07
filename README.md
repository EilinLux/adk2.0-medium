# ADK 2.0 101: Agent Developer Kit Implementation

This repository contains the codebase and architecture blueprints for the **ADK 101** tutorial series published on Medium by *Zelda Ailine Luconi*. 

You can access the full series list and updates directly on Medium:
📚 **[Medium Article Series List](https://medium.com/@ailluzdatascience/list/agent-developer-kit-adk-5d957c62e9a9)**

The project demonstrates how to move away from fragile, notebook-bound AI prototypes and build production-grade, event-driven AI agents using **Google's Agent Developer Kit (ADK) 2.0** and agentic architecture best practices.

---

## 🚀 Repository Structure & Branching Strategy

To keep the codebase clean, isolated, and easy to follow, **each article in the Medium series corresponds to a dedicated Git branch** (e.g., `01-first-agent`, `02b-multi-agent-workflow`, `02c-graph-agent-workflow`, `03a-session-state`).

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

Example for this article (`03a-session-state`):

```bash
git checkout -b 03a-session-state origin/03a-session-state
```

2. **Install dependencies:**

```bash
uv sync
```

3. **Configure environment variables:**
Create a `.env` file in the root directory (or inside `adk_agent_app/.env`) and populate it with your required variables (note that exact variables depend on the Medium article you are reading):

```env
# ============================================================================
# OPTION A: Vertex AI Configuration (Recommended for Google Cloud Production)
# ============================================================================
# Set to 1 (or TRUE) to route requests through Google Cloud Vertex AI
GOOGLE_GENAI_USE_VERTEXAI=1

# Your Google Cloud Project ID where Vertex AI API is enabled
GOOGLE_CLOUD_PROJECT=adk-workshop-sosta-app-dev

# The GCP region for Vertex AI model execution (e.g., us-central1, europe-west1)
GOOGLE_CLOUD_LOCATION=europe-west1

# Application identifier used by ADK session/runner services
APP_NAME=sosta_app

# Optional: Silence ADK's [EXPERIMENTAL] CredentialService CLI warnings
ADK_SUPPRESS_EXPERIMENTAL_FEATURE_WARNINGS=1

# ============================================================================
# OPTION B: Google AI Studio Configuration (Alternative via API Key)
# ============================================================================
# If using a Gemini API Key instead of Vertex AI, set GOOGLE_GENAI_USE_VERTEXAI=0
# and uncomment your API key below:
# GOOGLE_GENAI_USE_VERTEXAI=0
# GOOGLE_API_KEY=your_gemini_api_key_here
```

4. **Authenticate with Google Cloud (when using Vertex AI):**

```bash
gcloud auth application-default login
```

5. **Run the Agents & Session State Tests:**

```bash
# Launch the interactive ADK Dev UI for the main Sosta app
uv run adk web

# Or run the 03a Session State test scripts directly with Python:
uv run python tests/03a-session-state/session_test_1_output_key.py
uv run python tests/03a-session-state/session_test_2_output_key_with_output_schema.py
uv run python tests/03a-session-state/session_test_3_output_schema_without_output_key.py
uv run python tests/03a-session-state/session_test_4_output_key_with_output_schema_dict.py
uv run python tests/03a-session-state/session_test_5_variable_injection.py
uv run python tests/03a-session-state/session_test_6_state_layers.py
```
