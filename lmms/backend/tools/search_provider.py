# Copyright 2026 LMMs Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import base64
from urllib.parse import parse_qs, urlparse, unquote, quote
import requests
from bs4 import BeautifulSoup


class SearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, max_results: int = 24) -> List[Dict[str, Any]]:
        """
        Executes a search and returns structured results.
        Expected keys in each dict: title, url, snippet, source, retrieved_at
        """
        pass


class DDGSSearchProvider(SearchProvider):
    """
    High-capacity, fault-tolerant search provider supporting up to 24 search results.
    Combines DDGS API with Bing scraping, Wikipedia knowledge API, and web scraping fallbacks.
    """

    def search(self, query: str, max_results: int = 24) -> List[Dict[str, Any]]:
        results = []
        seen_urls = set()

        # 1. Attempt primary DDGS package if available and working
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")
                try:
                    from ddgs import DDGS
                except ImportError:
                    from duckduckgo_search import DDGS
                with DDGS() as ddgs:
                    for r in ddgs.text(query, max_results=max_results):
                        href = r.get("href", "")
                        if href and href not in seen_urls:
                            seen_urls.add(href)
                            results.append({
                                "title": r.get("title", ""),
                                "url": href,
                                "snippet": r.get("body", ""),
                                "source": "ddgs",
                                "retrieved_at": datetime.datetime.now().isoformat()
                            })
            if len(results) >= max_results:
                return results[:max_results]
        except Exception:
            pass

        # 2. Resilient Bing web search with clean base64 link resolution
        try:
            session = requests.Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
                "Accept-Language": "en-US,en;q=0.9",
            })
            queries_to_try = [query, f"{query} latest updates", f"{query} overview resources"]
            for q in queries_to_try:
                if len(results) >= max_results:
                    break
                b_url = f"https://www.bing.com/search?q={quote(q)}"
                resp = session.get(b_url, timeout=8)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                for li in soup.find_all("li", class_="b_algo"):
                    h2 = li.find("h2")
                    if not h2:
                        continue
                    a = h2.find("a")
                    if not a or not a.get("href"):
                        continue
                    title = a.get_text(strip=True)
                    raw_href = a["href"]
                    href = raw_href
                    if "bing.com/ck/a" in raw_href:
                        parsed = parse_qs(urlparse(raw_href).query)
                        if "u" in parsed:
                            u_val = parsed["u"][0]
                            if u_val.startswith("a1"):
                                b64 = u_val[2:] + "=" * ((4 - len(u_val[2:]) % 4) % 4)
                                try:
                                    href = base64.b64decode(b64).decode("utf-8", errors="ignore")
                                except Exception:
                                    pass
                    if not href.startswith("http") or href in seen_urls:
                        continue
                    seen_urls.add(href)
                    p = li.find("p") or li.find("div", class_="b_caption")
                    snippet = p.get_text(strip=True) if p else ""
                    results.append({
                        "title": title,
                        "url": href,
                        "snippet": snippet,
                        "source": "web_search",
                        "retrieved_at": datetime.datetime.now().isoformat()
                    })
                    if len(results) >= max_results:
                        break
        except Exception:
            pass

        # 3. Wikipedia API for encyclopedic, technical, and historical background depth
        if len(results) < max_results:
            try:
                w_url = "https://en.wikipedia.org/w/api.php"
                needed = max_results - len(results)
                params = {
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "format": "json",
                    "srlimit": min(needed, 24)
                }
                w_resp = requests.get(w_url, params=params, headers={"User-Agent": "LMMsSearchBot/1.0"}, timeout=5)
                if w_resp.status_code == 200:
                    w_items = w_resp.json().get("query", {}).get("search", [])
                    for item in w_items:
                        page_title = item.get("title", "")
                        page_url = f"https://en.wikipedia.org/wiki/{page_title.replace(' ', '_')}"
                        if page_url not in seen_urls:
                            seen_urls.add(page_url)
                            clean_snippet = BeautifulSoup(item.get("snippet", ""), "html.parser").get_text()
                            results.append({
                                "title": page_title,
                                "url": page_url,
                                "snippet": clean_snippet,
                                "source": "wikipedia",
                                "retrieved_at": datetime.datetime.now().isoformat()
                            })
                        if len(results) >= max_results:
                            break
            except Exception:
                pass

        return results[:max_results]
