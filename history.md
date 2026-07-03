# Project History — Llama-cpp Chat GUI Pro

> **Chronological build log.** Reverse-chronological (newest first). This is the "how did we get here" file. For current state and decisions, see `memory.md`. For architecture, see `AGENT_GUIDE.md`.

---

## 2026-07-03 — Tag: v0.2.0 — "Cross-platform support"

- Created annotated tag `v0.2.0` pointing at `b03bc92`
- Pushed to `origin` via SSH (no `gh` involvement, so the [[github-account-split]] doesn't block the tag itself)
- Tag message includes: highlights, commits-since-v0.1.0 list, known follow-ups
- GitHub **Release** page not created — that step needs `gh release create`, which is on the wrong account. The tag is in place; creating the Release is a follow-up that requires `gh auth login` as `kushalmanshrestha789` first.

## 2026-07-03 — Validation follow-up: fix ddgs + save baseline report

**Commits:**

- `666ecfc` — fix: prefer duckduckgo_search over ddgs in web search fallback
- `572b413` — docs: save 2026-07-03 Linux validation report, add example filename to prompt

**Why this happened:** the validation run on commit `8efbbb1` (in the previous entry) reported `PARTIAL_PASS` because the `ddgs` package's `primp` wheel download timed out on the headless container, which cascaded into `pystray` not being installed either. Two of the three recommendations from that report were addressed:

1. **`666ecfc`** — Reordered the `web_tools.py` import chain to try `duckduckgo_search` (the original, stable package, no Rust-based `primp` dependency) first, with `ddgs` as a fallback. Rewrote the missing-package error message to mention both options with both install commands. Updated `requirements.txt` to list `duckduckgo_search` as the primary dependency. Tested in a venv against all three scenarios (both / only-`ddgs` / neither) — all work.

2. **`572b413`** — Saved the full validation report to `docs/validation/2026-07-03-linux-partial-pass.md` (107 lines, with action items and a cross-link to the fix in `666ecfc`). Also added a concrete filename example to `AI_VALIDATION_PROMPT.md` so future validators follow the naming convention.

**Skipped:** the third recommendation (adding `pip install --no-deps ddgs` to the README) was reconsidered and dropped — that advice would confuse more users than it would help; the real fix is the dependency change in `666ecfc`.

## 2026-07-03 — AI validation prompt

**Commit:** `b40e54b` — docs: add AI_VALIDATION_PROMPT.md and link from README

- New `AI_VALIDATION_PROMPT.md` — a self-contained prompt any capable AI can run to clone, install, and test the repo, then return a structured pass/fail report
- Enforces a fixed Markdown report shape with a derived verdict (PASS / PARTIAL_PASS / FAIL / SKIPPED) so verification is consistent across runs
- Documented when to re-run (after `feat:` / `refactor:` commits, before release tags) and when not to (docs-only / chore-only)
- README gains a one-paragraph "Validation" section linking to the new file

## 2026-07-03 — README: Windows install + run section

**Commit:** `5a56196` — docs: add Windows install + run section, fix stale GTK/note language

- Rewrote the placeholder "see AGENT_GUIDE.md for the Windows port plan" note as a real cross-platform install guide
- Tightened stale wording ("Auto-detect GTK dark/light" → "Auto-detect system dark/light (gsettings on Linux, registry on Windows)")
- Added `platform_compat.py` to the Architecture and Files tables
- Rewrote the Data Storage section as a platform-aware table (Linux/XDG ↔ Windows)
- New sections: Installation (prereq + common + Linux + Windows + notes + PyInstaller), Environment overrides (`LLAMA_CHAT_MODELS_DIR`), Development
- **Unblocks the Windows handoff** — a user with no prior knowledge of the project can install and run on either OS from the README

## 2026-07-03 — Refactor: route all OS code through `platform_compat`

**Commit:** `c01df2f` — refactor: route all OS-specific code through platform_compat

- `llama_controller.py` — `PROFILES_PATH` / `PRESETS_PATH` now resolve via `config_dir()`; `Popen` splats `**subprocess_no_window_kwargs()`
- `llama_gui.py` — `HISTORY_DIR` / `BENCHMARK_DIR` via helpers; `_detect_dark_mode()` delegates to `is_dark_mode()`; `_populate_models()` uses `pathlib.rglob`; `nvidia-smi` uses `nvidia_smi_cmd()`
- `web_tools.py` — dropped the `_SYSTEM_SITE` Linux-only `sys.path` hack

**Bug caught by smoke test (and fixed in the same commit):**
- Initial `models_root()` was `~/.lmstudio/`, which made `rglob` surface the embedding model at `.internal/bundled-models/.../nomic-embed-text-v1.5.Q4_K_M.gguf` — not a chat model. Fixed to `~/.lmstudio/models`, plus added a `LLAMA_CHAT_MODELS_DIR` env-var override.
- Smoke test now asserts the new and old model lists are byte-identical AND the embedding model is never included.

**Smoke-tested on Linux:** all path constants resolve to the same strings the old code used, model list matches (4 entries), dark-mode detection still works, all .py files compile.

## 2026-07-03 — `platform_compat.py` lands (Windows port step 1)

**Commit:** `64b8263` — feat: add platform_compat.py for cross-platform paths and OS detection

- New module, 240 lines, no Tkinter imports
- Centralises: `config_dir`, `data_dir`, `documents_dir`, `models_root`, `history_dir`, `benchmark_dir`, `nvidia_smi_cmd`, `subprocess_no_window_kwargs`, `is_dark_mode`
- Smoke-tested on Linux: every helper returns the same path as the existing hardcoded constants → no regression
- `is_dark_mode()` returned `True` on the current Linux system (gsettings reports `prefer-dark`)

## 2026-07-03 — GitHub release + cross-platform prep

**Commits:**
- `36aec70` — Add MIT license and Python .gitignore
- `b6a5a23` — chore: add memory.md and history.md for project state tracking

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
