import httpx
from ..base import ToolDefinition, ToolResult, AuthType, ToolCategory

WEATHER_TOOL = ToolDefinition(
    name        = "weather",
    description = "Get current weather for a location using wttr.in.",
    category    = ToolCategory.SCIENCE,
    auth_type   = AuthType.NONE,
    base_url    = "https://wttr.in",
    parameters  = {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "City or location name"
            }
        },
        "required": ["location"]
    },
    requires_key = False,
)

async def execute_weather(params: dict) -> ToolResult:
    location = params.get("location", "")
    
    url = f"https://wttr.in/{location}?format=j1"
    
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(url)
            if r.status_code == 200:
                data = r.json()
                return ToolResult(
                    tool_name = "weather",
                    success   = True,
                    data      = data
                )
            else:
                return ToolResult(
                    tool_name = "weather",
                    success   = False,
                    data      = None,
                    error     = f"HTTP Error {r.status_code}"
                )
        except Exception as e:
            return ToolResult(
                tool_name = "weather",
                success   = False,
                data      = None,
                error     = str(e)
            )
