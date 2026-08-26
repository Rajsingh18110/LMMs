import re

with open("lmms/backend/main.py", "r") as f:
    code = f.read()

old_code = """                            first_line = None
                            with console.status(f"[bold blue]{current_model}:[/bold blue] [dim]Waiting for model...[/dim]", spinner="lmms_wave"):
                                resp = requests.post(f"{ENGINE_URL}/v1/chat/completions", json={
                                    "model_name": current_model,
                                    "messages": clean_messages,
                                    "stream": True,
                                    "temperature": req_temp,
                                    "top_p": req_top_p,
                                    "repetition_penalty": 1.15,
                                    "mode": current_mode.strip("/"),
                                    "think": True # Always get the stream to prevent connection hanging, we hide it client-side if needed
                                }, stream=True, timeout=(10, 60))
                                resp.raise_for_status()
                                
                                chunks_iterator = resp.iter_lines()
                                for line in chunks_iterator:
                                    if line:
                                        first_line = line
                                        break"""

new_code = """                            first_line = None
                            import threading
                            import time
                            
                            running_status = True
                            status_start_time = time.time()
                            
                            with console.status(f"[bold blue]{current_model}:[/bold blue] [dim]Waiting for model... (0s)[/dim]", spinner="lmms_wave") as status:
                                def update_status():
                                    while running_status:
                                        elapsed = int(time.time() - status_start_time)
                                        status.update(f"[bold blue]{current_model}:[/bold blue] [dim]Waiting for model... ({elapsed}s)[/dim]")
                                        time.sleep(1)
                                        
                                t_status = threading.Thread(target=update_status, daemon=True)
                                t_status.start()
                                
                                try:
                                    resp = requests.post(f"{ENGINE_URL}/v1/chat/completions", json={
                                        "model_name": current_model,
                                        "messages": clean_messages,
                                        "stream": True,
                                        "temperature": req_temp,
                                        "top_p": req_top_p,
                                        "repetition_penalty": 1.15,
                                        "mode": current_mode.strip("/"),
                                        "think": True
                                    }, stream=True, timeout=(10, 120))
                                    resp.raise_for_status()
                                    
                                    chunks_iterator = resp.iter_lines()
                                    for line in chunks_iterator:
                                        if line:
                                            first_line = line
                                            break
                                finally:
                                    running_status = False
                                    t_status.join(timeout=1.0)"""

code = code.replace(old_code, new_code)
with open("lmms/backend/main.py", "w") as f:
    f.write(code)

