import asyncio
import aiohttp
import time
from typing import Dict, Any, List, Optional, Callable
from bs4 import BeautifulSoup

from lmms.backend.research.events import (
    ResearchEvent, FetchStarted, FetchCompleted, FetchFailed, ExtractionStarted, ExtractionCompleted, dispatch_event
)

class ContentParser:
    """Intelligently extracts readable content while removing noise."""
    
    def parse(self, html: str) -> str:
        if not html:
            return ""
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove noisy elements
        for element in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "iframe"]):
            element.decompose()
            
        # Extract title and main text
        title = soup.title.string if soup.title else ""
        
        # Try to find the main content article if semantic tags exist
        main_content = soup.find('article') or soup.find('main') or soup.body
        
        if not main_content:
            return title
            
        # Get text, joining with newlines, collapsing multiple spaces
        text = main_content.get_text(separator='\n', strip=True)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Re-join
        content = f"TITLE: {title}\n\n" + "\n".join(lines)
        return content[:15000] # Limit size to prevent blowing up context

class URLFetcher:
    """Asynchronously fetches and parses URLs with timeouts and size limits."""
    
    def __init__(self, concurrency_limit: int = 5, timeout_sec: int = 15, max_size_bytes: int = 5 * 1024 * 1024):
        self.semaphore = asyncio.Semaphore(concurrency_limit)
        self.timeout = aiohttp.ClientTimeout(total=timeout_sec)
        self.max_size = max_size_bytes
        self.parser = ContentParser()
        
    async def fetch_one(self, session: aiohttp.ClientSession, url: str, run_id: str, emit_cb: Optional[Callable[[ResearchEvent], Any]] = None) -> Dict[str, Any]:
        async with self.semaphore:
            start_time = time.monotonic()
            await dispatch_event(emit_cb, FetchStarted(run_id=run_id, url=url))
            try:
                # We do not download the whole file if it's huge or not HTML
                async with session.get(url, timeout=self.timeout, allow_redirects=True) as response:
                    response.raise_for_status()
                    
                    content_type = response.headers.get('Content-Type', '').lower()
                    if 'text/html' not in content_type and 'text/plain' not in content_type:
                        duration = int((time.monotonic() - start_time) * 1000)
                        await dispatch_event(emit_cb, FetchFailed(run_id=run_id, url=url, error=f"Unsupported content type: {content_type}", duration_ms=duration))
                        return {"url": url, "success": False, "error": f"Unsupported content type: {content_type}"}
                    
                    # Read in chunks to enforce size limit
                    chunks = []
                    size = 0
                    async for chunk in response.content.iter_chunked(8192):
                        size += len(chunk)
                        if size > self.max_size:
                            duration = int((time.monotonic() - start_time) * 1000)
                            await dispatch_event(emit_cb, FetchFailed(run_id=run_id, url=url, error="Response exceeded maximum size limit", duration_ms=duration))
                            return {"url": url, "success": False, "error": "Response exceeded maximum size limit"}
                        chunks.append(chunk)
                        
                    html_bytes = b"".join(chunks)
                    html_text = html_bytes.decode('utf-8', errors='replace')
                    
                    duration = int((time.monotonic() - start_time) * 1000)
                    await dispatch_event(emit_cb, FetchCompleted(run_id=run_id, url=url, duration_ms=duration))
                    
                    await dispatch_event(emit_cb, ExtractionStarted(run_id=run_id, url=url))
                    parsed_content = self.parser.parse(html_text)
                    await dispatch_event(emit_cb, ExtractionCompleted(run_id=run_id, url=url))
                    
                    return {"url": url, "success": True, "content": parsed_content}
                    
            except asyncio.TimeoutError:
                duration = int((time.monotonic() - start_time) * 1000)
                await dispatch_event(emit_cb, FetchFailed(run_id=run_id, url=url, error="Connection timed out", duration_ms=duration))
                return {"url": url, "success": False, "error": "Connection timed out"}
            except aiohttp.ClientError as e:
                duration = int((time.monotonic() - start_time) * 1000)
                await dispatch_event(emit_cb, FetchFailed(run_id=run_id, url=url, error=f"HTTP Client error: {str(e)}", duration_ms=duration))
                return {"url": url, "success": False, "error": f"HTTP Client error: {str(e)}"}
            except Exception as e:
                duration = int((time.monotonic() - start_time) * 1000)
                await dispatch_event(emit_cb, FetchFailed(run_id=run_id, url=url, error=f"Unexpected fetch error: {str(e)}", duration_ms=duration))
                return {"url": url, "success": False, "error": f"Unexpected fetch error: {str(e)}"}

    async def fetch_all(self, urls: List[str], run_id: str = "test", emit_cb: Optional[Callable[[ResearchEvent], Any]] = None) -> List[Dict[str, Any]]:
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_one(session, url, run_id, emit_cb) for url in urls]
            return await asyncio.gather(*tasks)
