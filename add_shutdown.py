import re

with open("lmms/api/server.py", "r") as f:
    code = f.read()

old_code = """@app.post("/v1/internal/ping")
def ping():
    global LAST_PING_TIME
    LAST_PING_TIME = time.time()
    return {"status": "ok"}"""

new_code = """@app.post("/v1/internal/ping")
def ping():
    global LAST_PING_TIME
    LAST_PING_TIME = time.time()
    return {"status": "ok"}

@app.post("/v1/internal/shutdown")
def shutdown():
    import os, signal
    print("[Engine] Immediate shutdown requested by client.")
    os.kill(os.getpid(), signal.SIGTERM)
    return {"status": "shutting down"}"""

code = code.replace(old_code, new_code)
with open("lmms/api/server.py", "w") as f:
    f.write(code)
