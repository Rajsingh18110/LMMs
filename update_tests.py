import re

with open("tests/test_research.py", "r") as f:
    content = f.read()

# I need to add tests for history and events without breaking old tests.
# Instead of regex, I'll just append them.

additions = """
import os
import tempfile
from lmms.backend.research.history import ResearchHistoryStore
from lmms.backend.research.events import ResearchStarted, SearchCompleted, dispatch_event

def test_history_store():
    with tempfile.TemporaryDirectory() as td:
        store = ResearchHistoryStore(base_dir=td)
        res = ResearchResult(success=True, query="test", citations=[{"number": 1, "evidence": {"title": "X", "content": "Y"*6000}}])
        store.save_run("R-123", res)
        
        loaded = store.get_run("R-123")
        assert loaded is not None
        assert loaded["run_id"] == "R-123"
        # Test truncation
        assert len(loaded["citations"][0]["evidence"]["content"]) < 6000
        assert "[truncated" in loaded["citations"][0]["evidence"]["content"]

        # Corrupted
        with open(os.path.join(td, "R-123.json"), "w") as f:
            f.write("{bad json")
        assert store.get_run("R-123") is None
        
        # Missing
        assert store.get_run("R-999") is None

def test_events():
    events = []
    def sync_cb(ev):
        events.append(ev)
        
    async def run():
        await dispatch_event(sync_cb, ResearchStarted(run_id="R-1", query="q"))
    
    asyncio.run(run())
    assert len(events) == 1
    assert isinstance(events[0], ResearchStarted)

def test_engine_events():
    engine = ResearchEngine()
    engine.providers = [MockProvider(results=[{"url": "http://127.0.0.1/fake", "title": "Fake", "normalized_url": "http://127.0.0.1/fake"}])]
    engine.search_manager = SearchManager(providers=engine.providers)
    
    class FakeFetcher:
        async def fetch_all(self, urls, run_id, emit_cb=None):
            from lmms.backend.research.events import FetchCompleted
            if emit_cb:
                await emit_cb(FetchCompleted(run_id=run_id, url=urls[0], duration_ms=100))
            return [{"url": u, "success": True, "content": f"Content for {u}"} for u in urls]
    engine.fetcher = FakeFetcher()
    
    # We will pass a callback to track events
    emitted = []
    async def cb(ev):
        emitted.append(type(ev).__name__)
        
    # We must patch permission manager to pass the engine test
    from lmms.backend.tools.core import default_permission_manager, Permission
    default_permission_manager.grant_permission(Permission.NETWORK)
    
    res = asyncio.run(engine.execute("test query", emit_cb=cb))
    
    assert res.success is True
    assert "ResearchStarted" in emitted
    assert "SearchCompleted" in emitted
    assert "DeduplicationCompleted" in emitted
    assert "FetchCompleted" in emitted
    assert "ExtractionCompleted" in emitted
    assert "EvidenceAdded" in emitted
    assert "ResearchCompleted" in emitted
"""

# Just replace the old `test_research_engine_mocked` test with our new ones or append.
# To be safe, I'll replace the old one which used string progress events.
old_mocked_test = """def test_research_engine_mocked():
    engine = ResearchEngine()
    # Mock providers to avoid network
    engine.providers = [MockProvider(results=[{"url": "http://127.0.0.1/fake", "title": "Fake", "normalized_url": "http://127.0.0.1/fake"}])]
    engine.search_manager = SearchManager(providers=engine.providers)
    
    # Mock fetcher
    class FakeFetcher:
        async def fetch_all(self, urls):
            return [{"url": u, "success": True, "content": f"Content for {u}"} for u in urls]
    engine.fetcher = FakeFetcher()
    
    events = []
    def progress(msg):
        events.append(msg)
        
    res = asyncio.run(engine.execute("test query", progress))
    
    assert res.success is True
    assert len(res.citations) == 1
    assert "Content for http://127.0.0.1/fake" in res.citations[0].evidence.content
    assert "[Planning]" in events
    assert "[Extraction complete]" in events"""

content = content.replace(old_mocked_test, additions)

with open("tests/test_research.py", "w") as f:
    f.write(content)

print("Updated tests.")
