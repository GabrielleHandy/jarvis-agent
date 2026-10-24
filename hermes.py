import os
import socket
import time
import zipfile
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
from brain import ask_jarvis
from memory import (
    init_db,
    clear_messages,
    save_message,
    get_recent_messages,
    get_all_ideas,
    load_living_memory,
)
from skills import run_skills

init_db()

BUNDLE_FILES = [
    "brain.py",
    "memory.py",
    "skills.py",
    "hermes.py",
    "chat.html",
    "memory.md",
]
ZIP_NAME = "jarvis-agent.zip"

# Live telemetry state so your phone/browser can see what Jarvis is doing in real time
AGENT_STATUS = {
    "busy": False,
    "stage": "🟢 Idle — Ready",
    "started_at": 0.0,
}


def set_status(stage: str, busy: bool = True):
    """Updates live telemetry for the UI and prints a timestamped log in the SSH terminal."""
    if busy and not AGENT_STATUS["busy"]:
        AGENT_STATUS["started_at"] = time.time()
    AGENT_STATUS["busy"] = busy
    AGENT_STATUS["stage"] = stage
    elapsed = round(time.time() - AGENT_STATUS["started_at"], 1) if AGENT_STATUS["started_at"] else 0.0
    print(f"[{elapsed:4.1f}s] ⚡ {stage}", flush=True)


def get_local_ip() -> str:
    """Finds this machine's local Wi-Fi/LAN IP address."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.168.0.25", 11444))
            return s.getsockname()[0]
    except Exception:
        return "192.168.0.25"


def build_zip_bundle() -> str:
    """Packages all Jarvis agent files into jarvis-agent.zip for easy SSH/desktop deployment."""
    with zipfile.ZipFile(ZIP_NAME, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in BUNDLE_FILES:
            if os.path.exists(fname):
                zf.write(fname)
    return os.path.abspath(ZIP_NAME)


build_zip_bundle()

app = FastAPI(title="Hermes - My Personal Jarvis API")


@app.get("/")
def serve_chat_ui():
    """Serves your live Jarvis Chat + Obsidian Memory console at http://localhost:8000/"""
    return FileResponse("chat.html")


@app.get("/status")
def get_agent_status():
    """Returns live telemetry so the chat UI shows exactly what step Jarvis is on."""
    elapsed = (
        round(time.time() - AGENT_STATUS["started_at"], 1)
        if AGENT_STATUS["busy"] and AGENT_STATUS["started_at"]
        else 0.0
    )
    return {
        "busy": AGENT_STATUS["busy"],
        "stage": AGENT_STATUS["stage"],
        "elapsed_seconds": elapsed,
    }


@app.get("/network")
def get_network_info():
    """Returns the LAN URLs for generating phone QR codes."""
    ip = get_local_ip()
    return {
        "current_url": f"http://{ip}:8000",
        "desktop_url": "http://192.168.0.25:8000",
        "zip_path": os.path.abspath(ZIP_NAME),
    }


@app.get("/download-zip")
def download_zip():
    """Rebuilds and downloads jarvis-agent.zip."""
    build_zip_bundle()
    return FileResponse(ZIP_NAME, filename=ZIP_NAME, media_type="application/zip")


TOOL_INSTRUCTIONS = (
    "CRITICAL HOST OVERRIDE (DO NOT IGNORE):\n"
    "You are connected to a Python host (hermes.py + skills.py) that executes bracket tags on the user's computer.\n"
    "NEVER say 'I cannot access local files' or 'I do not have that file'. Instead, output the bracket tag!\n"
    "When you need a tool, output ONLY the bracket tag on your first turn:\n"
    "- [READ_FILE: filename] -> Reads any file in the project folder (e.g. [READ_FILE: brain.py], [READ_FILE: memory.md])\n"
    "- [WRITE_FILE: filename.md | content] -> Creates or overwrites a .md or .txt note file\n"
    "- [SET_MEMORY: key | value] -> Updates a Working Memory field in memory.md (e.g. [SET_MEMORY: current_blocker | None])\n"
    "- [ADD_OBSERVATION: text] -> Adds a new bullet to Long-Term Observations in memory.md\n"
    "- [REMOVE_OBSERVATION: snippet] -> Deletes a bullet matching snippet in memory.md (ONLY call after user approves a prune!)\n"
    "- [SAVE_IDEA: Category | Summary] -> Saves an idea to jarvis.db\n"
    "- [READ_IDEAS] -> Lists all saved ideas from jarvis.db"
)


def build_system_prompt() -> dict:
    """Dynamically reads memory.md from disk on every turn so Jarvis always has your latest Working Memory."""
    living_memory = load_living_memory()
    return {
        "role": "system",
        "content": (
            "You are Jarvis, my personal AI agent built from scratch. Be direct, sharp, and concise.\n\n"
            f"=== LIVING MEMORY (FROM memory.md) ===\n{living_memory}\n\n"
            f"=== {TOOL_INSTRUCTIONS} ==="
        ),
    }


class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
def chat_with_jarvis(req: ChatRequest):
    t0 = time.time()
    if req.message.strip().lower() == "/clear":
        clear_messages()
        return {
            "reply": "🧹 Cleared short-term chat history in jarvis.db! (memory.md and saved ideas are untouched).",
            "tool_steps": [],
            "elapsed_seconds": 0.1,
        }

    try:
        set_status("📥 Loading memory.md & recent chat context...", busy=True)
        save_message("user", req.message)

        recent = get_recent_messages(limit=8)
        recent[-1]["content"] += (
            "\n\n[SYSTEM NOTE: If this request involves reading a file, checking/saving ideas, or updating memory.md, "
            "do NOT refuse—output the exact tool tag like [READ_FILE: brain.py] or [SET_MEMORY: key | value] first!]"
        )

        history = [build_system_prompt()] + recent

        # MULTI-STEP REACT LOOP (Max 3 tool steps)
        tool_logs = []
        for step in range(3):
            set_status(
                f"🧠 Pass {step + 1}: vm-planner-27b is thinking ({len(history)} msgs in context)...",
                busy=True,
            )
            reply = ask_jarvis(history)

            set_status(f"🔍 Pass {step + 1}: Checking reply for tool calls...", busy=True)
            tool_observation = run_skills(reply)

            if not tool_observation:
                break

            first_line = tool_observation.splitlines()[0][:60]
            set_status(f"🛠️ Step {step + 1} Tool Executed: {first_line}...", busy=True)
            tool_logs.append(f"Step {step + 1}: {tool_observation}")
            history.append({"role": "assistant", "content": reply})
            history.append(
                {
                    "role": "user",
                    "content": (
                        f"TOOL OBSERVATION:\n{tool_observation}\n\n"
                        "Now answer the user's original request using this real data (or call another tool if needed)."
                    ),
                }
            )

        set_status("💾 Saving reply to jarvis.db...", busy=True)
        save_message("assistant", reply)
        total_time = round(time.time() - t0, 1)
        set_status(f"✅ Done in {total_time}s", busy=False)

        return {
            "reply": reply,
            "tool_steps": tool_logs,
            "context_window_size": len(history),
            "elapsed_seconds": total_time,
        }
    except Exception as e:
        set_status(f"⚠️ Error: {e}", busy=False)
        raise


@app.get("/ideas")
def list_ideas():
    """Returns all captured ideas for the Visual Dashboard."""
    return {"ideas": get_all_ideas()}


@app.get("/memory")
def view_living_memory():
    """Returns the current contents of memory.md."""
    return {"memory_md": load_living_memory()}


if __name__ == "__main__":
    local_ip = get_local_ip()
    print(f"\n📦 Built zip bundle: {os.path.abspath(ZIP_NAME)}")
    print(f"📱 OPEN THIS URL ON YOUR PHONE (Same Wi-Fi): http://{local_ip}:8000\n")
    uvicorn.run("hermes:app", host="0.0.0.0", port=8000, reload=True)
