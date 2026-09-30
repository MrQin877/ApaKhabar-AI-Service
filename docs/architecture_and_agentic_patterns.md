# Architecture and agentic patterns: code map

Reviewed against the implementation on 1 October 2026. See [operational architecture](agent-architecture.md), [judge setup](separate-judge.md), and the [editable draw.io diagram](architecture/apakhabar-current-ai.drawio).

## Roles and graph

The application implements four editorial roles within **one** `EditorialWorkflow`, not independent agent processes. There is no A2A protocol and no MCP server/client in this workflow.

| Role | Method in `app/workflows/editorial.py` | Model |
| --- | --- | --- |
| Planner | `plan()` | Generation |
| Researcher | `research()` | Generation |
| Writer | `write()` | Generation |
| Reviewer | `reflect()` | Judge when enabled; otherwise generation |

`build()` registers nine nodes: `plan`, `research`, `approval`, `check`, `clarify`, `write`, `reflect`, `revise`, `finish`.

### Plan and Execute

`plan()` identifies explicit user assertions and requested format. It requests at most three evidence-research tasks when eligible information is missing or configured web discovery is allowed. Fully supplied evidence can skip research. Writing and review are mandatory downstream stages, not tasks the planner may omit.

### ReAct-style research

`research()` requests a typed `ToolAction`, executes it, stores its result/error as an observation, and chooses another action or finishes. `app/tools/editorial.py` dispatches `search_information`, `inspect_source`, `read_skill`, and optional `web_search`; `finish` is handled by the workflow. These are direct Python tools, not MCP tools or native LangGraph ToolNode calls. Duplicate actions and total tool calls are bounded.

### Reflection and revision

`reflect()` supplies the draft, evidence, and completeness findings to the reviewer. Deterministic coverage and source checks supplement the model review. The code computes a weighted score from returned dimensions. `revise()` increments the revision counter and routes back to `write()` with review feedback. The loop stops at configured limits or when review no longer improves, retaining the best candidate. This reduces errors but does not guarantee factual accuracy.

### Human review

`approval()` interrupts for approval of discovered web snippets **after search**, before they become drafting evidence. `clarify()` interrupts for missing information, with at most one clarification round. Laravel owns source moderation, draft editing, category approval, and publishing confirmation. Completing the graph never publishes news.

## Model construction and routing

- `app/core/config.py`: provider, endpoint, alias, timeout, embedding, and evaluator settings, overridden by `.env`.
- `app/providers/models.py`: `GenerationModel.structured()` validates JSON with one repair attempt; `_chat()` calls llama.cpp or Ollama. `Embeddings` handles the separate retrieval model.
- `app/providers/evaluator.py`: `build_evaluator()` creates a model client using judge settings and rejects identical writer/judge names. Different aliases alone do not prove different weights.
- `app/services/agent_service.py`: initializes generation model, optional evaluator, skill registry, and tools; runs the graph with SQLite checkpoints and persisted events.
- `EditorialWorkflow.call()`: routes `Reflection` schemas to `self.evaluator`; all other graph schemas use `self.model`.

With the judge enabled, its failure preserves the draft with `evaluation_unavailable` and blocks publication rather than falling back to self-review. Defaults disable the judge; deployment configuration controls activation. DeepEval is a separate optional offline calibration runner, not part of each production request.

## Skill activation

`app/skills/registry.py` discovers `skills/*/SKILL.md`, validates metadata, and hashes contents. `activate(name)` loads instructions; `resource()` loads bounded Markdown references within that skill directory.

The application chooses skills explicitly:

| Stage | Skill | Trigger |
| --- | --- | --- |
| Extraction | `document-extraction` | `AIService` in `app/services/ai_service.py` activates it |
| Research | `evidence-research` | `plan()` / `research()` call `self.skill(...)` |
| New draft | `indonesian-news-writing` | `write()` when there is no current draft or revision |
| Revision | `draft-revision` | `write()` when current draft or revision count exists |
| Review | `editorial-review` | `reflect()` |

`EditorialWorkflow.skill()` calls `registry.activate()` and checks version consistency. The returned `active['instructions']` is included in the model prompt. The research model may request references through `read_skill`, restricted to active skills. Non-news formats load writing format references directly. Skills are maintained instructions, not independent models, executable programs, or uploaded source documents.

## Other application paths

- `app/api/assistant.py`: `/assistant/respond` classifies intent and answers questions from supplied information. An upload alone does not request a draft.
- `app/api/document.py`, `app/services/document_service.py`: upload normalization and file parsing, including spreadsheets and OCR-supported inputs.
- `app/services/extraction_service.py`, `app/services/ai_service.py`: chunked structured extraction; separate from the editorial graph.
- `app/services/knowledge_service.py`, `app/api/knowledge.py`: approved information indexing and owner/eligibility-filtered retrieval.
- `app/services/rag_service.py`: legacy raw-document retrieval, isolated from approved editorial research.
- `app/api/agent.py`: synchronous run/resume calls and persisted state inspection. Laravel queue workers provide asynchronous UI execution.

The Python article schema remains structured (`headline`, `lead`, `body`, etc.). Laravel maps it to unified draft `title`/`content`/`excerpt` fields. Extraction-quality badges in Laravel use evidence/completeness/confidence heuristics; the separate judge currently reviews drafts, not an independently evaluated extraction output.
