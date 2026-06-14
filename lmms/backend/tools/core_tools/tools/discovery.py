import httpx
import json
import time
from pathlib import Path
from .registry import ToolRegistry

class APICatalogFetcher:
    SOURCES = [
        "https://api.publicapis.org/entries",
        "https://raw.githubusercontent.com/public-api-lists/public-api-lists/master/public-api-lists.json",
        "https://raw.githubusercontent.com/tools-collection/apis-collection/main/apis.json",
    ]

    async def fetch_and_merge(self) -> list:
        all_apis = []
        async with httpx.AsyncClient(timeout=30) as client:
            for url in self.SOURCES:
                try:
                    r = await client.get(url)
                    data = r.json()
                    # Normalize different formats
                    entries = self._normalize(data)
                    all_apis.extend(entries)
                except Exception as e:
                    print(f"Source failed: {url} — {e}")
        
        # Deduplicate by API URL
        seen = set()
        unique = []
        for api in all_apis:
            key = api.get("url", api.get("Link", ""))
            if key and key not in seen:
                seen.add(key)
                unique.append(api)
        
        return unique

    def _normalize(self, data) -> list:
        # Handle different JSON structures
        if isinstance(data, dict):
            return data.get("entries", 
                   data.get("apis", 
                   data.get("data", [])))
        if isinstance(data, list):
            return data
        return []

class ToolDiscovery:
    """
    On LMMs first launch:
    1. Fetch all 3 API repos
    2. Parse and normalize
    3. Save to ~/.lmms/tools/api_catalog.json
    4. Register all in ToolRegistry

    On subsequent launches:
    Load from cache, refresh in background.
    """

    CATALOG_PATH = Path.home() / ".lmms" / "tools" / "api_catalog.json"
    REFRESH_DAYS = 7  # Re-fetch every 7 days

    async def run(self, registry: ToolRegistry):
        if self._needs_refresh():
            print("Discovering APIs from public repos...")
            fetcher = APICatalogFetcher()
            apis    = await fetcher.fetch_and_merge()
            self._save(apis)
            print(f"Discovered {len(apis)} APIs")
        else:
            apis = self._load()
        
        # Register all in registry
        for entry in apis:
            tool = registry._entry_to_tool(entry)
            if tool:
                registry.register(tool)

    def _needs_refresh(self) -> bool:
        if not self.CATALOG_PATH.exists():
            return True
        mtime = self.CATALOG_PATH.stat().st_mtime
        age   = time.time() - mtime
        return age > (self.REFRESH_DAYS * 86400)

    def _save(self, apis: list):
        self.CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.CATALOG_PATH.write_text(json.dumps(apis, indent=2))
        
    def _load(self) -> list:
        if self.CATALOG_PATH.exists():
            return json.loads(self.CATALOG_PATH.read_text())
        return []

if __name__ == "__main__":
    import asyncio
    async def test():
        print("Fetching from 3 sources...")
        f = APICatalogFetcher()
        res = await f.fetch_and_merge()
        print(f"Discovered {len(res)} unique APIs")
        td = ToolDiscovery()
        td._save(res)
        print("Saved to ~/.lmms/tools/api_catalog.json")
    asyncio.run(test())
