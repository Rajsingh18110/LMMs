import httpx
from ..base import ToolDefinition, ToolResult, \
                   AuthType, ToolCategory

WIKIPEDIA_TOOL = ToolDefinition(
    name        = "search_wikipedia",
    description = "Search Wikipedia for any topic. "
                  "Returns summary + full article. "
                  "Best for factual, historical info.",
    category    = ToolCategory.SOCIAL,
    auth_type   = AuthType.NONE,
    base_url    = "https://en.wikipedia.org/api/rest_v1",
    parameters  = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Topic to search"
            },
            "language": {
                "type": "string",
                "default": "en",
                "description": "Language code "
                               "(en, hi, fr, etc)"
            }
        },
        "required": ["query"]
    },
    requires_key = False,
)

async def execute_wikipedia(params: dict) -> ToolResult:
    query = params.get("query", "")
    lang = params.get("language", "en")
    
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{query}"
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(url)
            data = r.json()
            return ToolResult(
                tool_name = "search_wikipedia",
                success   = r.status_code == 200,
                data      = data
            )
        except Exception as e:
            return ToolResult(
                tool_name = "search_wikipedia",
                success   = False,
                data      = None,
                error     = str(e)
            )
