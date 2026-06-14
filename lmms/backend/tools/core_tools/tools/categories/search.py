import httpx
from ..base import ToolDefinition, ToolResult, \
                   AuthType, ToolCategory

WEB_SEARCH_TOOL = ToolDefinition(
    name        = "web_search",
    description = "Search the web for current information. "
                  "Uses DuckDuckGo as primary, SearXNG as "
                  "optional, and Brave Search as fallback.",
    category    = ToolCategory.SEARCH,
    auth_type   = AuthType.NONE,
    base_url    = "https://api.duckduckgo.com",
    parameters  = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            },
            "num_results": {
                "type": "integer",
                "default": 5,
                "description": "Number of results"
            }
        },
        "required": ["query"]
    },
    requires_key = False,
)

NEWS_SEARCH_TOOL = ToolDefinition(
    name        = "search_news",
    description = "Search for recent news articles.",
    category    = ToolCategory.NEWS,
    auth_type   = AuthType.NONE,
    base_url    = "https://api.duckduckgo.com",
    parameters  = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "num_results": {"type": "integer", "default": 5}
        },
        "required": ["query"]
    },
    requires_key = False,
)

IMAGE_SEARCH_TOOL = ToolDefinition(
    name        = "search_images",
    description = "Search for images.",
    category    = ToolCategory.SEARCH,
    auth_type   = AuthType.NONE,
    base_url    = "https://api.duckduckgo.com",
    parameters  = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "num_results": {"type": "integer", "default": 5}
        },
        "required": ["query"]
    },
    requires_key = False,
)

VIDEO_SEARCH_TOOL = ToolDefinition(
    name        = "search_videos",
    description = "Search for videos.",
    category    = ToolCategory.SEARCH,
    auth_type   = AuthType.NONE,
    base_url    = "https://api.duckduckgo.com",
    parameters  = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "num_results": {"type": "integer", "default": 5}
        },
        "required": ["query"]
    },
    requires_key = False,
)

YOUTUBE_SEARCH_TOOL = ToolDefinition(
    name        = "search_youtube",
    description = "Search for YouTube videos.",
    category    = ToolCategory.SEARCH,
    auth_type   = AuthType.API_KEY,
    base_url    = "https://www.googleapis.com/youtube/v3/search",
    parameters  = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "num_results": {"type": "integer", "default": 5}
        },
        "required": ["query"]
    },
    requires_key = True,
    key_env_name = "YOUTUBE_API_KEY",
)

SOCIAL_SEARCH_TOOL = ToolDefinition(
    name        = "search_social",
    description = "Search social media platforms (Reddit/Twitter).",
    category    = ToolCategory.SOCIAL,
    auth_type   = AuthType.NONE,
    base_url    = "https://api.duckduckgo.com",
    parameters  = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "platform": {"type": "string", "enum": ["reddit", "twitter"], "default": "reddit"},
            "num_results": {"type": "integer", "default": 5}
        },
        "required": ["query"]
    },
    requires_key = False,
)

async def execute_web_search(params: dict) -> ToolResult:
    # Uses duckduckgo-search package for primary
    query = params.get("query", "")
    num = params.get("num_results", 5)
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=num):
                results.append({
                    "title": r.get("title"),
                    "url": r.get("href"),
                    "content": r.get("body"),
                })
        return ToolResult(tool_name="web_search", success=True, data=results)
    except Exception as e:
        return ToolResult(tool_name="web_search", success=False, data=None, error=f"DDG Search failed: {e}")

BUILTIN_SEARCH_TOOLS = [
    WEB_SEARCH_TOOL,
    NEWS_SEARCH_TOOL,
    IMAGE_SEARCH_TOOL,
    VIDEO_SEARCH_TOOL,
    YOUTUBE_SEARCH_TOOL,
    SOCIAL_SEARCH_TOOL,
]
