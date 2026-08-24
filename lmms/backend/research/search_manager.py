import asyncio
import datetime
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
from urllib.parse import urlparse

from lmms.backend.research.events import (
    ResearchEvent, SearchStarted, SearchCompleted, SearchFailed, 
    DeduplicationStarted, DeduplicationCompleted, dispatch_event
)

class AsyncSearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        pass

class DDGSAsyncProvider(AsyncSearchProvider):
    def _sync_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        results = []
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                        "source": "ddgs",
                        "retrieved_at": datetime.datetime.now().isoformat()
                    })
        except Exception as e:
            raise Exception(f"DDGS Search Provider failed: {str(e)}")
        return results

    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        # Run the synchronous DDGS call in a separate thread
        return await asyncio.to_thread(self._sync_search, query, max_results)

class SearchManager:
    """Orchestrates parallel searches across providers or queries."""
    def __init__(self, providers: List[AsyncSearchProvider], concurrency_limit: int = 3):
        self.providers = providers
        self.semaphore = asyncio.Semaphore(concurrency_limit)
        
    def _normalize_url(self, url: str) -> str:
        """Removes trailing slashes, fragments, and basic tracking params."""
        parsed = urlparse(url)
        # Rebuild without fragment
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if normalized.endswith("/"):
            normalized = normalized[:-1]
        return normalized.lower()

    async def _search_with_provider(self, provider: AsyncSearchProvider, query: str, max_results: int, run_id: str, emit_cb: Optional[Callable[[ResearchEvent], Any]]) -> List[Dict[str, Any]]:
        async with self.semaphore:
            start_time = time.monotonic()
            try:
                res = await provider.search(query, max_results)
                duration = int((time.monotonic() - start_time) * 1000)
                await dispatch_event(emit_cb, SearchCompleted(run_id=run_id, query=query, result_count=len(res), duration_ms=duration))
                return res
            except Exception as e:
                duration = int((time.monotonic() - start_time) * 1000)
                await dispatch_event(emit_cb, SearchFailed(run_id=run_id, query=query, provider=type(provider).__name__, error=str(e), duration_ms=duration))
                print(f"[SearchManager] Provider {type(provider).__name__} failed: {e}")
                return []

    async def search_parallel(self, queries: List[str], max_results_per_query: int = 5, run_id: str = "test", emit_cb: Optional[Callable[[ResearchEvent], Any]] = None) -> List[Dict[str, Any]]:
        tasks = []
        for query in queries:
            await dispatch_event(emit_cb, SearchStarted(run_id=run_id, query=query))
            for provider in self.providers:
                tasks.append(self._search_with_provider(provider, query, max_results_per_query, run_id, emit_cb))
                
        all_results = await asyncio.gather(*tasks)
        
        # Flatten and deduplicate
        flattened = []
        for res_list in all_results:
            flattened.extend(res_list)
            
        await dispatch_event(emit_cb, DeduplicationStarted(run_id=run_id, original_count=len(flattened)))
            
        deduplicated = []
        seen_urls = set()
        for r in flattened:
            url = r.get("url", "")
            if not url:
                continue
            norm_url = self._normalize_url(url)
            if norm_url not in seen_urls:
                seen_urls.add(norm_url)
                r["normalized_url"] = norm_url
                deduplicated.append(r)
                
        await dispatch_event(emit_cb, DeduplicationCompleted(run_id=run_id, unique_count=len(deduplicated)))
        return deduplicated
