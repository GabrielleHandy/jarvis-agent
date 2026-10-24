import os
import re
from memory import (
    save_idea,
    get_all_ideas,
    update_working_memory,
    add_long_term_observation,
    remove_long_term_observation,
)


def run_skills(ai_reply: str) -> str:
    """
    Scans Jarvis's reply for tool tags, executes them in Python,
    and returns a combined observation string for the ReAct loop.
    """
    observations = []

    # Tool 1: [SET_MEMORY: key | value] -> Auto-updates Working Memory in memory.md
    for key, value in re.findall(r"\[SET_MEMORY:\s*(.*?)\s*\|\s*(.*?)\s*\]", ai_reply):
        observations.append(update_working_memory(key, value))

    # Tool 2: [ADD_OBSERVATION: text] -> Appends to Long-Term Observations in memory.md
    for obs_text in re.findall(r"\[ADD_OBSERVATION:\s*(.*?)\s*\]", ai_reply):
        observations.append(add_long_term_observation(obs_text))

    # Tool 3: [REMOVE_OBSERVATION: snippet] -> Prunes matching bullet from memory.md
    for snippet in re.findall(r"\[REMOVE_OBSERVATION:\s*(.*?)\s*\]", ai_reply):
        observations.append(remove_long_term_observation(snippet))

    # Tool 4: [SAVE_IDEA: Category | Idea]
    for category, idea_text in re.findall(r"\[SAVE_IDEA:\s*(.*?)\s*\|\s*(.*?)\s*\]", ai_reply):
        save_idea(category, idea_text)
        observations.append(f"✅ Saved idea under '{category.strip()}': {idea_text.strip()}")

    # Tool 5: [READ_IDEAS]
    if "[READ_IDEAS]" in ai_reply:
        ideas = get_all_ideas()
        if not ideas:
            observations.append("📂 Saved Ideas Database is currently empty.")
        else:
            formatted = "\n".join(
                f"- [{i['category']}] {i['idea_text']} (saved {i['created_at']})"
                for i in ideas
            )
            observations.append(f"📂 Current Saved Ideas in Database:\n{formatted}")

    # Tool 6: [READ_FILE: filename]
    for filename in re.findall(r"\[READ_FILE:\s*(.*?)\s*\]", ai_reply):
        safe_name = os.path.basename(filename.strip())
        if os.path.exists(safe_name):
            with open(safe_name, "r", encoding="utf-8") as f:
                content = f.read(4000)
            observations.append(f"📄 Contents of {safe_name}:\n{content}")
        else:
            observations.append(f"⚠️ File '{safe_name}' not found in workspace.")

    # Tool 7: [WRITE_FILE: filename.md | content] (Sandboxed to .md and .txt files)
    for filename, content in re.findall(r"\[WRITE_FILE:\s*(.*?)\s*\|\s*([\s\S]*?)\s*\]", ai_reply):
        safe_name = os.path.basename(filename.strip())
        if not safe_name.endswith((".md", ".txt")):
            observations.append(
                f"⛔ Guardrail blocked writing '{safe_name}': Only .md and .txt files are allowed."
            )
        else:
            with open(safe_name, "w", encoding="utf-8") as f:
                f.write(content)
            observations.append(f"📝 Wrote file '{safe_name}' ({len(content)} chars).")

    return "\n\n".join(observations)
