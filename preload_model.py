import re

with open("lmms/backend/main.py", "r") as f:
    code = f.read()

old_code = """    # ----------------------------------------
    
    while True:"""

new_code = """    # ----------------------------------------
    
    if current_model != "None":
        with console.status(f"[bold blue]{current_model}:[/bold blue] [dim]Loading model...[/dim]", spinner="lmms_wave"):
            try:
                requests.post(f"{ENGINE_URL}/v1/models/load", json={"model_name": current_model}, timeout=120)
            except Exception:
                pass

    while True:"""

code = code.replace(old_code, new_code)
with open("lmms/backend/main.py", "w") as f:
    f.write(code)
