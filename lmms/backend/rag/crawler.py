"""
Crawl4AI Crawler Module for LMMs Autonomous Deep Web Research.
Extracts clean Markdown, structured metadata, SPA content, and internal links.
Features smart anti-bot bypass and SPA bundle decoding.
"""

import asyncio
import logging
import re
from typing import Dict, Any, Optional
from urllib.parse import urljoin

logger = logging.getLogger("lmms.rag.crawler")


def _smart_spa_fallback_scraper(url: str, timeout: int = 15) -> Dict[str, Any]:
    """
    Robust fallback scraper that extracts metadata, visible HTML text,
    and SPA JavaScript strings when sites use heavy client-side rendering (React/Vite)
    or trigger anti-bot heuristics in headless browsers.
    """
    try:
        import urllib.request
        from bs4 import BeautifulSoup

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9"
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            html = response.read().decode("utf-8", errors="ignore")

        soup = BeautifulSoup(html, "html.parser")

        # 1. Extract title and all metadata tags
        meta_sections = []
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        if title:
            meta_sections.append(f"# {title}")

        for m in soup.find_all("meta"):
            name = m.get("name") or m.get("property") or m.get("http-equiv")
            content = m.get("content")
            if name and content and len(content.strip()) > 0:
                meta_sections.append(f"- **{name}**: {content.strip()}")

        # 2. Extract standard body text
        for tag in soup(["script", "style", "noscript", "svg", "canvas"]):
            tag.decompose()
        body_text = soup.get_text(separator="\n", strip=True)

        # 3. SPA Asset Analysis: If body text is very short (React/Vite single-page application root)
        spa_strings = []
        if len(body_text) < 400:
            soup_clean = BeautifulSoup(html, "html.parser")
            script_srcs = [s.get("src") for s in soup_clean.find_all("script") if s.get("src")]
            for src in script_srcs[:3]:
                full_js_url = urljoin(url, src)
                try:
                    j_req = urllib.request.Request(full_js_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(j_req, timeout=10) as j_resp:
                        j_text = j_resp.read().decode("utf-8", errors="ignore")
                        # Extract strings from React JSX children
                        matches = re.findall(r'children:[`"\']([^`"\']{15,})[`"\']', j_text)
                        spa_strings.extend(matches[:25])
                        # Extract copyright / author / license info
                        authors = re.findall(r'©[^`"\']+', j_text)
                        spa_strings.extend(authors[:5])
                except Exception:
                    pass

        parts = []
        if meta_sections:
            parts.append("### Page Meta & Author Information:\n" + "\n".join(meta_sections))
        if body_text and len(body_text.strip()) > 50:
            parts.append("### Page Content:\n" + body_text)
        if spa_strings:
            # Deduplicate preserving order
            seen = set()
            clean_strings = []
            for s in spa_strings:
                s_clean = s.strip()
                if s_clean and s_clean not in seen:
                    seen.add(s_clean)
                    clean_strings.append(f"- {s_clean}")
            if clean_strings:
                parts.append("### Rendered Application Text & Copyright:\n" + "\n".join(clean_strings))

        full_markdown = "\n\n".join(parts) if parts else body_text

        return {
            "success": True if full_markdown.strip() else False,
            "url": url,
            "markdown": full_markdown,
            "error": None if full_markdown.strip() else "Empty page content",
            "fallback": True
        }
    except Exception as e:
        return {
            "success": False,
            "url": url,
            "markdown": "",
            "error": f"Scrape error: {str(e)}"
        }


def _crawl4ai_sync_worker(url: str, css_selector: Optional[str] = None, timeout: int = 35) -> Dict[str, Any]:
    """Synchronous worker that uses Crawl4AI with automatic anti-bot / SPA fallback."""
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
                word_count_threshold=5,
                page_timeout=timeout * 1000,
                wait_until="domcontentloaded",
                delay_before_return_html=0.5,
                ignore_body_visibility=True
            )
            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                res = await crawler.arun(url=url, config=run_cfg)
                
                # Check if crawl4ai succeeded AND extracted meaningful content
                md = (res.markdown or "").strip()
                if res.success and len(md) > 100:
                    return {
                        "success": True,
                        "url": url,
                        "markdown": md,
                        "media": getattr(res, "media", {}),
                        "links": getattr(res, "links", {}),
                        "error": None
                    }

                # If crawl4ai reported anti-bot protection or returned an empty SPA shell,
                # seamlessly trigger smart SPA/meta fallback extraction
                err_msg = getattr(res, "error_message", "")
                if "anti-bot" in err_msg.lower() or not res.success or len(md) <= 100:
                    fallback_res = _smart_spa_fallback_scraper(url, timeout=timeout)
                    if fallback_res.get("success") and fallback_res.get("markdown"):
                        return fallback_res
                    return {
                        "success": False,
                        "url": url,
                        "markdown": md if md else "",
                        "error": err_msg or fallback_res.get("error") or "Crawl yielded minimal content"
                    }

                return {
                    "success": True,
                    "url": url,
                    "markdown": md,
                    "error": None
                }
        except Exception as e:
            # Fallback on any crawl4ai exception
            fallback_res = _smart_spa_fallback_scraper(url, timeout=timeout)
            if fallback_res.get("success") and fallback_res.get("markdown"):
                return fallback_res
            return {
                "success": False,
                "url": url,
                "markdown": "",
                "error": f"Crawl4ai: {str(e)} | Fallback: {fallback_res.get('error')}"
            }

    try:
        return asyncio.run(_crawl())
    except Exception as e:
        # Final synchronous fallback attempt
        return _smart_spa_fallback_scraper(url, timeout=timeout)


class AdvancedCrawler:
    """Advanced Web Crawler utilizing Crawl4AI with automatic markdown conversion and SPA fallback."""

    def __init__(self, timeout: int = 40):
        self.timeout = timeout

    def crawl_url(self, url: str, css_selector: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Crawl a URL synchronously and return markdown content, absorbing any extra kwargs."""
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"
        return _crawl4ai_sync_worker(url, css_selector=css_selector, timeout=self.timeout)

    def crawl_and_extract_text(self, url: str, max_chars: int = 15000, **kwargs) -> str:
        """Helper to get a prompt-friendly markdown summary from a URL."""
        res = self.crawl_url(url, **kwargs)
        if not res.get("success"):
            return f"Error crawling {url}: {res.get('error')}"
        md = res.get("markdown", "").strip()
        if not md:
            return f"Notice: No readable text extracted from {url}."
        if len(md) > max_chars:
            md = md[:max_chars] + f"\n\n... [Content truncated to first {max_chars} chars for model efficiency]"
        return f"=== Crawled from {url} ===\n\n{md}"
