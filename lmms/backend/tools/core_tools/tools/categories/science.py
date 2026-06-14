import httpx
from ..base import ToolDefinition, ToolResult, \
                   AuthType, ToolCategory

NASA_APOD_TOOL = ToolDefinition(
    name        = "nasa_apod",
    description = "NASA Astronomy Picture of the Day. "
                  "Returns today's space image + "
                  "explanation.",
    category    = ToolCategory.SCIENCE,
    auth_type   = AuthType.NONE,
    base_url    = "https://api.nasa.gov/planetary/apod",
    parameters  = {
        "type": "object",
        "properties": {
            "date": {
                "type": "string",
                "description": "Date YYYY-MM-DD "
                               "(default: today)"
            }
        },
        "required": []
    },
    requires_key = False,  # demo key works
)

async def execute_nasa_apod(params: dict) -> ToolResult:
    date = params.get("date")
    query_params = {"api_key": "DEMO_KEY"}
    if date:
        query_params["date"] = date
        
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(NASA_APOD_TOOL.base_url, params=query_params)
            data = r.json()
            return ToolResult(
                tool_name = "nasa_apod",
                success   = True,
                data      = data
            )
        except Exception as e:
            return ToolResult(
                tool_name = "nasa_apod",
                success   = False,
                data      = None,
                error     = str(e)
            )
