# Project Memory — Llama-cpp Chat GUI Pro

> **Live session state.** This file is the "where are we right now" anchor for the project. Update it whenever the state changes (new direction, new blocker, new decision, milestone hit). Do not append a session log here — that's what `history.md` is for.

---

## Current State

**Status:** Active development · On `main` · Pushed to GitHub

**Repo:** https://github.com/kushalmanshrestha789/llama-chat-gui
**Local path:** `/home/cipher/projects/llama-chat-gui`
**Stack:** Python 3 · Tkinter (UI) · `llama-cli` subprocess (engine) · `pystray` (tray) · `psutil` (telemetry)
**Last commit:** `64b8263` — feat: add platform_compat.py for cross-platform paths and OS detection
**Last tag:** _none_

---

## Active Direction

**Porting to Windows.** The project was built Linux-first. Work in progress is a cross-platform refactor that introduces a `platform_compat.py` helper module and swaps Linux-specific assumptions (XDG paths, `gsettings` dark-mode, `nvidia-smi` path, `subprocess` flags) for portable equivalents.

**Execution order** (see `AGENT_GUIDE.md` and the Windows port plan in chat history for detail):

1. ~~Create `platform_compat.py` with path / theme / GPU helpers~~ ✅ Done in `64b8263`
2. Swap call sites in `llama_controller.py`, `llama_gui.py`, `web_tools.py`
3. Smoke-test on Linux (must not regress)
4. Document Windows install/run in `README.md`
5. Hand off to Windows machine for visual validation

---

## Key Decisions

| Date       | Decision                                                                                                | Why                                                                                  |
|------------|---------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------|
| 2026-07-03 | License = MIT, copyright 2026 kushalmanshrestha789                                                       | Matches snapnote project, keeps personal work consistent                            |
| 2026-07-03 | `memory.md` = live state only; `history.md` = chronological build log                                    | Separates "where are we" from "how did we get here"                                  |
| 2026-07-03 | Git workflow: one commit per feature, Conventional Commits messages                                     | Granular history, easy to revert, easy to read                                       |
| 2026-07-03 | Windows port: introduce `platform_compat.py` rather than scattering `# if sys.platform == "win32"`       | Single source of truth for OS-specific behavior, easier to test                      |

---

## Open Blockers

- **No Windows machine available for testing in this session.** Linux smoke-test must pass before handing off. Document a clear Windows install/run path in `README.md` so the handoff is frictionless.
- **Tk theme rendering on Windows HiDPI is unverified.** May need `ctypes.windll.shcore.SetProcessDpiAwareness(1)`. Flag in `AGENT_GUIDE.md` once known.
- **`nvidia-smi.exe` may not be on PATH on many Windows machines.** Need a "Locate nvidia-smi" setting or graceful degradation (already partially handled by `try/except`).

---

## File Map

| File | Role | Status |
|------|------|--------|
| `llama_gui.py` | Tkinter UI, `SessionTab`, `LlamaChatGUI`, `ThemeManager` | Will be refactored (path/theme helpers) |
| `llama_controller.py` | `LlamaController` subprocess + queue lifecycle | Will be refactored (path constants, `CREATE_NO_WINDOW`) |
| `web_tools.py` | `search_web()` (DuckDuckGo) + `fetch_url()` | Will drop the Linux-only `_SYSTEM_SITE` hack |
| `requirements.txt` | `ddgs`, `requests`, `beautifulsoup4`, `psutil`, `Pillow`, `pystray` | Stable |
| `README.md` | User-facing features + install | Will gain a "Windows" section |
| `AGENT_GUIDE.md` | Developer handover / architecture | Will gain DPI / Windows pitfalls section |
| `LICENSE` | MIT | ✅ Done |
| `.gitignore` | Python + llama.cpp patterns | ✅ Done |
| `memory.md` | This file — live project state | ✅ Now |
| `history.md` | Chronological build log | ✅ Now |
| `platform_compat.py` | cross-platform paths, dark-mode, nvidia-smi, subprocess flags | ✅ Done in `64b8263`, smoke-tested on Linux |
| _(call-site swap)_ | replace hardcoded constants in the 3 source files with helpers | 🔜 Next |

---

## How To Update This File

- **State changes** (new direction, milestone, decision) → edit the relevant section
- **New blockers discovered** → add to "Open Blockers"
- **Blockers resolved** → move them to `history.md` with date and resolution
- **New files added** → add to "File Map"
- Do **not** append a running session log here — that's `history.md`
