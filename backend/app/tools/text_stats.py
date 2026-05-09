from typing import Any

from backend.app.tools.base import RuntimeTool, ToolResult, ToolSpec


class TextStatsTool(RuntimeTool):
    spec = ToolSpec(
        name="text_stats",
        description="Count words, characters, and lines in text.",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    )

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        text = str(arguments.get("text", ""))
        words = len([word for word in text.split() if word])
        characters = len(text)
        lines = len(text.splitlines()) if text else 0
        content = f"Text stats: {words} words, {characters} characters, {lines} lines."
        return ToolResult(content=content, data={"words": words, "characters": characters, "lines": lines})

