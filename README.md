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
- **Theme**: Auto-detect system dark/light (gsettings on Linux, registry on Windows), manual override
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
| `platform_compat.py` | Cross-platform paths, dark-mode detection, nvidia-smi lookup, subprocess flags |
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

- `llama_gui.py` — all UI, SessionTab, and tool-calling logic
- `llama_controller.py` — subprocess management and config persistence
- `web_tools.py` — search and fetch wrappers
- `platform_compat.py` — single source of truth for OS-specific paths and commands
- `requirements.txt` — `ddgs`, `requests`, `beautifulsoup4`, `psutil`, `Pillow`, `pystray`
- `AGENT_GUIDE.md` — developer handover notes
- `memory.md` — live project state (current direction, decisions, blockers)
- `history.md` — chronological build log

## Data Storage

The app uses platform-appropriate locations via `platform_compat.py`:

| Path (Linux / XDG) | Windows equivalent | Purpose |
|---|---|---|
| `~/.config/llama-chat-profiles.json` | `%APPDATA%\llama-chat\llama-chat-profiles.json` | Per-model parameter auto-save |
| `~/.config/llama-chat-presets.json` | `%APPDATA%\llama-chat\llama-chat-presets.json` | Named preset configs (save/load) |
| `~/.local/share/llama-chat/benchmarks/` | `%LOCALAPPDATA%\llama-chat\benchmarks\` | Benchmark CSV output |
| `~/Documents/ChatArchive/llama_chat_project/history/` | `%USERPROFILE%\Documents\ChatArchive\llama_chat_project\history\` | Chat history (Markdown) |

Windows paths are resolved through the Win32 Known Folders API where appropriate, so a OneDrive-redirected `Documents` folder is honoured automatically.

## Installation

### Prerequisites (all platforms)

- **Python 3.10+** with `pip` and `tkinter` (the `tkinter` package is bundled with the python.org installer; on Linux install `python3-tk` via your package manager)
- **`llama-cli` binary** on your `PATH` — get it from <https://github.com/ggerganov/llama.cpp/releases> (Windows builds are named `llama-<version>-bin-win-cuda-cu12.2-x64.zip` or similar; extract and put the folder on `PATH`)

### Common steps

```bash
git clone https://github.com/kushalmanshrestha789/llama-chat-gui.git
cd llama-chat-gui
python -m pip install -r requirements.txt
```

### Linux

```bash
python llama_gui.py
```

If your distro separates Tk (e.g. Ubuntu), install it first: `sudo apt install python3-tk`.

### Windows

```powershell
pythonw llama_gui.py
```

> Use `pythonw` (not `python`) — it's the GUI launcher that suppresses the console window. After the first run the app will appear in the system tray.

#### Windows-specific notes

- **NVIDIA GPU telemetry.** The app uses `nvidia-smi` to read GPU utilisation. On Windows it's usually at `C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe`; the app checks that location and `C:\Windows\System32\` automatically. If yours is elsewhere, add the folder to `PATH`. If you have no NVIDIA GPU, the GPU line is silently omitted (no error).
- **HiDPI displays.** Tk on Windows 10/11 scales reasonably well by default. If text looks tiny on a 4K monitor, right-click `pythonw.exe` → Properties → Compatibility → Change high DPI settings → "Override high DPI scaling: System (Enhanced)".
- **OneDrive Documents redirect.** Resolved automatically via the Known Folders API — no action needed.
- **Antivirus false positives.** Some antivirus products flag `pystray` builds that touch the tray icon. Add an exclusion for the project folder if launch is blocked.
- **Firewall prompt on first run.** The app's web tools (`/fetch` command, 🌐 button) make outbound HTTPS requests; the firewall will ask once.

#### Optional: build a single `.exe`

```powershell
python -m pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name llama-chat-gui llama_gui.py
```

Output appears in `dist\llama-chat-gui.exe`. Copy it anywhere; it's standalone.

## Environment overrides

| Variable | Effect |
|---|---|
| `LLAMA_CHAT_MODELS_DIR` | Override the model discovery root. Default is `~/.lmstudio/models`. Set this if your models live somewhere else. |

## Development

See [`AGENT_GUIDE.md`](AGENT_GUIDE.md) for architecture notes, common pitfalls, and how to add new `llama-cli` flags. For current project state see [`memory.md`](memory.md); for the build log see [`history.md`](history.md).

## Validation

[`AI_VALIDATION_PROMPT.md`](AI_VALIDATION_PROMPT.md) is a self-contained prompt you can paste into any capable AI assistant to have it clone, install, and test this repo on a target machine, then return a structured pass/fail report. Re-run it after every `feat:` or `refactor:` commit, and before any release tag.
