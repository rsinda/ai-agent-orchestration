# Frontend

Streamlit frontend for managing agents, workflows, runs, tools, memory, and Telegram setup.

## Run Frontend Only

Start the backend first, then run:

```bash
BACKEND_URL=http://localhost:8000 streamlit run frontend/streamlit_app.py
```

Open:

```text
http://localhost:8501
```

## Pages

- Dashboard: backend health, totals, quick template creation, quick workflow run, recent runs.
- Agents: create, edit, and delete agents; configure model, tool registry choices, memory, limits, rules, skills, and guardrails.
- Workflows: instantiate templates, view graph, inspect nodes/edges, edit workflow JSON, and run workflows.
- Memory: add memory records and recall memory with filters.
- Runs: inspect status, output, messages, events, tokens, and cost.
- Telegram: connect a default workflow and see connector status.
- Tools: choose a tool from the backend registry, inspect schema, and execute it with JSON arguments.

## Backend Contract

The UI reads `BACKEND_URL`, defaulting to:

```text
http://localhost:8000
```

Docker Compose sets:

```text
BACKEND_URL=http://backend:8000
```

All frontend data flows through `frontend/ui/api_client.py`; no agent runtime logic lives in Streamlit.

## Tool Dropdown

The Agents page calls `GET /tools` and renders registered tools as a multiselect. The `memory` option is included as a built-in runtime capability alongside registry tools like `web_search`, `calculator`, `current_time`, and `text_stats`.

## Workflow Visualization

Workflow graphs are rendered with Streamlit Graphviz from each workflow definition. The visual builder is template-first for demo reliability, with an advanced JSON editor for custom nodes, edges, conditions, and tool nodes.

