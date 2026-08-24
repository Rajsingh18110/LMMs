import datetime
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class SearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Executes a search and returns structured results.
        Expected keys in each dict: title, url, snippet, source, retrieved_at
        """
        pass

class DDGSSearchProvider(SearchProvider):
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
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
