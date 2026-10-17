import os
import json
import random
import string
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

router = APIRouter(tags=["dashboard"])

# Global Security State
server_otp: str = ""
server_api_key: str = ""
server_temp_token: str = ""
active_agent_name: str = "No Model Loaded"


def initialize_security_credentials() -> Dict[str, str]:
    """Generates server OTP and Master API key."""
    global server_otp, server_api_key
    server_otp = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    server_api_key = "lmms-sk-" + ''.join(random.choices(string.ascii_letters + string.digits, k=48))
    return {"otp": server_otp, "api_key": server_api_key}


class UnlockRequest(BaseModel):
    otp: str


@router.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>LMMs Engine Dashboard</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
        <style>
            body { 
                font-family: 'Inter', sans-serif; 
                background: radial-gradient(circle at 10% 20%, rgb(14, 14, 25) 0%, rgb(0, 0, 0) 90%);
                color: #ffffff; 
                display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; 
                overflow: hidden;
            }
            .glow {
                position: absolute;
                width: 600px; height: 600px;
                background: radial-gradient(circle, rgba(59,130,246,0.15) 0%, rgba(0,0,0,0) 70%);
                top: -200px; left: -200px;
                border-radius: 50%;
                z-index: -1;
            }
            .card { 
                background: rgba(20, 20, 30, 0.5); 
                backdrop-filter: blur(20px);
                border: 1px solid rgba(255, 255, 255, 0.08); 
                border-radius: 16px; 
                padding: 40px; width: 450px; 
                box-shadow: 0 8px 32px rgba(0,0,0,0.8), inset 0 0 15px rgba(255,255,255,0.02); 
            }
            h2 { 
                margin-top: 0; 
                background: linear-gradient(90deg, #4ade80, #3b82f6);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                font-weight: 800;
                font-size: 28px;
                margin-bottom: 25px;
            }
            .form-group { margin-bottom: 25px; }
            label { display: block; font-size: 13px; margin-bottom: 10px; color: #a1a1aa; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;}
            input[type="text"] { 
                width: 100%; padding: 12px 15px; 
                background-color: rgba(0, 0, 0, 0.5); 
                border: 1px solid rgba(255, 255, 255, 0.1); 
                border-radius: 8px; color: #fff; font-size: 16px; box-sizing: border-box; 
                transition: all 0.3s ease;
            }
            input[type="text"]:focus {
                border-color: #3b82f6;
                box-shadow: 0 0 12px rgba(59, 130, 246, 0.4);
                outline: none;
            }
            button { 
                width: 100%; padding: 14px; 
                background: linear-gradient(45deg, #3b82f6, #8b5cf6); 
                color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: 600;
                cursor: pointer; transition: all 0.3s ease; 
                box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3);
            }
            button:hover { 
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(139, 92, 246, 0.5);
            }
            .hidden { display: none !important; }
            canvas { 
                background-color: rgba(0,0,0,0.6); 
                border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); 
                margin-bottom: 15px; padding: 10px; cursor: crosshair; 
                box-shadow: inset 0 2px 10px rgba(0,0,0,0.5);
            }
            .copy-btn { 
                width: auto; padding: 6px 12px; font-size: 12px; 
                background: rgba(255,255,255,0.1); color: #fff; 
                border-radius: 6px; margin-bottom: 25px; 
                box-shadow: none; border: 1px solid rgba(255,255,255,0.1);
            }
            .copy-btn:hover {
                background: rgba(255,255,255,0.2);
                transform: translateY(0);
                box-shadow: none;
            }
            .agent-name { 
                color: #facc15; font-weight: 600; margin-bottom: 25px; 
                padding: 10px; background: rgba(250, 204, 21, 0.1); 
                border-radius: 8px; border: 1px solid rgba(250, 204, 21, 0.2);
                display: inline-block;
            }
            #error-msg { color: #f87171; font-size: 14px; margin-top: 15px; text-align: center; }
        </style>
    </head>
    <body>
        <div class="glow"></div>
        <div class="card" id="login-card">
            <h2>System Authentication</h2>
            <div class="form-group">
                <label for="otp">Terminal OTP</label>
                <input type="text" id="otp" placeholder="Enter 6-character code" autocomplete="off">
            </div>
            <button onclick="unlock()">Unlock Engine Dashboard</button>
            <div id="error-msg"></div>
        </div>

        <div class="card hidden" id="keys-card">
            <h2>LMMs Credentials</h2>
            <div class="agent-name" id="display-agent">System Offline</div>
            
            <label>Master API Key (Encrypted View)</label>
            <canvas id="canvas-api-key" width="370" height="40"></canvas>
            <button class="copy-btn" onclick="copyKey('api_key')">Copy API Key</button>
            
            <label>Universal Webhook URL</label>
            <canvas id="canvas-webhook" width="370" height="40"></canvas>
            <button class="copy-btn" onclick="copyKey('webhook_url')">Copy Webhook</button>
        </div>

        <script>
            let authToken = "";
            let secureCache = {};

            async function unlock() {
                const otp = document.getElementById("otp").value;
                const res = await fetch("/v1/auth/unlock", {
                    method: "POST", headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ otp })
                });
                if (!res.ok) {
                    document.getElementById("error-msg").innerText = "Invalid OTP. Check your terminal.";
                    return;
                }
                const data = await res.json();
                authToken = data.token;
                
                const keysRes = await fetch("/v1/auth/keys", {
                    headers: { "Authorization": "Bearer " + authToken }
                });
                const keys = await keysRes.json();
                secureCache = keys;
                
                document.getElementById("login-card").classList.add("hidden");
                document.getElementById("keys-card").classList.remove("hidden");
                
                document.getElementById("display-agent").innerText = "Active Model: " + keys.agent_name;
                
                drawToCanvas("canvas-api-key", keys.api_key);
                drawToCanvas("canvas-webhook", keys.webhook_url);
            }

            function drawToCanvas(canvasId, text) {
                const canvas = document.getElementById(canvasId);
                const ctx = canvas.getContext("2d");
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.fillStyle = "#4ade80";
                ctx.font = "15px Consolas, monospace";
                ctx.fillText(text, 10, 25);
            }

            function copyKey(keyType) {
                if (secureCache[keyType]) {
                    navigator.clipboard.writeText(secureCache[keyType])
                        .then(() => alert("Copied securely!"))
                        .catch(err => alert("Copy failed: " + err));
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.post("/v1/auth/unlock")
async def unlock_dashboard(req: UnlockRequest):
    global server_otp, server_temp_token
    if req.otp == server_otp:
        server_temp_token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        return {"token": server_temp_token}
    raise HTTPException(status_code=401, detail="Invalid OTP")


@router.get("/v1/auth/keys")
async def get_keys(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer ") or auth_header.split(" ")[1] != server_temp_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    global active_agent_name, server_api_key
    try:
        active_f = os.path.expanduser("~/.lmms/logs/active_models.json")
        if os.path.exists(active_f):
            with open(active_f, "r") as f:
                d = json.load(f)
            if d:
                active_agent_name = list(d.keys())[0]
    except Exception:
        pass

    return {
        "api_key": server_api_key,
        "webhook_url": "http://localhost:11435/webhook",
        "agent_name": active_agent_name
    }
