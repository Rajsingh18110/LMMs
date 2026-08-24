from typing import List, Dict, Any
from lmms.backend.tools.core import default_registry, default_executor, ToolDefinition, Permission
from lmms.backend.tools.search_provider import DDGSSearchProvider

# Register the structured canonical tool
def canonical_search_callback(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    provider = DDGSSearchProvider()
    return provider.search(query, max_results=max_results)

default_registry.register(ToolDefinition(
    name="web.search",
    description="Search the web using a search provider.",
    category="web",
    parameters={"query": "str", "max_results": "int"},
    permissions=[Permission.NETWORK],
    risk_level="low",
    requires_network=True,
    callback=canonical_search_callback
))

# Legacy backward-compatibility adapter
def web_search(query: str, max_results: int = 5) -> str:
    """
    Legacy search interface that returns formatted strings.
    This delegates execution to the canonical ToolExecutor to enforce permissions and structure.
    """
    result = default_executor.execute("web.search", {"query": query, "max_results": max_results})
    
    if not result.success:
        # Replicate legacy exception string format
        return f"Search failed: {result.error}"
        
    data = result.data
    if not data:
        return "No results found."
        
    formatted = []
    for r in data:
        formatted.append(f"Title: {r.get('title', '')}\nURL: {r.get('url', '')}\nSummary: {r.get('snippet', '')}\n")
        
    return "\n---\n".join(formatted)
