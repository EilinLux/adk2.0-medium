# ADK 2.0 101: Agent Developer Kit Implementation

This repository contains the codebase and architecture blueprints for the **ADK 101** tutorial series published on Medium by *Zelda Ailine Luconi*. 

The project demonstrates how to move away from fragile, notebook-bound AI prototypes and build production-grade, event-driven AI agents using **Google's Agent Developer Kit (ADK) 2.0**, Agentic Architecture best practices**.

## 🚀 Project Overview: Sosta App

The primary implementation built throughout this series is **Sosta App**—an intelligent travel optimization platform designed to eliminate "range anxiety" and "choice fatigue" for travelers. 

### 🛠️ Core Agent Architecture

| Medium Article & Milestone | GitHub Code Branch / Package | Key Concept Implemented |
| :--- | :--- | :--- |
| **#1: LlmAgent Class and how to run agents** | [01-first-agent](https://github.com/EilinLux/adk2.0-medium/tree/01-first-agent) | Setting up the declarative system environment and Google ADK 2.0 LlmClass(). |

---

## 📦 Installation & Setup

1. **Clone the repository:**
```bash
git clone https://github.com/EilinLux/adk101-medium.git
cd adk101-medium

```


2. **Install dependencies:**
```bash
uv sync

```


3. **Configure environment variables:**
Create a `.env` file in the root directory and populate it with your required variables:
```env
# Add your environment variables here

```


4. **Authenticate with Google Cloud:**
```bash
gcloud auth application-default login

```


5. **Run tests:**
Switch to your target branch and verify the setup:
```bash
git checkout <branch-name>

```