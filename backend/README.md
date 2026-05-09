# Backend

FastAPI backend for the AI Agent Orchestration Platform. It owns persistence, agent/workflow APIs, LangGraph execution, tools, memory, monitoring events, and Telegram integration.

## Responsibilities

- Agent CRUD and configuration: model, tools, channels, memory, time limits.
- Workflow CRUD and execution through LangGraph.
- Persisted runs, messages, run events, token usage, and cost fields.
- Tool registry and execution for `calculator`, `web_search`, `current_time`, and `text_stats`.
- Vector memory through `VectorMemoryStore`, with pgvector storage.
- Telegram connector with inbound endpoint and polling support.

## Local Backend Only

From the repo root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn backend.app.main:app --reload
```

Backend URLs:

```text
http://localhost:8000
http://localhost:8000/docs
```

## Environment

Use `.env` at the repo root.

```text
DATABASE_URL=sqlite:///./agent_orchestrator.db
LLM_PROVIDER=gemini
DEFAULT_MODEL=gemini-2.5-flash
GOOGLE_API_KEY=
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
TELEGRAM_BOT_TOKEN=
EMBEDDING_MODEL_NAME=BAAI/bge-small-en-v1.5
```

If no LLM key is configured, the runtime falls back to deterministic mock responses so tests and demos can still run.

## Main APIs

- `POST /agents`, `GET /agents`, `PATCH /agents/{id}`, `DELETE /agents/{id}`
- `POST /workflows`, `GET /workflows`, `PATCH /workflows/{id}`, `DELETE /workflows/{id}`
- `POST /workflows/{id}/runs`
- `GET /runs`, `GET /runs/{id}`, `GET /runs/{id}/messages`, `GET /runs/{id}/events`, `GET /runs/{id}/stream`
- `GET /templates`, `POST /templates/{id}/instantiate`
- `GET /tools`, `POST /tools/{name}/execute`
- `POST /memory/remember`, `POST /memory/recall`
- `GET /channels/telegram/status`, `POST /channels/telegram/connect`, `POST /channels/telegram/inbound`

## Memory Embeddings

The default memory store uses `LocalEmbeddingService`, backed by Fastembed library.

## Runtime

Workflows are JSON graph definitions that can be compiled into LangGraph. Supported node types:

- `agent`: loads an agent, recalls memory, optionally gathers tool context, calls the configured LLM, and persists a message.
- `tool`: executes a registered backend tool and persists a tool message.
- `condition`: no-op node used for graph routing when needed.

Supported built-in edge conditions:

- `always`
- `else`
- `critic_needs_revision`
- `critic_approved`
- any variable name stored in runtime state

## Adding Workflow Templates

Add a factory in `backend/app/templates/catalog.py`.

1. Add a `WorkflowTemplate` entry to `TEMPLATES`.
2. Create any default agents needed by the workflow.
3. Return a `Workflow` with `start_node`, `nodes`, and `edges`.
4. Use `type: "agent"` for agent nodes and `type: "tool"` for tool nodes.

Example tool node:

```json
{
  "id": "calculate",
  "type": "tool",
  "tool_name": "calculator",
  "input": {"expression": "(2 + 3) * 4"}
}
```

## Adding Messaging Channels

Add a channel adapter under `backend/app/channels/`.

1. Store channel config in `ChannelBinding`.
2. Convert inbound channel messages into `RuntimeExecutor.create_run(...)`.
3. Persist the human/channel message before executing the run.
4. Send the final run output back through the channel when credentials are configured.
5. Add API routes in `backend/app/api/channels.py`.

## Tests

```bash
pytest
```
