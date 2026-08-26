import re

with open("lmms/backend/main.py", "r") as f:
    code = f.read()

old_code = """            if cmd in ["exit", "quit", "clear"]:
                if cmd == "clear":
                    console.clear()
                    print_banner()
                    continue
                break"""

new_code = """            if cmd in ["exit", "quit", "clear"]:
                if cmd == "clear":
                    console.clear()
                    print_banner()
                    continue
                try:
                    import requests
                    requests.post("http://127.0.0.1:11435/v1/internal/shutdown", timeout=2)
                except:
                    pass
                break"""

code = code.replace(old_code, new_code)
with open("lmms/backend/main.py", "w") as f:
    f.write(code)
