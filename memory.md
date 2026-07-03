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

**Windows port landed in v0.2.0.** The cross-platform refactor (`platform_compat.py` + call-site swap) is complete and smoke-tested on Linux. The project now runs on both Linux and Windows from a single code path. No active development direction — open items are validation on real Windows hardware and a few small polish commits that can be picked up next session.

**Execution order recap (all complete except the final handoff):**

1. ~~Create `platform_compat.py` with path / theme / GPU helpers~~ ✅ `64b8263`
2. ~~Swap call sites in `llama_controller.py`, `llama_gui.py`, `web_tools.py`~~ ✅ `c01df2f`
3. ~~Smoke-test on Linux (must not regress)~~ ✅ `c01df2f` (caught & fixed the `models_root()` bug)
4. ~~Document Windows install/run in `README.md`~~ ✅ `5a56196` (full cross-platform install + Windows notes + PyInstaller)
5. **Hand off to Windows machine for visual validation** ← still open

**Next session should pick up:** either the first Windows run, or move on to the next project on the upload inventory (`~/clawd` is next up — see [[project-upload-inventory]]).

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
| `llama_gui.py` | Tkinter UI, `SessionTab`, `LlamaChatGUI`, `ThemeManager` | ✅ Refactored, uses `platform_compat` |
| `llama_controller.py` | `LlamaController` subprocess + queue lifecycle | ✅ Refactored, paths + `CREATE_NO_WINDOW` via helpers |
| `web_tools.py` | `search_web()` (DuckDuckGo) + `fetch_url()` | ✅ Dropped `_SYSTEM_SITE` hack, prefers `duckduckgo_search` |
| `requirements.txt` | `duckduckgo_search`, `requests`, `beautifulsoup4`, `psutil`, `Pillow`, `pystray`, `lxml`, `numpy` | ✅ Updated: `duckduckgo_search` primary, `ddgs` as fallback in code |
| `README.md` | User-facing features + install | ✅ Full cross-platform install + Windows section + Validation link |
| `AGENT_GUIDE.md` | Developer handover / architecture | Unchanged from initial drop — may need a Windows pitfalls section after first real Windows run |
| `LICENSE` | MIT | ✅ |
| `.gitignore` | Python + llama.cpp patterns | ✅ |
| `memory.md` | This file — live project state | ✅ |
| `history.md` | Chronological build log | ✅ |
| `platform_compat.py` | cross-platform paths, dark-mode, nvidia-smi, subprocess flags | ✅ `64b8263` |
| `AI_VALIDATION_PROMPT.md` | structured prompt to verify the project on any target OS via an AI | ✅ `b40e54b` |
| `docs/validation/2026-07-03-linux-partial-pass.md` | first validation report (PARTIAL_PASS, env-only install failures) | ✅ `572b413` |

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
