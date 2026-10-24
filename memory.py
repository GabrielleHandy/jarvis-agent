import os
import re
import sqlite3

DB_FILE = "jarvis.db"
MEMORY_MD_FILE = "memory.md"


def init_db():
    """Creates the SQLite database tables on your hard drive if they don't exist yet."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ideas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                idea_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def clear_messages():
    """Clears recent chat history from jarvis.db (useful if old refusals poisoned context)."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("DELETE FROM messages")


def save_message(role: str, content: str):
    """Saves a single message ('user' or 'assistant') permanently to jarvis.db."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "INSERT INTO messages (role, content) VALUES (?, ?)",
            (role, content),
        )


def get_recent_messages(limit: int = 8) -> list[dict]:
    """Loads the most recent messages from jarvis.db and formats them for the LLM."""
    with sqlite3.connect(DB_FILE) as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


def save_idea(category: str, idea_text: str):
    """Saves a captured idea or goal into the ideas table."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "INSERT INTO ideas (category, idea_text) VALUES (?, ?)",
            (category.strip(), idea_text.strip()),
        )


def get_all_ideas() -> list[dict]:
    """Returns all saved ideas from newest to oldest."""
    with sqlite3.connect(DB_FILE) as conn:
        rows = conn.execute(
            "SELECT id, category, idea_text, created_at FROM ideas ORDER BY id DESC"
        ).fetchall()
    return [
        {"id": r[0], "category": r[1], "idea_text": r[2], "created_at": r[3]}
        for r in rows
    ]


def load_living_memory() -> str:
    """Reads memory.md from disk so Jarvis always knows your Working Memory & Commands."""
    if not os.path.exists(MEMORY_MD_FILE):
        return ""
    with open(MEMORY_MD_FILE, "r", encoding="utf-8") as f:
        return f.read()


def update_working_memory(key: str, value: str) -> str:
    """Updates a key inside the Working Memory block of memory.md automatically."""
    content = load_living_memory()
    pattern = rf"^({re.escape(key.strip())}:\s*).*$"
    replacement = rf'\1"{value.strip()}"'
    new_content, count = re.subn(pattern, replacement, content, flags=re.MULTILINE)
    if count > 0:
        with open(MEMORY_MD_FILE, "w", encoding="utf-8") as f:
            f.write(new_content)
        return f"✅ Updated Working Memory in memory.md: {key.strip()} = \"{value.strip()}\""
    return f"⚠️ Key '{key.strip()}' not found in memory.md Working Memory."


def add_long_term_observation(observation: str) -> str:
    """Appends a new bullet point under ## Long-Term Observations in memory.md."""
    content = load_living_memory()
    marker = "## Long-Term Observations"
    if marker in content:
        parts = content.split(marker, 1)
        updated = f"{parts[0]}{marker}\n- {observation.strip()}{parts[1]}"
        with open(MEMORY_MD_FILE, "w", encoding="utf-8") as f:
            f.write(updated)
        return f"✅ Added Long-Term Observation to memory.md: {observation.strip()}"
    return "⚠️ Could not find '## Long-Term Observations' section in memory.md."


def remove_long_term_observation(snippet: str) -> str:
    """Removes a bullet line under Long-Term Observations in memory.md matching the snippet."""
    snippet_clean = snippet.strip()
    lines = load_living_memory().splitlines()
    kept_lines = [
        line
        for line in lines
        if not (line.strip().startswith("- ") and snippet_clean.lower() in line.lower())
    ]
    if len(kept_lines) == len(lines):
        return f"⚠️ No observation bullet found matching '{snippet_clean}'."
    with open(MEMORY_MD_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(kept_lines) + "\n")
    return f"🗑️ Pruned observation matching: '{snippet_clean}'"
