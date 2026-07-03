# Llama-cpp Chat GUI Pro

A Tkinter GUI wrapper around `llama-cli` with multi-session tabs, hardware telemetry, web tools, and autonomous tool-calling.

## Features

- **Multi-session tabs** via `ttk.Notebook` with per-session model config
- **Sidebar controls**: GPU offload (ngl), temperature, top-p, context size, system prompt, theme, presets
- **Token counter** + per-turn speed breakdown + color-coded live speed graph
- **Hardware telemetry**: CPU, RAM, GPU (via `psutil` + `nvidia-smi`)
- **Benchmark CSV export** with toggle button
- **Thinking filter**: hides `[Start/End thinking]` blocks behind a toggle
- **Preset system**: save/load named configs to `~/.config/llama-chat-presets.json`
- **Streaming indicator**: `● Generating` / `○ Idle` in status bar
- **Chat search**: `Ctrl+F` search bar with highlights and prev/next navigation
- **Theme**: Auto-detect GTK dark/light, manual override
- **Right-click menu**: Copy, Clear, Regenerate
- **System tray** integration via `pystray`
- **Web integration**: DuckDuckGo search + URL fetch via 🌐 button or `/search`, `/fetch`, `/web` commands
- **Autonomous tool calling**: 🛠 Tools mode — model can invoke `web_search()` and `fetch_url()` via `[TOOL_CALL]` syntax

## Architecture

| File | Role |
|---|---|
| `llama_gui.py` | Tkinter UI: `SessionTab` (per-tab state), `LlamaChatGUI` (app shell), `ThemeManager` |
| `llama_controller.py` | Subprocess lifecycle, dual queues, timing regexes, profile/preset functions |
| `web_tools.py` | `search_web()` (DuckDuckGo) and `fetch_url()` (requests + BeautifulSoup) wrappers |
| `AGENT_GUIDE.md` | Architecture reference for agent handover |

### Flow

```
User input → LlamaChatGUI.send_message()
  → LlamaController.send() → llama-cli stdin
  → LlamaController._read_stdout() → msg_queue + log_queue
  → LlamaChatGUI.poll_queues() (every 100ms)
    → SessionTab.process_output() → chat_display + log_display
```

### Tool Calling Flow

1. User toggles 🛠 Tools → tool definitions prepended to system prompt, process restarts
2. Model outputs `[TOOL_CALL tool_name(args)]`
3. `process_output()` detects pattern, calls `_handle_tool_call()`
4. Generation stopped via `\x03`, tool executed in background thread
5. Result sent back as `[TOOL_RESULT]\n{result}`, model continues with context

## Files

- `llama_gui.py` (1200 lines) — all UI, SessionTab, and tool-calling logic
- `llama_controller.py` (251 lines) — subprocess management and config persistence
- `web_tools.py` (61 lines) — search and fetch wrappers
- `requirements.txt` — `ddgs`, `requests`, `beautifulsoup4`, `psutil`, `Pillow`, `pystray`
- `AGENT_GUIDE.md` — developer handover notes
- `memory.md` — live project state (current direction, decisions, blockers)
- `history.md` — chronological build log

## Data Storage

| Path | Purpose |
|---|---|
| `~/.config/llama-chat-profiles.json` | Per-model parameter auto-save |
| `~/.config/llama-chat-presets.json` | Named preset configs (save/load) |
| `~/.local/share/llama-chat/benchmarks/` | Benchmark CSV output |
| `~/Documents/ChatArchive/llama_chat_project/history/` | Chat history (Markdown) |

> **Note:** Paths above are Linux/XDG. Windows equivalents are provided by `platform_compat.py` (see `AGENT_GUIDE.md` for the Windows port plan).
