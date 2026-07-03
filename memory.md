# Project Memory — Llama-cpp Chat GUI Pro

> **Live session state.** This file is the "where are we right now" anchor for the project. Update it whenever the state changes (new direction, new blocker, new decision, milestone hit). Do not append a session log here — that's what `history.md` is for.

---

## Current State

**Status:** Active development · On `main` · Pushed to GitHub

**Repo:** https://github.com/kushalmanshrestha789/llama-chat-gui
**Local path:** `/home/cipher/projects/llama-chat-gui`
**Stack:** Python 3 · Tkinter (UI) · `llama-cli` subprocess (engine) · `pystray` (tray) · `psutil` (telemetry)
**Last commit:** `b03bc92` — docs: update memory.md and history.md for fix #1 and validation report
**Last tag:** `v0.2.0` — "Cross-platform support" (annotated, on `origin`)

---

## Active Direction

**Porting to Windows.** The project was built Linux-first. Work in progress is a cross-platform refactor that introduces a `platform_compat.py` helper module and swaps Linux-specific assumptions (XDG paths, `gsettings` dark-mode, `nvidia-smi` path, `subprocess` flags) for portable equivalents.

**Execution order** (see `AGENT_GUIDE.md` and the Windows port plan in chat history for detail):

1. ~~Create `platform_compat.py` with path / theme / GPU helpers~~ ✅ Done in `64b8263`
2. ~~Swap call sites in `llama_controller.py`, `llama_gui.py`, `web_tools.py`~~ ✅ Done in `c01df2f`
3. ~~Smoke-test on Linux (must not regress)~~ ✅ Done in `c01df2f` (caught and fixed the `models_root()` bug)
4. ~~Document Windows install/run in `README.md`~~ ✅ Done in `5a56196` (full cross-platform install + Windows notes + PyInstaller)
5. **Hand off to Windows machine for visual validation** ← you are here

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

- **No Windows machine available for testing in this session.** README + `platform_compat.py` are in place; visual validation is the last open item. When the user runs it on Windows, any Tk HiDPI / theme / tray quirks should be filed as bug-fix commits and the resolution recorded in `AGENT_GUIDE.md` under a new "Windows" pitfalls section.
- **Re-run validation on a machine with normal PyPI connectivity** to confirm `666ecfc` moves the verdict from `PARTIAL_PASS` to `PASS`. The headless container that produced the baseline report had timeouts on the `primp` wheel.
- **GitHub Release page for v0.2.0 not created.** Tag is on `origin`; the Release page (with release notes, asset uploads) needs `gh release create`, which is blocked by [[github-account-split]]. Run `gh auth login` as `kushalmanshrestha789` first, then `gh release create v0.2.0 --notes-file <(git tag -l v0.2.0 --format='%(contents)')` (or paste the tag message manually).

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
| _(call-site swap)_ | replace hardcoded constants in the 3 source files with helpers | ✅ Done in `c01df2f` (also caught & fixed `models_root()` bug) |
| _(Windows docs)_ | full cross-platform install + run + PyInstaller in README.md | ✅ Done in `5a56196` |
| _(Windows validation)_ | first run on a real Windows machine; file bug-fix commits for any HiDPI / tray / theme issues | ⏳ Awaiting user handoff |
| `AI_VALIDATION_PROMPT.md` | structured prompt to verify the project on any target OS via an AI | ✅ Done in `b40e54b` |
| `web_tools.py` (search chain) | prefer `duckduckgo_search` over `ddgs` to avoid the `primp` wheel fragility | ✅ Done in `666ecfc` (fixes the install-failure mode caught by the first validation run) |
| `docs/validation/` | audit trail of validation runs | ✅ First report saved in `572b413` |
| `v0.2.0` tag | annotated tag marking the "Cross-platform support" milestone | ✅ Tagged locally + pushed to `origin` |

## Release status

| Version | Status | Notes |
|---|---|---|
| v0.2.0 | ✅ Tagged, pushed to `origin` (commit `b03bc92`) | Cross-platform support; GitHub **Release** page NOT created (blocked on `gh` account split — see [[github-account-split]]) |

---

## How To Update This File

- **State changes** (new direction, milestone, decision) → edit the relevant section
- **New blockers discovered** → add to "Open Blockers"
- **Blockers resolved** → move them to `history.md` with date and resolution
- **New files added** → add to "File Map"
- Do **not** append a running session log here — that's `history.md`
