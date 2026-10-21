"""
Backwards-compatibility shim for lmms.backend.tools.rag.
Delegates to the modern consolidated lmms.backend.rag package.
"""

from lmms.backend.rag.pipeline import RAGPipeline, get_rag_pipeline
from lmms.backend.rag.crawler import AdvancedCrawler

class RAGTool:
    """Backwards-compatible wrapper around RAGPipeline."""
    def __init__(self, workspace_id: str):
        self.workspace_id = workspace_id
        self.pipeline = get_rag_pipeline(workspace_id)
        self.db = self.pipeline.indexer.db

    def ingest_file(self, path: str) -> str:
        return self.pipeline.ingest_file(path)

    def ingest_directory(self, path: str) -> str:
        return self.pipeline.ingest_directory(path)

    def ingest_url(self, url: str) -> str:
        return self.pipeline.crawl_and_index_url(url)

    def search(self, query: str, k: int = 5, max_tokens: int = None) -> str:
        return self.pipeline.search(query=query, k=k, max_tokens=max_tokens)
