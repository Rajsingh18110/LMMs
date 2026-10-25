"""
site_adapters.py — Optional, Explicitly Registered Site-Specific Adapters for LMMs.

The core browser agent is completely website-independent and discovers UI elements,
forms, editors, and action buttons dynamically from live DOM observations.

Site adapters are strictly optional hints that can provide specialized domain knowledge
(such as custom editor selectors or draft storage keys) without hardcoding site-specific
assumptions into the core agent loop or browser backend.
"""

from typing import Dict, Any, Optional, List
import urllib.parse


class BaseSiteAdapter:
    """Base class for optional domain-specific adapters."""
    domain: str = ""

    def matches(self, url: str) -> bool:
        if not url or not self.domain:
            return False
        try:
            parsed = urllib.parse.urlparse(url)
            host = (parsed.hostname or "").lower()
            return host == self.domain.lower() or host.endswith("." + self.domain.lower())
        except Exception:
            return False

    def get_editor_hints(self) -> Dict[str, Any]:
        """Optional hints for rich text or custom editors."""
        return {}

    def get_save_draft_hints(self) -> List[str]:
        """Optional button label or selector hints for saving drafts."""
        return []

    def get_publish_hints(self) -> List[str]:
        """Optional button label or selector hints for publication controls."""
        return []


class ReadXHubAdapter(BaseSiteAdapter):
    """Optional adapter for readxhub.in providing editor hints."""
    domain = "readxhub.in"

    def get_editor_hints(self) -> Dict[str, Any]:
        return {
            "title_selectors": ["input[placeholder*='title' i]", "input[name='title']"],
            "body_selectors": ["p.document-paragraph", "div.document-paragraph", "[contenteditable='true']"],
            "description_selectors": ["textarea[placeholder*='description' i]"]
        }

    def get_save_draft_hints(self) -> List[str]:
        return ["button:has-text('Save draft')", "button:has-text('Save Draft')", "Save draft"]

    def get_publish_hints(self) -> List[str]:
        return ["button:has-text('Publish Post')", "Publish Post"]


class SiteAdapterRegistry:
    """Registry of optional site-specific adapters."""
    _adapters: List[BaseSiteAdapter] = [
        ReadXHubAdapter()
    ]

    @classmethod
    def register(cls, adapter: BaseSiteAdapter):
        cls._adapters.append(adapter)

    @classmethod
    def get_adapter_for_url(cls, url: str) -> Optional[BaseSiteAdapter]:
        for adapter in cls._adapters:
            if adapter.matches(url):
                return adapter
        return None


def get_site_adapter(url: str) -> Optional[BaseSiteAdapter]:
    """Retrieves an optional site adapter for a URL if registered, else None."""
    return SiteAdapterRegistry.get_adapter_for_url(url)
