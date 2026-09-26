# ApaKhabar AI Service - Architecture & Agentic Patterns

This document outlines the file structure, core responsibilities of each module, and the agentic AI patterns implemented in the ApaKhabar AI Service.

---

## 📂 File and Folder Structure

### 1. `app/api/` (FastAPI Routers)
This folder contains the HTTP endpoints that handle incoming requests from the Laravel backend.
* **`agent.py`**: Endpoints for running background agent tasks (starting runs, submitting approvals, getting events).
* **`document.py`**: Endpoints for document upload, normalisation (PDF, CSV, TXT, DOCX), and parsing.
* **`extraction.py`**: Triggers the AI extraction pipeline for processed documents.
* **`news.py`**: Endpoints for synchronous news generation requests.
* **`rag.py` / `knowledge.py`**: Endpoints for embedding generation and ChromaDB vector search.

### 2. `app/services/` (Core Business Logic)
The core Python services that power the application's AI and data capabilities.
* **`ai_service.py`**: The bridge between the application and the local LLM. It defines prompts and manages the structured extraction pipeline.
* **`extraction_service.py`**: Chunks normalized documents and calls `ai_service.py` to extract structured JSON information. It handles large tables and long text efficiently.
* **`document_service.py`**: Parses incoming files (CSV, PDF, Excel) into a standard `NormalizedDocument` schema.
* **`agent_service.py`**: Manages the persistence, checkpoints, and execution of the LangGraph agent runs using SQLite.
* **`rag_service.py`**: Chunks knowledge items, calculates embeddings, and stores them in ChromaDB.

### 3. `app/workflows/` (LangGraph Agents)
Contains the state machine definitions for the autonomous agents.
* **`editorial.py`**: Defines the `EditorialWorkflow`, a state graph modeling the entire research, drafting, and review process of the AI journalist.

### 4. `app/tools/` (Agent Tools)
* **`editorial.py`**: Defines the specific tools the LangGraph agent can call (e.g., `search_knowledge` for RAG).

### 5. `app/providers/` (Model Integration)
* **`models.py`**: HTTP wrappers for interacting with `llama.cpp` and `Ollama`. It enforces JSON schema compliance by injecting grammar constraints into the generation process.

### 6. `app/schemas/` (Pydantic Models)
Defines the strict type schemas used across the API, LangGraph state, and LLM structured outputs.
* **`agent.py`, `news.py`, `information.py`, `document.py`**: Enforce correct data structures at runtime.

### 7. `skills/` (Prompt Engineering & Personas)
Markdown-based prompt injection files loaded dynamically by the `SkillRegistry`.
* **`document-extraction/`**: Prompts for extracting facts from raw text.
* **`evidence-research/`**: Instructions for the agent on how to search and synthesize facts.
* **`indonesian-news-writing/` & `draft-revision/`**: Personas and stylistic rules for the AI journalist.
* **`editorial-review/`**: The strict guidelines the reflection agent uses to critique drafts.

---

## 🤖 Agentic Patterns Implemented

The service is built around a robust **LangGraph** state machine (defined in `app/workflows/editorial.py`), which orchestrates several advanced agentic patterns to guarantee factual accuracy and high-quality writing.

### 1. Plan-and-Execute
Before writing an article, the agent does not immediately start drafting or calling tools randomly.
1. The agent first reads the user's request.
2. It generates an `ExecutionPlan` detailing exactly what knowledge it needs to retrieve.
3. It then executes the plan by transitioning to the tool-calling phase.

### 2. ReAct (Reasoning and Acting)
During the research phase, the agent employs the **ReAct** pattern:
* **Reasoning**: It evaluates its current knowledge against the `ExecutionPlan`.
* **Acting**: It generates a `ToolAction` (like `search_knowledge`) to query the vector database.
* **Observation**: The system executes the tool and appends the result to the agent's state.
The agent loops through this process until it determines it has sufficient evidence to draft the article.

### 3. Reflection Agent (Actor-Critic)
To prevent hallucinations and enforce strict journalistic standards, the system employs a **Reflection** pattern (often called Actor-Critic).
1. **Actor (Drafting)**: The agent writes a `NewsArticle` based strictly on retrieved facts.
2. **Critic (Reviewing)**: A separate node in the graph assumes the `editorial-review` persona and evaluates the draft. It generates a `Reflection` containing a quality score and specific critiques (e.g., "Paragraph 2 contains an unverified date").
3. **Revision**: If the draft fails the review, the graph loops back to the Actor, providing it with the Critic's feedback so it can rewrite and improve the article.
This loop is bounded by a `revision_budget` to prevent infinite loops.

### 4. Human-in-the-Loop (Interrupts)
For potentially dangerous or unverified actions (like searching the live web), the LangGraph workflow uses `interrupt()`. The agent pauses its execution, saves its state to SQLite, and waits for the Laravel frontend to submit an explicit user approval before resuming the graph.
