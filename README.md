# ADK 2.0 101: Agent Developer Kit Implementation

This repository contains the codebase and architecture blueprints for the **ADK 101** tutorial series published on Medium by *Zelda Ailine Luconi*. 

You can access the full series list and updates directly on Medium:
📚 **[Medium Article Series List](https://medium.com/@ailluzdatascience/list/agent-developer-kit-adk-5d957c62e9a9)**

The project demonstrates how to move away from fragile, notebook-bound AI prototypes and build production-grade, event-driven AI agents using **Google's Agent Developer Kit (ADK) 2.0** and agentic architecture best practices.

---

## 🚀 Repository Structure & Branching Strategy

To keep the codebase clean, isolated, and easy to follow, **each article in the Medium series corresponds to a dedicated Git branch** (e.g., `01-first-agent`, `02b-multi-agent-workflow`).

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

Example for this article (`02b-multi-agent-workflow`):

```bash
git checkout -b 02b-multi-agent-workflow origin/02b-multi-agent-workflow
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

5. **Run the Multi-Agent Workflow:**

```bash
# Launch the interactive ADK Dev UI in your browser
uv run adk web

# Or run the agent directly in the terminal
uv run adk run adk_agent_app
```
