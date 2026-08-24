import hashlib
import datetime
from typing import List, Dict, Any

from lmms.backend.research.result import Evidence, Citation

class EvidenceStore:
    """Stores extracted evidence mapped to their sources and metadata."""
    
    def __init__(self):
        self.evidence: List[Evidence] = []
        
    def _generate_identifier(self, url: str) -> str:
        """Generates a stable, unique source identifier."""
        return hashlib.md5(url.encode('utf-8')).hexdigest()[:8]
        
    def add_evidence(self, url: str, title: str, content: str):
        if not content.strip():
            return
            
        ev = Evidence(
            source_url=url,
            title=title,
            content=content,
            retrieved_at=datetime.datetime.now().isoformat(),
            source_identifier=self._generate_identifier(url)
        )
        self.evidence.append(ev)
        
    def get_all(self) -> List[Evidence]:
        return self.evidence

class CitationManager:
    """Manages citations for evidence to be safely injected into LLM context."""
    
    def __init__(self):
        self.citations: List[Citation] = []
        self._counter = 1
        
    def build_citations(self, evidence_store: EvidenceStore) -> List[Citation]:
        self.citations = []
        self._counter = 1
        
        for ev in evidence_store.get_all():
            cit = Citation(number=self._counter, evidence=ev)
            self.citations.append(cit)
            self._counter += 1
            
        return self.citations
        
    def format_for_llm(self) -> str:
        """Formats the collected citations into a string suitable for an LLM prompt."""
        if not self.citations:
            return "No citations available."
            
        formatted = []
        for c in self.citations:
            formatted.append(f"[{c.number}] Source: {c.evidence.title} ({c.evidence.source_url})")
            formatted.append(f"Retrieved: {c.evidence.retrieved_at}")
            formatted.append("--- Snippet ---")
            formatted.append(c.evidence.content)
            formatted.append("----------------")
            
        return "\n".join(formatted)
