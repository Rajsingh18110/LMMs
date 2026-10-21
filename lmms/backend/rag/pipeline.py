"""
Consolidated RAG Pipeline for LMMs.
Integrates Crawl4AI web crawling, smart chunking, indexing, and semantic retrieval.
"""

import os
from typing import Optional, Dict, Any

from lmms.backend.rag.crawler import AdvancedCrawler
from lmms.backend.rag.indexer import RAGIndexer
from lmms.backend.rag.retriever import RAGRetriever


class RAGPipeline:
    """Unified entry point for all RAG operations in LMMs."""

    def __init__(self, workspace_id: Optional[str] = None):
        self.workspace_id = workspace_id or "global"
        self.crawler = AdvancedCrawler()
        self.indexer = RAGIndexer(self.workspace_id)
        self.retriever = RAGRetriever(self.workspace_id)

    def search(self, query: str, k: int = 5, max_tokens: Optional[int] = None) -> str:
        """Search workspace vector knowledge."""
        return self.retriever.search(query=query, k=k, max_tokens=max_tokens)

    def crawl_url(self, url: str, css_selector: Optional[str] = None, max_chars: int = 15000) -> str:
        """Directly crawl any URL using Crawl4AI and return clean markdown text."""
        return self.crawler.crawl_and_extract_text(url=url, max_chars=max_chars)

    def crawl_and_index_url(self, url: str, css_selector: Optional[str] = None) -> str:
        """Crawl a URL using Crawl4AI and automatically ingest it into vector memory."""
        res = self.crawler.crawl_url(url=url, css_selector=css_selector)
        if not res.get("success"):
            return f"Error crawling {url}: {res.get('error')}"

        markdown = res.get("markdown", "")
        if not markdown.strip():
            return f"Notice: No readable text extracted from {url}."

        try:
            chunks_indexed = self.indexer.index_text(
                markdown,
                source=url,
                metadata={"type": "web_url", "url": url}
            )
            return f"Successfully crawled and indexed {chunks_indexed} chunks from {url}"
        except Exception as e:
            return f"Error indexing crawled content from {url}: {str(e)}"

    def ingest_file(self, path: str) -> str:
        """Ingest single file into vector memory."""
        return self.indexer.index_file(path)

    def ingest_directory(self, path: str) -> str:
        """Ingest entire directory into vector memory."""
        return self.indexer.index_directory(path)


# Global helper instance
_active_pipelines: Dict[str, RAGPipeline] = {}

def get_rag_pipeline(workspace_id: Optional[str] = None) -> RAGPipeline:
    ws = workspace_id or "global"
    if ws not in _active_pipelines:
        _active_pipelines[ws] = RAGPipeline(workspace_id=ws)
    return _active_pipelines[ws]
