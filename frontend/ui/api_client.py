import os
from typing import Any

import requests


class ApiError(RuntimeError):
    pass


class ApiClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (
            base_url or os.getenv("BACKEND_URL") or "http://localhost:8000"
        ).rstrip("/")

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def list_agents(self) -> list[dict[str, Any]]:
        return self._request("GET", "/agents")

    def create_agent(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/agents", json=payload)

    def update_agent(self, agent_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("PATCH", f"/agents/{agent_id}", json=payload)

    def delete_agent(self, agent_id: str) -> None:
        self._request("DELETE", f"/agents/{agent_id}")

    def list_workflows(self) -> list[dict[str, Any]]:
        return self._request("GET", "/workflows")

    def create_workflow(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/workflows", json=payload)

    def update_workflow(
        self, workflow_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return self._request("PATCH", f"/workflows/{workflow_id}", json=payload)

    def list_templates(self) -> list[dict[str, Any]]:
        return self._request("GET", "/templates")

    def instantiate_template(
        self, template_id: str, name: str | None = None
    ) -> dict[str, Any]:
        return self._request(
            "POST", f"/templates/{template_id}/instantiate", json={"name": name or None}
        )

    def run_workflow(
        self,
        workflow_id: str,
        input_text: str,
        user_id: str | None = None,
        execute_async: bool = True,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/workflows/{workflow_id}/runs",
            json={
                "input": input_text,
                "user_id": user_id or None,
                "execute_async": execute_async,
            },
        )

    def list_runs(self, limit: int = 25) -> list[dict[str, Any]]:
        return self._request("GET", "/runs", params={"limit": limit})

    def get_run(self, run_id: str) -> dict[str, Any]:
        return self._request("GET", f"/runs/{run_id}")

    def get_run_messages(self, run_id: str) -> list[dict[str, Any]]:
        return self._request("GET", f"/runs/{run_id}/messages")

    def get_run_events(self, run_id: str) -> list[dict[str, Any]]:
        return self._request("GET", f"/runs/{run_id}/events")

    def list_tools(self) -> list[dict[str, Any]]:
        return self._request("GET", "/tools")

    def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self._request(
            "POST", f"/tools/{tool_name}/execute", json={"arguments": arguments}
        )

    def remember(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/memory/remember", json=payload)

    def recall_memory(
        self, query: str, filters: dict[str, Any], limit: int = 5
    ) -> list[dict[str, Any]]:
        return self._request(
            "POST",
            "/memory/recall",
            json={"query": query, "filters": filters, "limit": limit},
        )

    def telegram_status(self) -> dict[str, Any]:
        return self._request("GET", "/channels/telegram/status")

    def connect_telegram(
        self,
        default_workflow_id: str,
        name: str = "Telegram Bot",
        bot_token: str | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/channels/telegram/connect",
            json={
                "channel": "telegram",
                "name": name,
                "bot_token": bot_token or None,
                "default_workflow_id": default_workflow_id,
            },
        )

    def _request(self, method: str, path: str, **kwargs):
        try:
            response = requests.request(
                method, f"{self.base_url}{path}", timeout=90, **kwargs
            )
        except requests.RequestException as exc:
            raise ApiError(
                f"Could not reach backend at {self.base_url}: {exc}"
            ) from exc

        if response.status_code == 204:
            return None
        if response.status_code >= 400:
            detail = response.text
            try:
                detail = response.json().get("detail", detail)
            except ValueError:
                pass
            raise ApiError(
                f"{method} {path} failed with {response.status_code}: {detail}"
            )
        return response.json()
