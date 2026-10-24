import time
import requests

BASE_URL = "http://192.168.0.25:11444/v1"
MODEL_ID = "vm-planner-27b"


def normalize_messages(messages: list[dict]) -> list[dict]:
    """Merges consecutive messages with the same role so strict LLM servers never 503/400."""
    cleaned = []
    for msg in messages:
        if cleaned and cleaned[-1]["role"] == msg["role"]:
            cleaned[-1]["content"] += "\n\n" + msg["content"]
        else:
            cleaned.append({"role": msg["role"], "content": msg["content"]})
    return cleaned


def ask_jarvis(messages: list[dict], model: str = MODEL_ID) -> str:
    """Sends a conversation history list to your local GPU model with auto-retry on 503."""
    payload = {
        "model": model,
        "messages": normalize_messages(messages),
        "temperature": 0.7,
    }

    # Retry up to 3 times if the GPU server returns 503 (busy / reloading model into VRAM)
    for attempt in range(3):
        try:
            response = requests.post(
                f"{BASE_URL}/chat/completions",
                json=payload,
                timeout=90,
            )
            if response.status_code == 503 and attempt < 2:
                time.sleep(2)
                continue
            if not response.ok:
                return f"⚠️ GPU Server Error ({response.status_code}): {response.text}"
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except requests.RequestException as e:
            if attempt < 2:
                time.sleep(2)
                continue
            return f"⚠️ Could not reach GPU server at {BASE_URL}: {e}"
    return "⚠️ GPU server was busy after 3 retries."
