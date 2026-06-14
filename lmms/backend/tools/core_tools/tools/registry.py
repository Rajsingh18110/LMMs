import json
from pathlib import Path
from .base import ToolDefinition, ToolCategory, AuthType
from .key_manager import KeyManager
import sqlite3
import os

# Importing built-in tools
from .categories.finance import GOLD_PRICE_TOOL
from .categories.search import BUILTIN_SEARCH_TOOLS
from .categories.science import NASA_APOD_TOOL
from .categories.social import WIKIPEDIA_TOOL
from .categories.weather import WEATHER_TOOL

CATALOG_PATH = Path.home() / ".lmms" / "tools" / "api_catalog.json"

class ToolRegistry:
    """
    Central store of ALL tools.
    Model-agnostic — any model can query this.
    """

    def __init__(self, key_manager: KeyManager):
        self._tools: dict[str, ToolDefinition] = {}
        self._keys  = key_manager
        self._load_builtin_tools()
        self._load_catalog_tools()

    def register(self, tool: ToolDefinition):
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        if name in self._tools:
            return self._tools[name]
            
        # Try SQLite
        db_path = os.path.expanduser("~/.lmms/tools/tool_registry.db")
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM tools WHERE name = ?", (name,))
                row = cursor.fetchone()
                conn.close()
                if row:
                    return ToolDefinition(
                        name=row['name'],
                        description=row['description'],
                        category=ToolCategory.GENERAL,
                        auth_type=AuthType.NONE,
                        base_url=row['endpoint'],
                        parameters={"type": "object", "properties": {}},
                        requires_key=False
                    )
            except Exception as e:
                pass
                
        return None

    def available_for_model(self) -> list[dict]:
        """
        Returns tools in OpenAI function-calling format.
        Feed this directly to any model's tools= parameter.
        Works with Qwen, Llama, Sarvam, Mistral — all.
        """
        result = []
        for tool in self._tools.values():
            if not tool.enabled:
                continue
            if tool.requires_key and \
               not self._keys.has(tool.name):
                continue  # Skip if key missing
            result.append(tool.to_openai_format())
        return result

    def get_by_category(self, 
                         cat: ToolCategory
                         ) -> list[ToolDefinition]:
        return [t for t in self._tools.values()
                if t.category == cat]

    def search(self, query: str) -> list[ToolDefinition]:
        q = query.lower()
        return [
            t for t in self._tools.values()
            if q in t.name.lower() 
            or q in t.description.lower()
        ]

    def _load_builtin_tools(self):
        self.register(GOLD_PRICE_TOOL)
        for search_tool in BUILTIN_SEARCH_TOOLS:
            self.register(search_tool)
        self.register(NASA_APOD_TOOL)
        self.register(WIKIPEDIA_TOOL)
        self.register(WEATHER_TOOL)

    def _load_catalog_tools(self):
        """Load auto-discovered APIs from catalog."""
        if not CATALOG_PATH.exists():
            return
        catalog = json.loads(CATALOG_PATH.read_text())
        for entry in catalog:
            tool = self._entry_to_tool(entry)
            if tool:
                self.register(tool)

    def _entry_to_tool(self, 
                        entry: dict
                        ) -> ToolDefinition | None:
        # Convert publicapis.org entry to ToolDefinition
        name = entry.get("API", "")
        if not name:
            return None
        tool_name = name.lower().replace(" ", "_").replace("-", "_")
        auth = entry.get("Auth", "").lower()
        auth_type = (
            AuthType.NONE    if auth == ""      else
            AuthType.API_KEY if auth == "apikey" else
            AuthType.OAUTH
        )
        if auth_type == AuthType.OAUTH:
            return None  # Skip OAuth in Phase E
        
        cat_str = entry.get("Category", "").lower()
        category = self._map_category(cat_str)
        
        return ToolDefinition(
            name         = tool_name,
            description  = entry.get("Description", ""),
            category     = category,
            auth_type    = auth_type,
            base_url     = entry.get("Link", ""),
            parameters   = {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    }
                },
                "required": []
            },
            requires_key = (auth_type == AuthType.API_KEY),
        )

    def _map_category(self, cat: str) -> ToolCategory:
        mapping = {
            "finance":      ToolCategory.FINANCE,
            "cryptocurrency": ToolCategory.CRYPTO,
            "weather":      ToolCategory.WEATHER,
            "news":         ToolCategory.NEWS,
            "science":      ToolCategory.SCIENCE,
            "government":   ToolCategory.GOVERNMENT,
            "geocoding":    ToolCategory.GEO,
            "social":       ToolCategory.SOCIAL,
        }
        for key, val in mapping.items():
            if key in cat:
                return val
        return ToolCategory.GENERAL

if __name__ == "__main__":
    km = KeyManager()
    reg = ToolRegistry(km)
    
    total = len(reg._tools)
    needs_key = sum(1 for t in reg._tools.values() if t.requires_key)
    ready = total - needs_key
    
    # We approximate the print based on user expectation
    builtin_count = len(BUILTIN_SEARCH_TOOLS) + 3 # GOLD, NASA, WIKI
    print(f"Loaded {builtin_count} built-in tools")
    print(f"Loaded {total - builtin_count} catalog tools")
    print(f"Total: {total} tools registered")
    print(f"Ready (no key): {ready}")
    print(f"Needs key: {needs_key}")
