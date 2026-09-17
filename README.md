<div align="center">
  <!-- <img src="docs/logo.png" alt="BurpNake Logo" width="200"/> -->
  <h1>BurpNake</h1>
  <p><b>Autonomous AI-Driven Penetration Testing & Bug Bounty Platform</b></p>

  [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
  [![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
  [![Node.js 18+](https://img.shields.io/badge/node.js-18+-green.svg)](https://nodejs.org/)
  [![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
</div>

<br />

## Table of Contents
- [Overview](#overview)
- [Screenshots](#screenshots)
- [Core Capabilities](#core-capabilities)
- [System Architecture](#system-architecture)
- [Detailed Installation Guide](#detailed-installation-guide)
- [LLM Configuration Guide](#llm-configuration-guide)
- [Legal Disclaimer](#legal-disclaimer)

---

## Overview

BurpNake is an advanced, AI-driven autonomous penetration testing and bug bounty platform. Unlike traditional static scanners, BurpNake leverages Large Language Models (LLMs) to perform semantic analysis of HTTP traffic, execute state-aware fuzzing, dynamically chain vulnerabilities, and automatically write Proof-of-Concept (PoC) scripts. 

It acts as an automated extension of a security researcher's mind, replicating the chain-of-thought process required to discover complex, multi-stage vulnerabilities.

---

## Screenshots

> **Note:** Screenshots of the live dashboard, AI chain builder, and active vulnerability fuzzing will be added here.

*   **Dashboard & Live Feed:**
    <!-- ![Dashboard Preview](link_to_dashboard_image) -->
    
*   **AI Chain Builder & Exploit Generation:**
    <!-- ![AI Chain Builder](link_to_chain_image) -->

*   **Autonomous Agent Execution:**
    <!-- ![Agent Execution](link_to_agent_image) -->

---

## Core Capabilities

*   **Semantic DOM Reconnaissance:** Parses HTML Abstract Syntax Trees (AST) using BeautifulSoup and lxml to extract hidden inputs, developer comments, and inline API endpoints, eliminating LLM hallucination during payload generation.
*   **Multi-Step Stateful Fuzzing:** Capable of executing complex, multi-stage attacks (e.g., account creation followed by privilege escalation). It maintains session state and cookies across HTTP requests dynamically.
*   **Dynamic Vulnerability Chaining:** An independent background AI agent continuously evaluates low-severity findings, querying the LLM to logically chain them into critical impacts (e.g., Self-XSS + Open Redirect into Account Takeover).
*   **Blind Vulnerability Differ:** Implements differential analysis on word counts, response lengths, and time delays to accurately detect blind injection vulnerabilities (Blind SQLi, Blind SSRF) without relying on visible errors.
*   **Robust LLM Gateway:** Built-in failover mechanism supporting local offline models (Ollama), cloud models (Gemini), and free open-source proxies (G4F).

---

## System Architecture

1.  **Traffic Interception:** A custom Java extension intercepts traffic from Burp Suite and forwards it to the BurpNake backend.
2.  **Triage & Passive Analysis:** The backend evaluates the traffic against 88 distinct vulnerability patterns and extracts DOM context.
3.  **Autonomous Agent Loop:** The AI takes control, deciding on the next attack vector, mutating payloads, and sending verification requests.
4.  **Reporting:** Confirmed vulnerabilities are formatted into HackerOne/Bugcrowd standard markdown reports with functional Python/cURL PoC scripts, streamed in real-time to the React frontend.

---

## Detailed Installation Guide

### Prerequisites
Before installing BurpNake, ensure your system meets the following requirements:
*   **Python 3.12** or higher (Required for the backend API and AI agent)
*   **Node.js 18** or higher (Required to build and run the React frontend)
*   **Java 11** or higher (Required to load the Burp Suite interceptor extension)
*   **Docker and Docker Compose** (Optional, but highly recommended for containerized deployment)

### Method 1: Docker Installation (Recommended)
The fastest and most reliable way to deploy the entire stack is using Docker Compose.

1.  **Clone the repository:**
    `ash
    git clone https://github.com/egnake/Burpnake.git
    cd Burpnake
    `
2.  **Prepare the environment variables:**
    `ash
    cp .env.example .env
    `
    Open the .env file in a text editor and configure your preferred LLM credentials (e.g., GEMINI_API_KEY or OLLAMA_BASE_URL).
3.  **Build and start the containers:**
    `ash
    docker-compose up --build
    `
4.  **Access the application:**
    *   Dashboard: http://localhost:3000
    *   Backend API Docs: http://localhost:8899/docs

### Method 2: Manual / Local Installation

If you prefer to run the applications directly on your host machine, follow these steps.

#### 1. Backend Setup (FastAPI)
1.  Clone the repository and navigate to the root directory.
2.  Create a virtual Python environment to isolate dependencies:
    `ash
    python -m venv venv
    `
3.  Activate the virtual environment:
    *   **Windows:** .\venv\Scripts\activate
    *   **Linux / macOS:** source venv/bin/activate
4.  Install the required Python packages:
    `ash
    pip install -r requirements.txt
    `
5.  Configure the environment variables:
    *   Copy the .env.example file and rename it to .env.
    *   Edit .env to include your API keys.
6.  Start the backend server:
    `ash
    python run.py
    `
    The backend API will start on http://localhost:8899.

#### 2. Frontend Setup (React + Vite)
1.  Open a new terminal window and navigate to the rontend directory:
    `ash
    cd frontend
    `
2.  Install the Node.js dependencies:
    `ash
    npm install
    `
3.  Start the frontend development server:
    `ash
    npm run dev
    `
    The frontend dashboard will start on http://localhost:3000.

#### 3. Burp Suite Extension Setup
BurpNake relies on a custom Burp Suite extension to capture HTTP traffic in real-time.
1.  Ensure Java is installed and Burp Suite is running.
2.  In Burp Suite, navigate to the **Extensions** tab, then select the **Installed** sub-tab.
3.  Click the **Add** button.
4.  Set the **Extension type** to **Java**.
5.  In the **Extension file (.jar)** field, click **Select file...** and navigate to the cloned repository. Select connector/BurpNakeConnector.jar.
6.  Click **Next**. The extension will load, and the output console should confirm that it has connected to the BurpNake backend on port 8899.

---

## LLM Configuration Guide

BurpNake requires a Large Language Model to operate its autonomous agents. You must configure at least one provider in your .env file.

*   **Ollama (Local & Private):** Best for sensitive targets where data cannot leave your machine.
    1. Install Ollama on your system.
    2. Pull a capable coding model (e.g., ollama pull qwen2.5-coder:14b or ollama pull llama3).
    3. Set OLLAMA_BASE_URL=http://localhost:11434 in your .env.
*   **Gemini (Cloud):** Highly recommended for complex DOM reasoning and long-context capabilities.
    1. Obtain an API key from Google AI Studio.
    2. Set GEMINI_API_KEY=your_api_key_here in your .env.
*   **G4F (Free Fallback):** If you do not have access to an API key, you can route requests through free community providers.
    1. Set G4F_ENABLED=true in your .env. Note that stability may vary based on provider availability.

---

## Legal Disclaimer

BurpNake is developed exclusively for authorized penetration testing and official bug bounty programs. The tool adheres to strictly configured scope rules to prevent unintended or unauthorized testing. The developers assume no liability and are not responsible for any misuse, damage, or legal consequences caused by the deployment of this software.

---

## License

MIT License