import httpx
from ..base import ToolResult

async def execute_crypto_price(params: dict) -> ToolResult:
    coin = params.get("coin", "bitcoin").lower()
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd,eur")
            if r.status_code == 200:
                return ToolResult(tool_name="crypto_price", success=True, data=r.json())
            return ToolResult(tool_name="crypto_price", success=False, data=None, error=f"Status: {r.status_code}")
        except Exception as e:
            return ToolResult(tool_name="crypto_price", success=False, data=None, error=str(e))

async def execute_crypto_market_data(params: dict) -> ToolResult:
    coin = params.get("coin", "bitcoin").lower()
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(f"https://api.coingecko.com/api/v3/coins/{coin}?localization=false&tickers=false&community_data=false&developer_data=false&sparkline=false")
            if r.status_code == 200:
                data = r.json()
                md = data.get("market_data", {})
                res = {
                    "name": data.get("name"),
                    "symbol": data.get("symbol"),
                    "current_price_usd": md.get("current_price", {}).get("usd"),
                    "market_cap_usd": md.get("market_cap", {}).get("usd"),
                    "price_change_24h": md.get("price_change_24h")
                }
                return ToolResult(tool_name="crypto_market_data", success=True, data=res)
            return ToolResult(tool_name="crypto_market_data", success=False, data=None, error=f"Status: {r.status_code}")
        except Exception as e:
            return ToolResult(tool_name="crypto_market_data", success=False, data=None, error=str(e))

async def execute_crypto_trending(params: dict) -> ToolResult:
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get("https://api.coingecko.com/api/v3/search/trending")
            if r.status_code == 200:
                coins = r.json().get("coins", [])[:5]
                return ToolResult(tool_name="crypto_trending", success=True, data=[c.get("item", {}).get("name") for c in coins])
            return ToolResult(tool_name="crypto_trending", success=False, data=None, error=f"Status: {r.status_code}")
        except Exception as e:
            return ToolResult(tool_name="crypto_trending", success=False, data=None, error=str(e))
