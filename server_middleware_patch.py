import sys

content = """
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse

class ActiveRequestsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        global ACTIVE_REQUESTS
        with REQUEST_LOCK:
            ACTIVE_REQUESTS += 1
            
        try:
            response = await call_next(request)
            if isinstance(response, StreamingResponse):
                original_body = response.body_iterator
                async def wrapped_body():
                    try:
                        async for chunk in original_body:
                            yield chunk
                    finally:
                        global ACTIVE_REQUESTS
                        with REQUEST_LOCK:
                            ACTIVE_REQUESTS -= 1
                response.body_iterator = wrapped_body()
                return response
            else:
                with REQUEST_LOCK:
                    ACTIVE_REQUESTS -= 1
                return response
        except Exception:
            with REQUEST_LOCK:
                ACTIVE_REQUESTS -= 1
            raise

app.add_middleware(ActiveRequestsMiddleware)
"""

with open("/home/kali/Projects/LMMs/lmms/api/server.py", "r") as f:
    text = f.read()

# Replace the previous heart_beat code slightly to insert the middleware
text = text.replace('LAST_PING_TIME = time.time()', content + '\nLAST_PING_TIME = time.time()')

with open("/home/kali/Projects/LMMs/lmms/api/server.py", "w") as f:
    f.write(text)
