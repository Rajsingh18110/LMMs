"""
Crawl4AI Crawler Module for LMMs Autonomous Deep Web Research.
Extracts clean Markdown, structured metadata, and internal links.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("lmms.rag.crawler")

def _crawl4ai_sync_worker(url: str, css_selector: Optional[str] = None, timeout: int = 35) -> Dict[str, Any]:
    """Synchronous worker designed to safely execute async crawl4ai in a worker process/thread."""
    async def _crawl():
        try:
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
            
            browser_cfg = BrowserConfig(
                headless=True,
                verbose=False,
                extra_args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            run_cfg = CrawlerRunConfig(
                css_selector=css_selector if css_selector else None,
                word_count_threshold=10,
                page_timeout=timeout * 1000,
            )
            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                res = await crawler.arun(url=url, config=run_cfg)
                if not res.success:
                    return {
                        "success": False,
                        "url": url,
                        "markdown": "",
                        "error": getattr(res, "error_message", "Crawl failed")
                    }
                
                # Extract markdown, title, and links
                md = res.markdown or ""
                return {
                    "success": True,
                    "url": url,
                    "markdown": md,
                    "media": getattr(res, "media", {}),
                    "links": getattr(res, "links", {}),
                    "error": None
                }
        except Exception as e:
            # Fallback to Playwright or standard requests if crawl4ai raises
            try:
                import urllib.request
                from bs4 import BeautifulSoup
                
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
                )
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    html = response.read().decode("utf-8", errors="ignore")
                
                soup = BeautifulSoup(html, "html.parser")
                for s in soup(["script", "style", "noscript", "svg"]):
                    s.decompose()
                text = soup.get_text(separator="\n", strip=True)
                return {
                    "success": True,
                    "url": url,
                    "markdown": text,
                    "error": None,
                    "fallback": True
                }
            except Exception as fe:
                return {
                    "success": False,
                    "url": url,
                    "markdown": "",
                    "error": f"Crawl4ai error: {str(e)} | Fallback error: {str(fe)}"
                }

    try:
        return asyncio.run(_crawl())
    except Exception as e:
        return {
            "success": False,
            "url": url,
            "markdown": "",
            "error": str(e)
        }


class AdvancedCrawler:
    """Advanced Web Crawler utilizing Crawl4AI with automatic markdown conversion."""
    
    def __init__(self, timeout: int = 40):
        self.timeout = timeout

    def crawl_url(self, url: str, css_selector: Optional[str] = None) -> Dict[str, Any]:
        """Crawl a URL synchronously and return markdown content."""
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"
        return _crawl4ai_sync_worker(url, css_selector=css_selector, timeout=self.timeout)

    def crawl_and_extract_text(self, url: str, max_chars: int = 15000) -> str:
        """Helper to get a prompt-friendly markdown summary from a URL."""
        res = self.crawl_url(url)
        if not res.get("success"):
            return f"Error crawling {url}: {res.get('error')}"
        md = res.get("markdown", "").strip()
        if not md:
            return f"Notice: No readable text extracted from {url}."
        if len(md) > max_chars:
            md = md[:max_chars] + f"\n\n... [Content truncated to first {max_chars} chars for model efficiency]"
        return f"=== Crawled from {url} ===\n\n{md}"
