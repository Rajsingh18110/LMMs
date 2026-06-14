import base64
import requests

def analyze_image(image_path: str, prompt: str = "What is in this image?") -> str:
    try:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()

        payload = {
            "model_name": "gemma4",
            "messages": [{"role": "user", "content": prompt, "images": [image_data]}],
            "stream": False
        }
        
        response = requests.post("http://localhost:11435/v1/chat/completions", json=payload, timeout=60)
        if response.status_code == 200:
            return response.json().get("choices", [{}])[0].get("message", {}).get("content", "No content returned.")
        else:
            return f"Engine error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error analyzing image: {str(e)}"
