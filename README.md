# 🛡️ Sentinel

**An autonomous SRE agent that monitors containers, diagnoses failures, and takes action.**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Google ADK](https://img.shields.io/badge/Google-ADK-4285F4.svg)](https://github.com/google/adk-python)
[![DSPy](https://img.shields.io/badge/DSPy-Optimized-orange.svg)](https://github.com/stanfordnlp/dspy)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)

---

## What is this?

Sentinel is an AI agent that acts like a Site Reliability Engineer. Give it a container name, and it will:

1. **Fetch logs** from Docker
2. **Analyze them** for root causes using a trained DSPy brain
3. **Recommend actions** (restart, escalate, or ignore)
4. **Execute fixes** automatically when appropriate

The interesting part isn't that it uses an LLM—it's *how* it uses one. Instead of raw prompting, Sentinel uses **DSPy** to compile optimized few-shot examples from training data. This makes it way more reliable for production incidents.

---

## Architecture

┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Server                         │
│                     (api_server.py)                         │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                     Sentinel Agent                          │
│                  (Google ADK + Gemini)                      │
│                                                             │
│  ┌──────────────────┐      ┌──────────────────────────────┐ │
│  │   MCP Toolset    │      │      SRE Brain (DSPy)        │ │
│  │                  │      │                              │ │
│  │ • list_containers│      │ • Chain-of-Thought reasoning │ │
│  │ • get_logs       │◄────►│ • Trained on incident data   │ │
│  │ • restart_service│      │ • Outputs: cause + action    │ │
│  │                  │      │                              │ │
│  └────────┬─────────┘      └──────────────────────────────┘ │
└───────────┼─────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Docker Daemon                          │
│                    (Your containers)                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Features

- 🔍 **Automated Log Analysis** - Fetches and analyzes container logs without manual intervention
- 🧠 **DSPy-Trained Brain** - Uses compiled few-shot examples, not raw prompting
- 🔧 **MCP Tool Integration** - Docker operations exposed via Model Context Protocol
- 🔄 **Smart Decision Making** - Knows when to restart vs. when to escalate
- 🌐 **REST API** - FastAPI server with Swagger docs for easy integration
- 💬 **Session Memory** - Maintains conversation context across requests

---

## Tech Stack

| Technology | Purpose |
|------------|---------|
| **Google ADK** | Agent orchestration framework |
| **Gemini 2.5 Flash** | Fast, capable LLM for reasoning |
| **DSPy** | Prompt optimization via few-shot compilation |
| **FastMCP** | Model Context Protocol server for tools |
| **FastAPI** | REST API with async support |
| **Docker SDK** | Container management |
| **DeepEval** | LLM behavior testing |

---

### Prerequisites

- Python 3.12+
- Docker running locally
- Google API key (Gemini access)

## Project Structure

```
sentinel/
├── api_server.py          # FastAPI REST interface
├── agents/
│   └── sentinel_agent.py  # Core agent logic + REPL
├── modules/
│   ├── rca_brain.py       # DSPy module for RCA
│   ├── train_brain.py     # Training script
│   └── brain_compiled.json # Optimized weights
├── servers/
│   └── ops_server.py      # MCP server (Docker tools)
├── tests/
│   └── test_logic.py      # Behavior tests
├── pyproject.toml
└── requirements.txt
```
---

## How It Works

### 1. Tool Integration via MCP

The agent connects to `ops_server.py` via stdin/stdout using the Model Context Protocol. This gives it three tools:

- `list_active_containers()` - See what's running
- `get_container_logs(name, tail)` - Fetch recent logs
- `restart_service(name)` - Restart a container

### 2. Analysis via DSPy Brain

When the agent spots errors in logs, it calls `consult_sre_expert()`. This routes through our DSPy module, which:

1. Uses Chain-of-Thought to reason step-by-step
2. Outputs structured fields: `root_cause`, `severity`, `suggested_action`
3. Draws on few-shot examples compiled during training

### 3. Why DSPy Instead of Raw Prompting?

Raw prompts are brittle. Small changes in log format can break them. DSPy lets us:

- Define a **typed contract** (inputs → outputs)
- **Compile** optimized prompts from training examples
- **Validate** outputs match expected patterns

The compiled brain in `brain_compiled.json` contains few-shot examples that dramatically improve accuracy.

---

## Key Learnings

Building this taught me a few things:

1. **MCP is underrated** - Separating tools into a subprocess makes them reusable across agents
2. **DSPy > prompt engineering** - For structured outputs, compilation beats hand-tuning
3. **Test LLM behavior, not just outputs** - The `test_logic.py` approach catches subtle bugs
4. **Session state matters** - ADK's session service makes multi-turn conversations trivial

---

## Author

Built by [Kunj Patel](https://linkedin.com/in/kunjpatel101) as an exploration of agentic AI for DevOps.

Questions? Open an issue or reach out on LinkedIn!
