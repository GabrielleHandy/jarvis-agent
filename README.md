# Jarvis: A Small, Transparent AI Agent Built from Scratch

Jarvis is a personal AI assistant built in Python to explore how AI agents actually work under the hood—without relying on heavy frameworks like LangChain.

It connects to a local open-source model running on my home network, executes real actions (like reading and writing files), and maintains memory across restarts.

---

## Why I Built This

Most AI agent tutorials tell you to install huge libraries that hide everything behind layers of abstractions. When something breaks, it's almost impossible to tell if the prompt was bad, the model failed, or the library glitched.

I wanted to understand every single step:
1. How does an agent decide to use a tool?
2. How do you pass the tool result back into the prompt?
3. How do you stop a local model from crashing when its VRAM is busy?

Building it from scratch with small, modular Python files made every part explainable and debuggable.

---

## How It Works

1. **The Brain (`brain.py`):** Sends chat history to a local LLM (`vm-planner-27b`) over a local network. It cleans up message formatting and includes an automatic retry loop if the local GPU server is busy loading into memory.
2. **The Skills (`skills.py`):** When the AI outputs a tag like `[READ_FILE: notes.txt]` or `[SAVE_IDEA: App | New concept]`, Python detects the command, runs the action safely, and feeds the result back to the AI.
3. **The Memory (`memory.py`):** 
   - A local **SQLite database** saves every message with timestamps.
   - A readable **`memory.md` file** acts as the agent's scratchpad for active project goals and long-term notes.
4. **The Interface (`hermes.py` + `chat.html`):** A lightweight FastAPI server that lets me talk to Jarvis through a clean web UI from my phone or laptop on the local Wi-Fi.

---

## Practical Problems I Solved

- **The GPU 503 Busy Bug:** When switching models or sending rapid queries, the local server would return a `503 Service Unavailable`. I added a 3-try retry loop with a 2-second delay so tasks don't crash midway.
- **Message Role Errors:** The local API rejected requests if two `user` messages were sent consecutively. I wrote a small function to merge consecutive same-role messages before sending the payload.
- **File Safety:** Restricted file tools so the AI can only read and write files inside the project folder rather than accidentally wandering across the computer.

---

## Tech Stack

- **Python 3** (FastAPI, Requests, SQLite3, Pydantic)
- **Local LLM** (OpenAI-compatible server)
- **Frontend** (HTML/CSS/JavaScript)

---

## Quickstart

### 1. Install Dependencies
```bash
git clone https://github.com/<your-username>/jarvis-agent.git
cd jarvis-agent
pip install -r requirements.txt
```

### 2. Configure Model Endpoint
In `brain.py`, set your local or remote OpenAI-compatible server address:
```python
BASE_URL = "http://localhost:11444/v1"
MODEL_ID = "vm-planner-27b"
```

### 3. Run
```bash
python hermes.py
```
Open `http://localhost:8000` in your browser.
