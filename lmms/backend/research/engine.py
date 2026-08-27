import asyncio
import time
from typing import Callable, List, Optional, Any

from lmms.backend.research.result import ResearchResult
from lmms.backend.research.search_manager import SearchManager, DDGSAsyncProvider
from lmms.backend.research.fetcher import URLFetcher
from lmms.backend.research.evidence import EvidenceStore, CitationManager
from lmms.backend.research.history import ResearchHistoryStore
from lmms.backend.research.events import (
    ResearchEvent, ResearchStarted, ResearchCompleted, ResearchFailed,
    EvidenceAdded, generate_run_id, dispatch_event
)

# Import from Tool Runtime to ensure we enforce permissions
from lmms.backend.tools.core import default_permission_manager, Permission

class ResearchEngine:
    """
    Main orchestrator for Web Research.
    Wires together SearchManager, URLFetcher, EvidenceStore, and CitationManager.
    """
    
    def __init__(self, concurrency_limit=3):
        # We instantiate internal providers. We must check NETWORK permission before running.
        self.providers = [DDGSAsyncProvider()]
        self.search_manager = SearchManager(providers=self.providers, concurrency_limit=concurrency_limit)
        self.fetcher = URLFetcher(concurrency_limit=concurrency_limit)
        self.evidence_store = EvidenceStore()
        self.citation_manager = CitationManager()
        self.history_store = ResearchHistoryStore()

    async def execute(self, query: str, emit_cb: Optional[Callable[[ResearchEvent], Any]] = None) -> ResearchResult:
        
        run_id = generate_run_id()
        start_time = time.monotonic()
        await dispatch_event(emit_cb, ResearchStarted(run_id=run_id, query=query))
        
        errors = []
        
        # 1. Enforce ToolRuntime permission policy (NETWORK is required)
        if not default_permission_manager.check_permission([Permission.WEB_SEARCH]):
            error_msg = "Permission Denied: NETWORK permission is required for Web Research."
            await dispatch_event(emit_cb, ResearchFailed(run_id=run_id, error=error_msg))
            res = ResearchResult(
                success=False,
                query=query,
                errors=[error_msg]
            )
            self.history_store.save_run(run_id, res)
            return res

        try:
            # 2. Planning
            queries = [query]
            
            # 3. Searching
            search_results = await self.search_manager.search_parallel(queries, max_results_per_query=5, run_id=run_id, emit_cb=emit_cb)
            
            # 4. Deduplication
            urls_to_fetch = [r["normalized_url"] for r in search_results if "normalized_url" in r]
            
            # 5. Fetching
            fetch_results = await self.fetcher.fetch_all(urls_to_fetch, run_id=run_id, emit_cb=emit_cb)
            
            sources = []
            successful_fetches = []
            
            for f_res in fetch_results:
                sources.append({
                    "url": f_res["url"],
                    "success": f_res["success"],
                    "error": f_res.get("error")
                })
                if f_res["success"]:
                    successful_fetches.append(f_res)
                else:
                    errors.append(f"Failed to fetch {f_res['url']}: {f_res.get('error')}")
                    
            # 6. Extraction & Evidence Collection
            for f_res in successful_fetches:
                # Find matching original title from search results if possible
                original_title = "Unknown Title"
                for s_res in search_results:
                    if s_res.get("normalized_url") == f_res["url"]:
                        original_title = s_res.get("title", "Unknown Title")
                        break
                        
                self.evidence_store.add_evidence(
                    url=f_res["url"],
                    title=original_title,
                    content=f_res["content"]
                )
                await dispatch_event(emit_cb, EvidenceAdded(run_id=run_id, url=f_res["url"]))
                
            # 7. Build Citations
            citations = self.citation_manager.build_citations(self.evidence_store)
            
            duration_ms = int((time.monotonic() - start_time) * 1000)
            await dispatch_event(emit_cb, ResearchCompleted(run_id=run_id, duration_ms=duration_ms))
            
            res = ResearchResult(
                success=True,
                query=query,
                sources=sources,
                evidence=self.evidence_store.get_all(),
                citations=citations,
                errors=errors,
                metadata={
                    "total_searches": len(search_results),
                    "total_fetched": len(successful_fetches)
                }
            )
            self.history_store.save_run(run_id, res)
            return res

        except Exception as e:
            await dispatch_event(emit_cb, ResearchFailed(run_id=run_id, error=str(e)))
            res = ResearchResult(
                success=False,
                query=query,
                errors=[f"Research engine failed: {str(e)}"]
            )
            self.history_store.save_run(run_id, res)
            return res
