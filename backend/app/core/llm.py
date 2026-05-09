from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from backend.app.core.config import get_settings


@dataclass
class LLMResult:
    content: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float = 0.0


class LLMClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def complete(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        context: list[dict[str, Any]] | None = None,
    ) -> LLMResult:
        selected_model = model or self.settings.default_model
        provider = self._provider_for_model(selected_model)
        if selected_model == "mock-agent" or not self._has_credentials(provider):
            return self._mock_completion(selected_model, system_prompt, user_prompt, context or [])

        chat_model = self._chat_model(provider, selected_model)
        response = await chat_model.ainvoke(self._messages(system_prompt, user_prompt, context or []))
        usage = self._usage(response)
        return LLMResult(
            content=str(response.content),
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            cost_usd=0.0,
        )

    def _provider_for_model(self, model: str) -> str:
        provider = self.settings.llm_provider.lower()
        if model.startswith("gpt-") or model.startswith("o"):
            return "openai"
        if model.startswith("gemini-"):
            return "gemini"
        return provider

    def _has_credentials(self, provider: str) -> bool:
        if provider == "gemini":
            return bool(self.settings.google_api_key)
        if provider == "openai":
            return bool(self.settings.openai_api_key)
        return False

    def _chat_model(self, provider: str, model: str):
        if provider == "openai":
            return ChatOpenAI(
                model=model,
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url,
                temperature=0.2,
            )
        if provider == "gemini":
            return ChatGoogleGenerativeAI(
                model=model,
                google_api_key=self.settings.google_api_key,
                temperature=0.2,
            )
        raise ValueError(f"Unsupported LLM provider '{provider}'.")

    def _messages(
        self,
        system_prompt: str,
        user_prompt: str,
        context: list[dict[str, Any]],
    ) -> list[BaseMessage]:
        messages: list[BaseMessage] = [SystemMessage(content=system_prompt)]
        for item in context[-8:]:
            content = item.get("content", "")
            if item.get("sender_id") == "human":
                messages.append(HumanMessage(content=content))
            else:
                messages.append(AIMessage(content=content))
        messages.append(HumanMessage(content=user_prompt))
        return messages

    def _usage(self, response: BaseMessage) -> dict[str, int]:
        usage = getattr(response, "usage_metadata", None) or {}
        return {
            "prompt_tokens": int(usage.get("input_tokens", usage.get("prompt_tokens", 0)) or 0),
            "completion_tokens": int(usage.get("output_tokens", usage.get("completion_tokens", 0)) or 0),
        }

    def _mock_completion(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        context: list[dict[str, Any]],
    ) -> LLMResult:
        role_line = system_prompt.strip().splitlines()[0][:120] if system_prompt else "Agent"
        context_hint = context[-1]["content"][:180] if context else user_prompt[:180]
        if "critic" in role_line.lower() or "quality" in system_prompt.lower():
            content = f"APPROVED: The draft is usable for the request. Key basis: {context_hint}"
        elif "writer" in role_line.lower():
            content = f"Final answer: {context_hint}"
        elif "triage" in role_line.lower():
            content = f"Classification: general_support. Summary: {user_prompt[:180]}"
        else:
            content = f"{role_line} response: {context_hint}"
        return LLMResult(
            content=content,
            prompt_tokens=max(1, len((system_prompt + user_prompt).split())),
            completion_tokens=max(1, len(content.split())),
            cost_usd=0.0,
        )
