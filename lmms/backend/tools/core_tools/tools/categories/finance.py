import httpx
from ..base import ToolDefinition, ToolResult, \
                   AuthType, ToolCategory

# Gold Price — no auth needed
GOLD_PRICE_TOOL = ToolDefinition(
    name        = "get_gold_price",
    description = "Get live gold price in USD, INR, "
                  "EUR. Returns current price per gram "
                  "and per troy ounce.",
    category    = ToolCategory.FINANCE,
    auth_type   = AuthType.NONE,
    base_url    = "https://api.metals.live/v1/spot",
    parameters  = {
        "type": "object",
        "properties": {
            "currency": {
                "type": "string",
                "enum": ["USD", "INR", "EUR", "GBP"],
                "description": "Currency for price"
            }
        },
        "required": []
    },
    requires_key = False,
)

async def execute_gold_price(params: dict) -> ToolResult:
    currency = params.get("currency", "USD")
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(
                "https://api.metals.live/v1/spot/gold")
            data = r.json()
            return ToolResult(
                tool_name = "get_gold_price",
                success   = True,
                data      = {
                    "gold_usd_per_oz": data[0]["price"],
                    "currency": currency,
                    "unit": "troy_ounce"
                }
            )
        except Exception as e:
            return ToolResult(
                tool_name = "get_gold_price",
                success   = False,
                data      = None,
                error     = str(e)
            )
