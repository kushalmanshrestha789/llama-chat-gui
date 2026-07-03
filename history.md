# Project History — Llama-cpp Chat GUI Pro

> **Chronological build log.** Reverse-chronological (newest first). This is the "how did we get here" file. For current state and decisions, see `memory.md`. For architecture, see `AGENT_GUIDE.md`.

---

## 2026-07-03 — GitHub release + cross-platform prep

**Commits:**
- `36aec70` — Add MIT license and Python .gitignore
- (this commit introduces `memory.md` and `history.md`)

**Highlights:**
- Project uploaded to GitHub: https://github.com/kushalmanshrestha789/llama-chat-gui
- Added MIT LICENSE (matches the snapnote project for consistency)
- Added `.gitignore` (Python + llama.cpp — excludes `__pycache__`, venvs, `*.gguf`, etc.)
- Created `memory.md` (live project state) and `history.md` (this file)
- Established git workflow: one commit per feature, Conventional Commits messages
- Decided to port the project to Windows; execution order is in `memory.md`
- Removed the "Session History" section from `README.md` (it now lives here)

---

## 2026-06-22 — Initial build session

> The entire project was built in one AI-coding-assistant session on 2026-06-22. Chronological build order, preserved verbatim from the original `README.md`:

1. Initial `LlamaController` + `SessionTab` + `LlamaChatGUI` separation with queue/reader-thread pattern
2. Temperature, top-p sliders, system prompt editor, dynamic ctx_size
3. Multi-session tabs via `SessionTab` + `ttk.Notebook`
4. Stop generation button (`\x03` to stdin)
5. Token counter / speed history graph / color-coded speed indicator
6. Per-turn performance breakdown in sidebar
7. Hardware telemetry (CPU, RAM, GPU via `psutil` + `nvidia-smi`)
8. Benchmark CSV export with toggle
9. Sample speed breakdown (regex in controller)
10. Thinking filter: `[Start thinking]` / `[End thinking]` hidden by toggle
11. Preset system: save/load named configs
12. Streaming indicator
13. Chat search: `Ctrl+F` with highlights and navigation
14. Manual theme override: Auto / Light / Dark
15. Right-click menu on chat
16. Web search/fetch integration: `web_tools.py` module, `/web` `/search` `/fetch` commands, 🌐 Web button
17. Tool calling: model autonomously invokes tools via `[TOOL_CALL]` syntax using `[TOOL_RESULT]` feedback

**Initial commit:** `f33b04e` — Initial commit: Llama-cpp Chat GUI Pro

---

## How To Update This File

- New commit / milestone / direction change → add a new dated section **at the top** (reverse-chronological)
- Keep entries short and scannable — bullet points, not prose
- For very large milestones, link to a separate doc or `AGENT_GUIDE.md` section rather than dumping detail here
- This file is committed to git; the diff history is the audit trail
