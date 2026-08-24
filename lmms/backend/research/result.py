from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class Evidence:
    """Represents an extracted piece of evidence from a source."""
    source_url: str
    title: str
    content: str
    retrieved_at: str
    source_identifier: str # A unique hash or slug for the source

@dataclass
class Citation:
    """Represents a formatted citation linking back to the evidence."""
    number: int
    evidence: Evidence

@dataclass
class ResearchResult:
    """The structured final result returned by the ResearchEngine."""
    success: bool
    query: str
    sources: List[Dict[str, Any]] = field(default_factory=list) # URL, title, status (success/failed)
    evidence: List[Evidence] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
