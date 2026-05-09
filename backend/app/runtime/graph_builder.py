from collections.abc import Awaitable, Callable
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph


class RuntimeState(TypedDict, total=False):
    run_id: str
    workflow_id: str
    input: str
    user_id: str | None
    messages: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    variables: dict[str, Any]
    iteration: int


NodeHandler = Callable[[dict[str, Any], RuntimeState], Awaitable[RuntimeState]]


class GraphBuilder:
    def compile(self, definition: dict[str, Any], node_handler: NodeHandler):
        nodes = definition.get("nodes", [])
        edges = definition.get("edges", [])
        if not nodes:
            raise ValueError("Workflow definition must include at least one node.")

        graph = StateGraph(RuntimeState)
        node_ids = {node["id"] for node in nodes}

        for node in nodes:
            node_id = node["id"]

            async def run_node(
                state: RuntimeState, current_node: dict[str, Any] = node
            ) -> RuntimeState:
                return await node_handler(current_node, state)

            graph.add_node(node_id, run_node)

        entrypoint = definition.get("start_node") or nodes[0]["id"]
        if entrypoint not in node_ids:
            raise ValueError(
                f"Workflow start_node '{entrypoint}' does not match any node."
            )
        graph.set_entry_point(entrypoint)

        outgoing_by_source: dict[str, list[dict[str, Any]]] = {
            node_id: [] for node_id in node_ids
        }
        for edge in edges:
            source = edge["source"]
            if source not in outgoing_by_source:
                raise ValueError(
                    f"Workflow edge source '{source}' does not match any node."
                )
            target = edge.get("target")
            if target not in node_ids and target != "END":
                raise ValueError(
                    f"Workflow edge target '{target}' does not match any node."
                )
            outgoing_by_source[source].append(edge)

        for node_id in node_ids:
            outgoing = outgoing_by_source[node_id]
            if not outgoing:
                graph.add_edge(node_id, END)
            elif len(outgoing) == 1 and self._is_unconditional(outgoing[0]):
                graph.add_edge(node_id, self._target(outgoing[0]))
            else:
                graph.add_conditional_edges(
                    node_id,
                    self._router(outgoing),
                    {self._route_key(edge): self._target(edge) for edge in outgoing},
                )

        return graph.compile()

    def _router(self, outgoing: list[dict[str, Any]]):
        def route(state: RuntimeState) -> str:
            fallback = outgoing[-1]
            for edge in outgoing:
                condition = edge.get("condition", "always")
                if str(condition).lower() == "else":
                    fallback = edge
                    continue
                if self._condition_matches(condition, state):
                    return self._route_key(edge)
            return self._route_key(fallback)

        return route

    def _condition_matches(self, condition: str | None, state: RuntimeState) -> bool:
        variables = state.get("variables", {})
        raw_condition = "" if condition is None else str(condition).strip()
        normalized_condition = raw_condition.lower()
        if normalized_condition in ("always", ""):
            return True
        if normalized_condition == "critic_needs_revision":
            return (
                bool(variables.get("needs_revision"))
                and int(state.get("iteration", 0)) < 2
            )
        if normalized_condition == "critic_approved":
            return not bool(variables.get("needs_revision"))

        last_output = self._last_message_content(state)
        comparable_output = self._comparable_text(last_output)
        if normalized_condition.startswith("output_equals:"):
            expected = raw_condition.split(":", 1)[1]
            return comparable_output == self._comparable_text(expected)
        if normalized_condition.startswith("output_contains:"):
            expected = raw_condition.split(":", 1)[1]
            return self._comparable_text(expected) in comparable_output
        if raw_condition and comparable_output == self._comparable_text(raw_condition):
            return True

        return bool(variables.get(raw_condition)) or bool(
            variables.get(normalized_condition)
        )

    def _is_unconditional(self, edge: dict[str, Any]) -> bool:
        return str(edge.get("condition") or "").lower() in ("", "always")

    def _route_key(self, edge: dict[str, Any]) -> str:
        return f"{edge['source']}->{edge.get('target', 'END')}:{edge.get('condition', 'always')}"

    def _target(self, edge: dict[str, Any]):
        return END if edge.get("target") == "END" else edge["target"]

    def _last_message_content(self, state: RuntimeState) -> str:
        messages = state.get("messages", [])
        if not messages:
            return ""
        return str(messages[-1].get("content") or "")

    def _comparable_text(self, value: str) -> str:
        return value.strip().strip("\"'`.,:;").lower()
