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
                if condition == "else":
                    fallback = edge
                    continue
                if self._condition_matches(condition, state):
                    return self._route_key(edge)
            return self._route_key(fallback)

        return route

    def _condition_matches(self, condition: str, state: RuntimeState) -> bool:
        variables = state.get("variables", {})
        if condition in ("always", "", None):
            return True
        if condition == "critic_needs_revision":
            return (
                bool(variables.get("needs_revision"))
                and int(state.get("iteration", 0)) < 2
            )
        if condition == "critic_approved":
            return not bool(variables.get("needs_revision"))
        return bool(variables.get(condition))

    def _is_unconditional(self, edge: dict[str, Any]) -> bool:
        return edge.get("condition") in (None, "", "always")

    def _route_key(self, edge: dict[str, Any]) -> str:
        return f"{edge['source']}->{edge.get('target', 'END')}:{edge.get('condition', 'always')}"

    def _target(self, edge: dict[str, Any]):
        return END if edge.get("target") == "END" else edge["target"]
