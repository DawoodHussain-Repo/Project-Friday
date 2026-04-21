import os

from langchain_core.tools import tool


@tool
def web_search(query: str) -> str:
    """Searches the web for real-time information and returns a short summary."""
    tavily_api_key = os.getenv("TAVILY_API_KEY", "")

    if tavily_api_key:
        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=tavily_api_key)
            results = client.search(query=query, max_results=3)
            chunks = [r.get("content", "") for r in results.get("results", [])]
            return "\n\n".join([c for c in chunks if c]) or "No web results found."
        except Exception as exc:
            return f"Web search failed: {exc}"

    try:
        from duckduckgo_search import DDGS

        rows = []
        with DDGS() as ddgs:
            for item in ddgs.text(query, max_results=3):
                title = item.get("title", "No title")
                body = item.get("body", "")
                href = item.get("href", "")
                rows.append(f"{title}\n{body}\n{href}")
        return "\n\n".join(rows) if rows else "No web results found."
    except Exception as exc:
        return f"No search provider available: {exc}"
