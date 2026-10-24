# Jarvis Living Memory

## Working Memory
```yaml
active_project: "Jarvis Local-First Agent"
current_block: "Autonomous Task Execution"
current_blocker: "None"
session_focus: "Local tool execution and memory synchronization"
last_session_date: "2026-10-23"
```

## Long-Term Observations
- Operates in local-first environment with private on-premise model inference.
- Maintains state across sessions through dual-layer persistence (SQLite + structured Markdown).

## Session Close Rule
At the end of any work session, update working memory fields and append observations via `[SET_MEMORY]` and `[ADD_OBSERVATION]` tool calls.
