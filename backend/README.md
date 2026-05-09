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
- `output_equals:<text>`
- `output_contains:<text>`
- exact previous-agent output, for example `MATH`
- any variable name stored in runtime state

## Workflow Edges And Routing

Each workflow edge describes where LangGraph should route after a node finishes.

```json
{
  "source": "1-triage-agent",
  "target": "2-math-agent",
  "condition": "output_equals:MATH",
  "label": "math"
}
```

Edge fields:

- `source`: node id that just finished.
- `target`: next node id, or `END` to finish the run.
- `condition`: routing rule evaluated against runtime state.
- `label`: optional display label for UI graph rendering.

Condition behavior:

- `always`: route unconditionally.
- `else`: fallback route when no earlier condition from the same source matched.
- `critic_needs_revision`: route when critic output marked `needs_revision` and retry limit has not been reached.
- `critic_approved`: route when critic output did not mark `needs_revision`.
- `output_equals:MATH`: route when the previous agent/tool output message equals `MATH`, case-insensitive.
- `output_contains:MATH`: route when the previous agent/tool output message contains `MATH`, case-insensitive.

When a node has multiple outgoing edges, order matters. The router evaluates non-`else` edges in the JSON order and picks the first match. Keep `else` as the fallback edge for that source node.

Example triage-to-math workflow:

```json
{
  "start_node": "1-triage-agent",
  "nodes": [
    {
      "id": "1-triage-agent",
      "type": "agent",
      "label": "Triage Agent",
      "agent_id": "triage-agent-id",
      "recipient_id": "workflow"
    },
    {
      "id": "2-math-agent",
      "type": "agent",
      "label": "Math Agent",
      "agent_id": "math-agent-id",
      "recipient_id": "workflow"
    }
  ],
  "edges": [
    {
      "source": "1-triage-agent",
      "target": "2-math-agent",
      "condition": "output_equals:MATH",
      "label": "math"
    },
    {
      "source": "1-triage-agent",
      "target": "END",
      "condition": "else",
      "label": "not math"
    },
    {
      "source": "2-math-agent",
      "target": "END",
      "condition": "always",
      "label": "finish"
    }
  ]
}
```

For this pattern, make the triage agent return exactly `MATH` for math requests. If the model may respond with a sentence like `This is a MATH request`, use `output_contains:MATH` instead.

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
