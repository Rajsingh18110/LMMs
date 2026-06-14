import os
import json
import threading
import requests

PERSONA_FILE = os.path.expanduser("~/.lmms/persona.json")
ENGINE_URL = "http://localhost:11435"

def _ensure_persona_file():
    if not os.path.exists(PERSONA_FILE):
        os.makedirs(os.path.dirname(PERSONA_FILE), exist_ok=True)
        with open(PERSONA_FILE, "w") as f:
            json.dump([], f)

def get_persona():
    _ensure_persona_file()
    try:
        with open(PERSONA_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_persona_fact(fact):
    facts = get_persona()
    if fact not in facts:
        facts.append(fact)
        with open(PERSONA_FILE, "w") as f:
            json.dump(facts, f, indent=4)

def _extract_task(user_message, model_name):
    prompt = f"""Analyze the following user message. Does it contain any permanent, long-term facts about the user? (For example: their name, their profession, their preferences, their location).
If NO, reply exactly with the word: NONE
If YES, reply with a concise, single-sentence fact. (e.g. "The user's name is Raj.")

User Message: {user_message}"""

    try:
        import time
        time.sleep(3) # Allow foreground stream to start first
        resp = requests.post(f"{ENGINE_URL}/v1/chat/completions", json={
            "model_name": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "temperature": 0.1
        }, timeout=30)
        
        if resp.status_code == 200:
            content = ""
            for line in resp.iter_lines():
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            import json
                            chunk = json.loads(line[6:])
                            content += chunk.get("content", "")
                        except:
                            pass
            
            content = content.strip()
            if content and content.upper() != "NONE" and "NONE" not in content.upper():
                save_persona_fact(content)
    except Exception as e:
        pass # Silently fail background extraction

def auto_extract_persona(user_message, model_name):
    """Spawns a background thread to extract persona facts without blocking the chat."""
    if not model_name or model_name == "None":
        return
        
    t = threading.Thread(target=_extract_task, args=(user_message, model_name), daemon=True)
    t.start()
