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
| **#1: [LlmAgent Class and How to Run Agents](https://medium.com/google-cloud/adk2-0-101-1-llmagent-class-and-how-to-run-agents-7908277a35ed)** | [`01-first-agent`](https://github.com/EilinLux/adk2.0-medium/tree/01-first-agent) | Setting up the declarative system environment and Google ADK 2.0 `LlmClass()`. |
| **#2a: [Digital Assembly Line - 1st Pillar](https://medium.com/google-cloud/adk2-0-101-2a-digital-assembly-line-1st-pillar-f43b082509bb)** | Just Theory | Architectural foundation and assembly line patterns for multi-agent execution. |
| **#2b: Multi-Agents Workflows** | [`02b-multi-agent-workflow`](https://github.com/EilinLux/adk2.0-medium/tree/02b-multi-agent-workflow) | Draft the Agents workflow except for Suggeritore. |


---

## 📦 Installation & Setup

1a. **Clone the repository:**

```
Bash
git clone https://github.com/EilinLux/adk101-medium.git
cd adk101-medium
```

1b. **List all available article branches:**

```
Bash
git branch -a
```

1c. **Switch (checkout) to a specific article branch:**
To follow along with a specific Medium article, switch directly to its corresponding branch:

```
Bash
git checkout <branch-name>
```

Example:

```
Bash
git checkout 01-first-agent
```

2. **Install dependencies:**
```bash
uv sync

```


3. **Configure environment variables:**
Create a `.env` file in the root directory and populate it with your required variables (keep in mind, this depoend on the Medium arcile you are reading):

```env
# Add your environment variables here
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=adk-workshop-sosta-app-dev
GOOGLE_CLOUD_LOCATION=europe-west1
APP_NAME=sosta_app
# GEMINI_API_KEY=...

```




4. **Authenticate with Google Cloud:**
```bash
gcloud auth application-default login

```
