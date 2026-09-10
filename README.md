# ADK 2.0 101: Agent Developer Kit Implementation

This repository contains the codebase and architecture blueprints for the **ADK 101** tutorial series published on Medium by *Zelda Ailine Luconi*. 

The project demonstrates how to move away from fragile, notebook-bound AI prototypes and build production-grade, event-driven AI agents using **Google's Agent Developer Kit (ADK) 2.0**, Agentic Architecture best practices**.

## 🚀 Project Overview: Sosta App

The primary implementation built throughout this series is **Sosta App**—an intelligent travel optimization platform designed to eliminate "range anxiety" and "choice fatigue" for travelers. 

### 🛠️ Core Agent Architecture

Here is a polished, production-ready `README.md` for your repository, incorporating all the structural upgrades, visual flowcharts, complete branch mappings, and explicit run commands.

---

# ADK 2.0 101: Agent Developer Kit Implementation

This repository contains the codebase, micro-agent implementations, and architectural blueprints for the **ADK 101** tutorial series published on Medium by *Zelda Ailine Luconi*.

The project demonstrates how to move away from fragile, notebook-bound AI prototypes and build production-grade, event-driven AI agents using **Google's Agent Developer Kit (ADK) 2.0** and enterprise agentic design principles.

---

## 🚀 Project Overview: Sosta App

The primary application built throughout this series is **Sosta**—an intelligent travel optimization platform designed to eliminate "range anxiety" and "choice fatigue" for electric vehicle travelers.

Instead of relying on a monolithic prompt, Sosta is architected as a **Digital Assembly Line**: a network of specialized, single-responsibility micro-agents collaborating through typed schemas and deterministic workflows.


## 🗺️ Series Roadmap & Companion Branches

Each article in the series corresponds to a dedicated git branch containing clean, structured Python code (managed via `uv` with standard `pyproject.toml` configuration).

Here is the review of your proposed **Part 3d ("Runners in ADK")** content, followed by the revised series roadmap table with Part 3d incorporated.

---

### Part 1: Editorial & Technical Review of Part 3d

Your proposed draft for **Part 3d** (`Runners in ADK — the orchestrator you never see but always need`) bridges a crucial gap in ADK architecture.

#### Key Feedback & Technical Refinements

1. **Clarified Role in Roadmap**:
Article 3d explains **how execution happens**—decoupling agent prompts from storage, handling event streaming, tool recursion limits (`RunConfig`), and managing the execution lifecycle.
2. **Fixed Typos & Terminology**:
* `"light-motive"` $\rightarrow$ `leitmotif` (or `guiding principle`)
* `"privious"` $\rightarrow$ `previous`
* `"shouòd"` $\rightarrow$ `should`
* Fixed renumbering in section titles (Section `03` followed `01` directly in your TOC).


3. **PEP 8 Code Cleanliness**:
Standardized `InMemoryRunner` vs `Runner` code examples and imports to ensure all snippets match clean Python conventions.

---

### Part 2: Complete Series Roadmap Table (Filled In)

Here is the updated series table incorporating **Article 3d**:

| Medium Article & Milestone | GitHub Branch | Key Concept & Technical Implementation | Architectural Pattern |
| --- | --- | --- | --- |
| **#1 · Environment Setup & First Agent** | [`01-first-agent`](https://github.com/EilinLux/adk2.0-medium/tree/01-first-agent) | Declarative environment setup using `uv` and `pyproject.toml`. Instantiating the foundational `Agent` class, configuring prompt instructions, and testing execution across three local runtimes (`adk run`, `adk web`, and programmatic Python invocation). | **Single-Agent Baseline** |
| **#2a · Assembly Line Principles** | *(Theory / `main`)* | Deconstructing monolithic prompt traps into modular micro-agents using Henry Ford’s assembly line principles. Establishing the 4 core pillars: structured workflows, typed JSON handoffs, technological model heterogeneity, and dual-layer state management (*Travel Sheet* session context vs. *Warehouse* persistent storage). | **System Architecture Blueprint** |
| **#2b · Multi-Agent Workflows** | [`02b-multi-agent-workflow`](https://github.com/EilinLux/adk2.0-medium/tree/02b-multi-agent-workflow) | Building a hierarchical collaborative team. Implements local tool scoping (`tools=[is_registered_user_tool]`) to enforce the Principle of Least Privilege and eliminate context bloat. Establishes parent-child supervisor delegation (`sub_agents=[registratore, cameriere]`) for dynamic LLM-driven task handoffs. | **Hierarchical Collaborative Team** |
| **#2c · Graph Workflows & HITL** | [`02c-graph-agent-workflows`](https://www.google.com/search?q=https://github.com/EilinLux/adk2.0-medium/tree/02c-graph-agent-workflows) | Refactoring loose LLM orchestration into a rigid Directed Acyclic Graph (`Workflow`). Implements Human-in-the-Loop (HITL) pauses via `RequestInput` generators, semantic extraction using Pydantic schemas (`output_schema=UserExtraction`), and prompt-injection-proof Python edge routers (`Event(route=...)`). | **Deterministic Pipeline (DAG)** |
| **#3a · Session & Session States** | [`03a-session-state`](https://www.google.com/search?q=https://github.com/EilinLux/adk2.0-medium/tree/03a-session-state) | Deep-dive into ADK's state mechanics. Automating entity extraction into state via `output_schema` and `output_key`, dynamic prompt templating using `{variable}` injection, and isolating variables across four distinct persistence scopes (`session`, `user:`, `app:`, and `temp:`). | **State & Context Management** |


## 🤖 Micro-Agent Directory

* **Gatekeeper:** Authentication guardrail and entry-point orchestrator. Validates user accounts and routes users to the appropriate flow.
* **Registratore:** Onboarding specialist. Collects culinary preferences, dietary restrictions, and vehicle specifications for new users.
* **Cameriere:** Session coordinator. Retrieves stored user profiles, gathers active trip context (companions, final destination), and prepares context for search.
* **Suggeritore:** Matching engine. Queries stop databases, filters by charging compatibility, and surfaces optimal stop suggestions.

---

## 📦 Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/EilinLux/adk2.0-medium.git
cd adk2.0-medium

```

### 2. Install dependencies with `uv`

This project uses [`uv`](https://github.com/astral-sh/uv) for lightning-fast, deterministic Python package management.

```bash
uv sync

```

### 3. Configure environment variables

Create a `.env` file in the root directory:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_CLOUD_PROJECT=your_gcp_project_id

```

### 4. Authenticate Google Cloud (Optional / Vertex AI)

If using Vertex AI runtimes instead of direct API keys:

```bash
gcloud auth application-default login

```

---

## ⚡ Quick Start: Running the Agents

Switch to your target branch to test the specific implementation pattern:

```bash
git checkout 02-multi-agent-workflow

```

### Run via ADK Terminal CLI

Interact with the agent directly inside your terminal:

```bash
uv run adk run adk_agent_app/agent.py

```

### Run via Interactive Web UI

Launch ADK's built-in web viewer to inspect turn-by-turn trace logs, tool executions, and state changes:

```bash
uv run adk web adk_agent_app/agent.py

```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](https://www.google.com/search?q=LICENSE) file for details.


