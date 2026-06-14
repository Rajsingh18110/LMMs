import time
import httpx
from .base import ToolDefinition, ToolResult
from .registry import ToolRegistry
from .key_manager import KeyManager

from .categories.finance import execute_gold_price
from .categories.search import execute_web_search
from .categories.social import execute_wikipedia
from .categories.science import execute_nasa_apod
from .categories.weather import execute_weather
from .categories.anime import execute_anime_search, execute_anime_news, execute_anime_schedule
from .categories.crypto import execute_crypto_price, execute_crypto_market_data, execute_crypto_trending
from .categories.cyber import execute_cve_lookup, execute_security_news
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from lmms.backend.tools.kali_knowledge import list_kali_tools, tool_manual, kali_doc_search
from lmms.backend.connectors.telegram import execute_telegram_search_channels, execute_telegram_read_channel, execute_telegram_search_messages
from .categories.github import execute_github_search_repos, execute_github_repo_info, execute_github_clone_repo
from .categories.system_apps import execute_apt_search, execute_apt_install, execute_launch_app
from .categories.dom_control import execute_take_screenshot, execute_click_at, execute_type_text

EXECUTORS = {
    "get_gold_price":   execute_gold_price,
    "web_search":       execute_web_search,
    "search_news":      execute_web_search,
    "search_images":    execute_web_search,
    "search_videos":    execute_web_search,
    "search_youtube":   execute_web_search,
    "search_social":    execute_web_search,
    "search_wikipedia": execute_wikipedia,
    "nasa_apod":        execute_nasa_apod,
    "weather":          execute_weather,
    "anime_search":     execute_anime_search,
    "anime_news":       execute_anime_news,
    "anime_schedule":   execute_anime_schedule,
    "crypto_price":     execute_crypto_price,
    "crypto_market_data": execute_crypto_market_data,
    "crypto_trending":  execute_crypto_trending,
    "cve_lookup":       execute_cve_lookup,
    "security_news":    execute_security_news,
    "kali_list_tools":  list_kali_tools,
    "kali_tool_help":   tool_manual,
    "kali_doc_search":  kali_doc_search,
    "telegram_search_channels": execute_telegram_search_channels,
    "telegram_read_channel": execute_telegram_read_channel,
    "telegram_search_messages": execute_telegram_search_messages,
    # Github
    "github_search_repos":   execute_github_search_repos,
    "github_repo_info":      execute_github_repo_info,
    "github_clone_repo":     execute_github_clone_repo,
    # System Apps
    "apt_search":            execute_apt_search,
    "apt_install":           execute_apt_install,
    "launch_app":            execute_launch_app,
    # DOM Control
    "take_screenshot":       execute_take_screenshot,
    "click_at":              execute_click_at,
    "type_text":             execute_type_text,
}

CACHE_TTL = {
    "web_search":     300,   # 5 min
    "search_news":    60,    # 1 min
    "search_images":  1800,  # 30 min
    "search_videos":  1800,  # 30 min
    "search_youtube": 900,   # 15 min
    "search_social":  300,   # 5 min
    "get_gold_price": 300,   # 5 min
}

class ToolExecutor:
    """
    Model calls a tool → Executor runs it →
    Returns data back to model.
    Model NEVER directly calls APIs.
    LMMs always in the middle.
    """

    def __init__(self, registry: ToolRegistry,
                       keys:     KeyManager):
        self._registry = registry
        self._keys     = keys
        self._cache    = {}  # simple TTL cache

    async def execute(self, 
                      tool_name: str,
                      params:    dict) -> ToolResult:
        # 1. Validate tool exists
        tool = self._registry.get(tool_name)
        if not tool:
            return ToolResult(
                tool_name = tool_name,
                success   = False,
                data      = None,
                error     = f"Unknown tool: {tool_name}"
            )

        # 2. Check key if required
        if tool.requires_key:
            key = self._keys.get(tool_name)
            if not key:
                return ToolResult(
                    tool_name = tool_name,
                    success   = False,
                    data      = None,
                    error     = f"API key missing for "
                                f"{tool_name}. Add via: "
                                f"lmms keys set "
                                f"{tool_name} YOUR_KEY"
                )
            params["_api_key"] = key

        # 3. Check cache
        cache_key = f"{tool_name}:{hash(str(params))}"
        ttl = CACHE_TTL.get(tool_name, 300)  # Default 5 min
        
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() - cached["ts"] < ttl:
                result = cached["result"]
                result.cached = True
                return result

        # 4. Execute
        executor_fn = EXECUTORS.get(tool_name)
        if executor_fn:
            result = await executor_fn(params)
        else:
            # Auto-execute catalog tools (simple GET)
            result = await self._auto_execute(
                tool, params)

        # 5. Cache result
        if result.success:
            self._cache[cache_key] = {
                "ts":     time.time(),
                "result": result
            }

        return result

    async def _auto_execute(self, 
                             tool:   ToolDefinition,
                             params: dict) -> ToolResult:
        """For catalog tools without custom executor."""
        async with httpx.AsyncClient(timeout=10) as c:
            try:
                headers = {}
                if "_api_key" in params:
                    headers["X-API-Key"] = \
                        params.pop("_api_key")
                r = await c.get(tool.base_url,
                                params=params,
                                headers=headers)
                return ToolResult(
                    tool_name = tool.name,
                    success   = r.status_code == 200,
                    data      = r.json()
                )
            except Exception as e:
                return ToolResult(
                    tool_name = tool.name,
                    success   = False,
                    data      = None,
                    error     = str(e)
                )

if __name__ == "__main__":
    import asyncio
    import sys
    
    async def test():
        km = KeyManager()
        reg = ToolRegistry(km)
        exe = ToolExecutor(reg, km)
        
        args = sys.argv[1:]
        if len(args) < 2:
            print("Usage: python -m lmms.core.tools.executor <tool_name> '<json_params>'")
            return
            
        tool_name = args[0]
        import json
        params = json.loads(args[1])
        
        print(f"Executing: {tool_name}")
        t0 = time.time()
        res = await exe.execute(tool_name, params)
        t1 = time.time()
        print(f"Result: {res.data}")
        if res.error:
            print(f"Error: {res.error}")
        print(f"Time: {t1-t0:.2f}s")
        
    asyncio.run(test())
