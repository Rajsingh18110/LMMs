import httpx
from ..base import ToolResult

async def execute_anime_search(params: dict) -> ToolResult:
    query = params.get("query")
    if not query:
        return ToolResult(tool_name="anime_search", success=False, data=None, error="Missing query")
        
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(f"https://api.jikan.moe/v4/anime?q={query}&sfw=true&limit=3")
            if r.status_code == 200:
                data = r.json().get("data", [])
                results = []
                for item in data:
                    results.append({
                        "title": item.get("title"),
                        "score": item.get("score"),
                        "episodes": item.get("episodes"),
                        "status": item.get("status"),
                        "synopsis": item.get("synopsis", "")[:200] + "..."
                    })
                return ToolResult(tool_name="anime_search", success=True, data=results)
            return ToolResult(tool_name="anime_search", success=False, data=None, error=f"Status: {r.status_code}")
        except Exception as e:
            return ToolResult(tool_name="anime_search", success=False, data=None, error=str(e))

async def execute_anime_news(params: dict) -> ToolResult:
    anime_id = params.get("anime_id", "1") # default to Cowboy Bebop if none
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(f"https://api.jikan.moe/v4/anime/{anime_id}/news")
            if r.status_code == 200:
                return ToolResult(tool_name="anime_news", success=True, data=r.json().get("data", [])[:3])
            return ToolResult(tool_name="anime_news", success=False, data=None, error=f"Status: {r.status_code}")
        except Exception as e:
            return ToolResult(tool_name="anime_news", success=False, data=None, error=str(e))

async def execute_anime_schedule(params: dict) -> ToolResult:
    day = params.get("day", "monday")
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(f"https://api.jikan.moe/v4/schedules?filter={day}&limit=5")
            if r.status_code == 200:
                data = r.json().get("data", [])
                return ToolResult(tool_name="anime_schedule", success=True, data=[d.get("title") for d in data])
            return ToolResult(tool_name="anime_schedule", success=False, data=None, error=f"Status: {r.status_code}")
        except Exception as e:
            return ToolResult(tool_name="anime_schedule", success=False, data=None, error=str(e))
