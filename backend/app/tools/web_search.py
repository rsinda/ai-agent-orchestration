from typing import Any

import httpx

from backend.app.tools.base import RuntimeTool, ToolResult, ToolSpec


class WebSearchTool(RuntimeTool):
    spec = ToolSpec(
        name="web_search",
        description="Free web search using DuckDuckGo Instant Answer results.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 8},
            },
            "required": ["query"],
        },
    )

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        query = str(arguments.get("query", "")).strip()
        if not query:
            raise ValueError("web_search requires a query.")
        max_results = max(1, min(int(arguments.get("max_results", 5)), 8))

        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            response = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            )
            response.raise_for_status()
        data = response.json()
        results = self._extract_results(data, max_results)
        if not results and data.get("AbstractText"):
            results.append(
                {
                    "title": data.get("Heading") or query,
                    "url": data.get("AbstractURL") or "",
                    "snippet": data.get("AbstractText"),
                }
            )

        if not results:
            return ToolResult(content=f"No instant web results found for: {query}", data={"query": query, "results": []})

        lines = [f"{idx}. {item['title']} - {item['snippet']} ({item['url']})" for idx, item in enumerate(results, start=1)]
        return ToolResult(content="\n".join(lines), data={"query": query, "results": results})

    def _extract_results(self, data: dict[str, Any], max_results: int) -> list[dict[str, str]]:
        results: list[dict[str, str]] = []

        def visit(items: list[dict[str, Any]]) -> None:
            for item in items:
                if len(results) >= max_results:
                    return
                if "Topics" in item:
                    visit(item.get("Topics") or [])
                    continue
                text = item.get("Text")
                url = item.get("FirstURL")
                if text and url:
                    title = text.split(" - ", 1)[0][:120]
                    results.append({"title": title, "url": url, "snippet": text})

        visit(data.get("RelatedTopics") or [])
        return results

