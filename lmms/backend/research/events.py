from dataclasses import dataclass, field
import datetime
import uuid
import asyncio
from typing import Optional, Callable, Any

def generate_run_id() -> str:
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    short_id = uuid.uuid4().hex[:6]
    return f"R-{date_str}-{short_id}"

@dataclass(kw_only=True)
class ResearchEvent:
    run_id: str
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.datetime.now().isoformat()

# Core Lifecycle Events
@dataclass(kw_only=True)
class ResearchStarted(ResearchEvent):
    query: str

@dataclass(kw_only=True)
class ResearchCompleted(ResearchEvent):
    duration_ms: int

@dataclass(kw_only=True)
class ResearchFailed(ResearchEvent):
    error: str

# Searching Events
@dataclass(kw_only=True)
class SearchStarted(ResearchEvent):
    query: str

@dataclass(kw_only=True)
class SearchCompleted(ResearchEvent):
    query: str
    result_count: int
    duration_ms: int

@dataclass(kw_only=True)
class SearchFailed(ResearchEvent):
    query: str
    provider: str
    error: str
    duration_ms: int

# Deduplication Events
@dataclass(kw_only=True)
class DeduplicationStarted(ResearchEvent):
    original_count: int

@dataclass(kw_only=True)
class DeduplicationCompleted(ResearchEvent):
    unique_count: int

# Fetching Events
@dataclass(kw_only=True)
class FetchStarted(ResearchEvent):
    url: str

@dataclass(kw_only=True)
class FetchCompleted(ResearchEvent):
    url: str
    duration_ms: int

@dataclass(kw_only=True)
class FetchFailed(ResearchEvent):
    url: str
    error: str
    duration_ms: int

# Extraction Events
@dataclass(kw_only=True)
class ExtractionStarted(ResearchEvent):
    url: str

@dataclass(kw_only=True)
class ExtractionCompleted(ResearchEvent):
    url: str

@dataclass(kw_only=True)
class EvidenceAdded(ResearchEvent):
    url: str

async def dispatch_event(callback: Optional[Callable[[ResearchEvent], Any]], event: ResearchEvent):
    """Safely dispatches an event to a sync or async callback."""
    if not callback:
        return
        
    try:
        if asyncio.iscoroutinefunction(callback):
            await callback(event)
        else:
            callback(event)
    except Exception as e:
        print(f"Event dispatch error: {e}")
