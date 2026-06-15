import httpx
import json
from typing import AsyncGenerator

class LMMsClient:
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=120.0)

    async def get_models(self):
        resp = await self.client.get(f"{self.base_url}/models")
        return resp.json()

    async def get_history(self):
        resp = await self.client.get(f"{self.base_url}/history")
        return resp.json()

    async def create_session(self, title: str, mode: str, model: str):
        resp = await self.client.post(f"{self.base_url}/history/new", json={
            "title": title, "mode": mode, "model": model
        })
        return resp.json()

    async def get_system_status(self):
        resp = await self.client.get(f"{self.base_url}/system/status")
        return resp.json()

    async def stream_chat(self, message: str, mode: str = "fast", model: str = "qwen3:8b", session_id: str = None) -> AsyncGenerator[str, None]:
        async with self.client.stream("POST", f"{self.base_url}/chat/stream", json={
            "message": message,
            "mode": mode,
            "model": model,
            "session_id": session_id,
            "stream": True
        }) as response:
            async for chunk in response.aiter_text():
                if chunk:
                    yield chunk

    async def close(self):
        await self.client.aclose()
