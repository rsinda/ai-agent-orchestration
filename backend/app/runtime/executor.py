from datetime import timezone
import re
from typing import Any

from sqlalchemy.orm import Session

from backend.app.core.llm import LLMClient
from backend.app.db.models import Agent, Message, Run, RunEvent, Workflow, utc_now
from backend.app.memory.base import MemoryRecordInput
from backend.app.memory.pgvector import PgVectorMemoryStore
from backend.app.runtime.event_bus import event_bus
from backend.app.runtime.graph_builder import GraphBuilder, RuntimeState
from backend.app.tools.registry import ToolRegistry, default_tool_registry


class RuntimeExecutor:
    def __init__(self, db: Session, tool_registry: ToolRegistry | None = None) -> None:
        self.db = db
        self.llm = LLMClient()
        self.graph_builder = GraphBuilder()
        self.memory = PgVectorMemoryStore(db)
        self.tools = tool_registry or default_tool_registry

    def create_run(
        self, workflow_id: str, input_text: str = "", user_id: str | None = None
    ) -> Run:
        workflow = self.db.get(Workflow, workflow_id)
        if workflow is None:
            raise ValueError("Workflow not found.")
        run = Run(
            workflow_id=workflow_id,
            status="pending",
            input=input_text,
            state={"user_id": user_id} if user_id else {},
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    async def execute_run(self, run_id: str) -> Run:
        run = self.db.get(Run, run_id)
        if run is None:
            raise ValueError("Run not found.")
        workflow = self.db.get(Workflow, run.workflow_id)
        if workflow is None:
            raise ValueError("Workflow not found.")

        run.status = "running"
        run.started_at = utc_now()
        self.db.commit()
        await self._record_event(run.id, "run_started", None, {"input": run.input})

        try:
            graph = self.graph_builder.compile(workflow.definition, self._execute_node)
            initial_state: RuntimeState = {
                "run_id": run.id,
                "workflow_id": workflow.id,
                "input": run.input,
                "user_id": (run.state or {}).get("user_id"),
                "messages": (
                    [{"sender_id": "human", "content": run.input}] if run.input else []
                ),
                "tool_results": [],
                "variables": {},
                "iteration": 0,
            }
            final_state = await graph.ainvoke(initial_state)
            final_messages = final_state.get("messages", [])
            run.output = final_messages[-1]["content"] if final_messages else ""
            run.state = dict(final_state)
            run.status = "succeeded"
            run.finished_at = utc_now()
            self.db.commit()
            await self._record_event(
                run.id, "run_succeeded", None, {"output": run.output}
            )
        except Exception as exc:
            run.status = "failed"
            run.finished_at = utc_now()
            run.state = {**(run.state or {}), "error": str(exc)}
            self.db.commit()
            await self._record_event(run.id, "run_failed", None, {"error": str(exc)})
            raise

        self.db.refresh(run)
        return run

    async def _execute_node(
        self, node: dict[str, Any], state: RuntimeState
    ) -> RuntimeState:
        node_type = node.get("type", "agent")
        if node_type == "condition":
            return state
        if node_type == "tool":
            return await self._execute_tool_node(node, state)
        if node_type != "agent":
            await self._record_event(
                state["run_id"], "node_skipped", node["id"], {"type": node_type}
            )
            return state

        agent_id = node.get("agent_id")
        agent = self.db.get(Agent, agent_id)
        if agent is None:
            raise ValueError(f"Agent '{agent_id}' not found for node '{node['id']}'.")

        await self._record_event(
            state["run_id"], "node_started", node["id"], {"agent_id": agent.id}
        )
        context = state.get("messages", [])[-8:]
        user_prompt = self._agent_prompt(agent, state, context)
        tool_context = await self._agent_tool_context(agent, node, state, context)
        memories = self.memory.recall(
            user_prompt or agent.role,
            filters={
                "agent_id": agent.id,
                "workflow_id": state["workflow_id"],
                "user_id": state.get("user_id"),
            },
            limit=3,
        )
        memory_context = "\n".join(f"- {hit.content}" for hit in memories)
        prompt = (
            user_prompt
            if not memory_context
            else f"{user_prompt}\n\nRelevant memory:\n{memory_context}"
        )
        if tool_context:
            prompt = f"{prompt}\n\nTool results:\n{tool_context}"

        await self._record_event(
            state["run_id"],
            "model_call_started",
            node["id"],
            {"model": agent.model or self.llm.settings.default_model},
        )
        result = await self.llm.complete(
            model=agent.model,
            system_prompt=agent.system_prompt,
            user_prompt=prompt,
            context=context,
        )

        variables = dict(state.get("variables", {}))
        if "critic" in agent.role.lower() or "critic" in agent.name.lower():
            variables["needs_revision"] = "REVISION_REQUIRED" in result.content.upper()
            state["iteration"] = int(state.get("iteration", 0)) + 1

        message = Message(
            run_id=state["run_id"],
            workflow_id=state["workflow_id"],
            sender_id=agent.id,
            recipient_id=node.get("recipient_id", "workflow"),
            channel="internal",
            content=result.content,
            meta={"node_id": node["id"], "agent_name": agent.name},
        )
        self.db.add(message)
        run = self.db.get(Run, state["run_id"])
        if run is not None:
            usage = dict(run.token_usage or {})
            usage["prompt_tokens"] = (
                usage.get("prompt_tokens", 0) + result.prompt_tokens
            )
            usage["completion_tokens"] = (
                usage.get("completion_tokens", 0) + result.completion_tokens
            )
            run.token_usage = usage
            run.cost_usd = (run.cost_usd or 0.0) + result.cost_usd
        self.db.commit()
        self.db.refresh(message)

        self.memory.remember(
            MemoryRecordInput(
                agent_id=agent.id,
                workflow_id=state["workflow_id"],
                run_id=state["run_id"],
                user_id=state.get("user_id"),
                content=result.content,
                source_message_id=message.id,
            )
        )

        next_messages = [
            *state.get("messages", []),
            {"sender_id": agent.id, "content": result.content},
        ]
        new_state: RuntimeState = {
            **state,
            "messages": next_messages,
            "variables": variables,
        }
        await self._record_event(
            state["run_id"],
            "node_finished",
            node["id"],
            {
                "message_id": message.id,
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "cost_usd": result.cost_usd,
            },
        )
        return new_state

    async def _execute_tool_node(
        self, node: dict[str, Any], state: RuntimeState
    ) -> RuntimeState:
        tool_name = node.get("tool_name") or node.get("name")
        if not tool_name:
            raise ValueError(f"Tool node '{node['id']}' is missing tool_name.")

        arguments = self._resolve_tool_arguments(
            node.get("input") or node.get("arguments") or {}, state
        )
        await self._record_event(
            state["run_id"],
            "tool_call_started",
            node["id"],
            {"tool_name": tool_name, "arguments": arguments},
        )
        try:
            result = await self.tools.execute(tool_name, arguments)
            event_type = "tool_call_finished"
            payload = {"tool_name": tool_name, "result": result.data}
            content = result.content
        except Exception as exc:
            event_type = "tool_call_failed"
            payload = {"tool_name": tool_name, "error": str(exc)}
            content = f"Tool {tool_name} failed: {exc}"

        message = Message(
            run_id=state["run_id"],
            workflow_id=state["workflow_id"],
            sender_id=f"tool:{tool_name}",
            recipient_id=node.get("recipient_id", "workflow"),
            channel="tool",
            content=content,
            meta={"node_id": node["id"], "tool_name": tool_name},
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)

        tool_result = {
            "tool_name": tool_name,
            "content": content,
            "message_id": message.id,
            "node_id": node["id"],
        }
        new_state: RuntimeState = {
            **state,
            "messages": [
                *state.get("messages", []),
                {"sender_id": f"tool:{tool_name}", "content": content},
            ],
            "tool_results": [*state.get("tool_results", []), tool_result],
        }
        await self._record_event(
            state["run_id"],
            event_type,
            node["id"],
            {**payload, "message_id": message.id},
        )
        return new_state

    async def _agent_tool_context(
        self,
        agent: Agent,
        node: dict[str, Any],
        state: RuntimeState,
        context: list[dict[str, Any]],
    ) -> str:
        enabled_tools = set(agent.tools or [])
        enabled_tools.update(node.get("tools") or [])
        enabled_tools.discard("memory")
        if not enabled_tools:
            return ""

        prompt_text = state.get("input", "")
        context_lines: list[str] = []
        for tool_name in sorted(enabled_tools):
            arguments = self._default_tool_arguments(tool_name, state, context)
            if arguments is None:
                continue
            await self._record_event(
                state["run_id"],
                "agent_tool_call_started",
                node["id"],
                {"agent_id": agent.id, "tool_name": tool_name, "arguments": arguments},
            )
            try:
                result = await self.tools.execute(tool_name, arguments)
                context_lines.append(f"{tool_name}: {result.content}")
                await self._record_event(
                    state["run_id"],
                    "agent_tool_call_finished",
                    node["id"],
                    {
                        "agent_id": agent.id,
                        "tool_name": tool_name,
                        "result": result.data,
                    },
                )
            except Exception as exc:
                context_lines.append(f"{tool_name}: failed with {exc}")
                await self._record_event(
                    state["run_id"],
                    "agent_tool_call_failed",
                    node["id"],
                    {
                        "agent_id": agent.id,
                        "tool_name": tool_name,
                        "error": str(exc),
                        "prompt": prompt_text[:300],
                    },
                )
        return "\n".join(context_lines)

    def _agent_prompt(
        self, agent: Agent, state: RuntimeState, context: list[dict[str, Any]]
    ) -> str:
        transcript = "\n".join(
            f"{item.get('sender_id', 'unknown')}: {item.get('content', '')}"
            for item in context
        )
        return (
            f"Original user request:\n{state.get('input', '')}\n\n"
            f"Conversation so far:\n{transcript}\n\n"
            f"Your role is {agent.role}. Produce the next useful message for this workflow."
        )

    def _resolve_tool_arguments(self, value: Any, state: RuntimeState) -> Any:
        if isinstance(value, dict):
            return {
                key: self._resolve_tool_arguments(item, state)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [self._resolve_tool_arguments(item, state) for item in value]
        if not isinstance(value, str):
            return value

        replacements = {
            "{{input}}": state.get("input", ""),
            "{{user_id}}": state.get("user_id") or "",
            "{{last_message}}": (state.get("messages") or [{"content": ""}])[-1].get(
                "content", ""
            ),
        }
        resolved = value
        for token, replacement in replacements.items():
            resolved = resolved.replace(token, str(replacement))
        for match in re.findall(r"{{variables\.([a-zA-Z0-9_]+)}}", resolved):
            resolved = resolved.replace(
                f"{{{{variables.{match}}}}}",
                str((state.get("variables") or {}).get(match, "")),
            )
        return resolved

    def _default_tool_arguments(
        self,
        tool_name: str,
        state: RuntimeState,
        context: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        input_text = state.get("input", "")
        lowered = input_text.lower()
        last_message = (context[-1]["content"] if context else input_text) or input_text
        if tool_name == "web_search":
            if any(
                term in lowered
                for term in [
                    "search",
                    "latest",
                    "current",
                    "news",
                    "web",
                    "look up",
                    "find online",
                ]
            ):
                return {"query": input_text, "max_results": 5}
            return None
        if tool_name == "calculator":
            expression = self._extract_expression(input_text)
            return {"expression": expression} if expression else None
        if tool_name == "current_time":
            if any(
                term in lowered for term in ["time", "date", "today", "now", "current"]
            ):
                return {"timezone": "UTC"}
            return None
        if tool_name == "text_stats":
            if any(
                term in lowered
                for term in [
                    "word count",
                    "text stats",
                    "character count",
                    "how many words",
                ]
            ):
                return {"text": last_message}
            return None
        return None

    def _extract_expression(self, text: str) -> str | None:
        if not re.search(r"\d", text):
            return None
        candidates = re.findall(r"[-+*/().%\d\s]+", text)
        candidates = [
            candidate.strip()
            for candidate in candidates
            if re.search(r"\d\s*[-+*/%]\s*\d", candidate)
        ]
        if not candidates:
            return None
        return max(candidates, key=len)

    async def _record_event(
        self,
        run_id: str,
        event_type: str,
        node_id: str | None,
        payload: dict[str, Any],
    ) -> RunEvent:
        event = RunEvent(
            run_id=run_id, event_type=event_type, node_id=node_id, payload=payload
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        envelope = {
            "id": event.id,
            "run_id": event.run_id,
            "event_type": event.event_type,
            "node_id": event.node_id,
            "payload": event.payload,
            "created_at": event.created_at.astimezone(timezone.utc).isoformat(),
        }
        await event_bus.publish(run_id, envelope)
        return event
