from dataclasses import dataclass, field
from typing import Any
from enum import Enum

class AuthType(Enum):
    NONE    = "none"      # No key needed — free direct
    API_KEY = "apikey"    # Free key required
    OAUTH   = "oauth"     # Complex — skip Phase E

class ToolCategory(Enum):
    FINANCE       = "finance"
    WEATHER       = "weather"
    SEARCH        = "search"
    NEWS          = "news"
    SCIENCE       = "science"
    GEO           = "geo"
    CRYPTO        = "crypto"
    SOCIAL        = "social"
    UTILITY       = "utility"
    GOVERNMENT    = "government"
    COMMUNICATION = "communication"
    GENERAL       = "general"

@dataclass
class ToolDefinition:
    """
    OpenAI function-calling compatible format.
    ANY model that supports tool use can use this.
    Qwen, Llama, Sarvam, Mistral — all work.
    """
    name:        str          # "get_gold_price"
    description: str          # "Fetch live gold price in USD/INR"
    category:    ToolCategory
    auth_type:   AuthType
    base_url:    str
    parameters:  dict         # JSON Schema format
    requires_key: bool = False
    key_env_name: str  = ""   # "GOLD_API_KEY"
    enabled:     bool  = True
    rate_limit:  int   = 60   # calls per minute
    
    def to_openai_format(self) -> dict:
        """
        Returns OpenAI function-calling format.
        Works with ANY model that supports tools.
        """
        return {
            "type": "function",
            "function": {
                "name":        self.name,
                "description": self.description,
                "parameters":  self.parameters,
            }
        }

@dataclass  
class ToolResult:
    tool_name:  str
    success:    bool
    data:       Any        # raw API response
    error:      str = ""
    cached:     bool = False
    fetched_at: str  = ""
