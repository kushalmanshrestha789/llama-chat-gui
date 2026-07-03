# AI Validation Prompt

> **Purpose:** Paste the prompt below into any capable AI assistant (Claude, GPT, Gemini, local model, etc.) and have it clone, install, and test this repository on a target machine. The AI returns a structured pass/fail report.
>
> **Why this exists:** Cross-platform code can only be validated by running it on the target platform. After the Windows port of Llama-cpp Chat GUI Pro, every commit should ideally be re-verified on both Linux and Windows. This prompt is the contract for that verification.

---

## The Prompt (copy everything between the markers)

```
You are a senior QA engineer. Your job is to clone, install, and
test the repository at:

    https://github.com/kushalmanshrestha789/llama-chat-gui

on the machine you are running on, then return a structured
pass/fail report.

== SCOPE ==

You MUST:

  1. Detect the host operating system. Report it explicitly.
     Acceptable values: Linux, macOS, Windows. If it is anything
     else, stop and report UNSUPPORTED_PLATFORM.

  2. Clone the repository to a temporary working directory
     (e.g. /tmp/llama-chat-gui-qa on Linux/macOS,
     %TEMP%\llama-chat-gui-qa on Windows). Use the HTTPS URL,
     not SSH, so the clone works without GitHub credentials.

  3. Check out the main branch at the commit hash the user
     supplies. If no hash is supplied, use HEAD of main.

  4. Run the static checks:
       - `python3 -m py_compile platform_compat.py
                          llama_controller.py web_tools.py`
         (Windows: use `python` instead of `python3`)
       - Confirm all .py files compile with no errors.

  5. Run the unit-level smoke tests for platform_compat:
         cd <repo>
         python3 platform_compat.py
       Capture the output. Every helper must return a sensible
       value. (For Windows, the nvidia-smi path may legitimately
       not exist; that is OK as long as the function returns
       without raising.)

  6. Run the cross-platform regression assertion. Execute this
     Python snippet and report the result:

         import sys, glob
         sys.path.insert(0, '.')
         from pathlib import Path
         from platform_compat import (
             config_dir, data_dir, documents_dir, models_root,
             nvidia_smi_cmd, subprocess_no_window_kwargs,
             is_dark_mode, IS_WINDOWS,
         )
         # Linux/XDG expectations
         if not IS_WINDOWS:
             assert config_dir()  == Path.home() / '.config'
             assert data_dir()    == Path.home() / '.local' / 'share'
             assert models_root() == Path.home() / '.lmstudio' / 'models'
             assert nvidia_smi_cmd() == ['nvidia-smi']
             assert subprocess_no_window_kwargs() == {}
         # Windows expectations
         else:
             import os
             assert str(config_dir()).lower().startswith(
                 os.environ.get('APPDATA', '').lower()
             )
             assert str(data_dir()).lower().startswith(
                 os.environ.get('LOCALAPPDATA', '').lower()
             )
             assert nvidia_smi_cmd()  # returns a list, no raise
         # Both platforms
         assert is_dark_mode() is None or isinstance(is_dark_mode(), bool)
         print('REGRESSION_OK')

  7. Try to install runtime dependencies:
         python3 -m pip install -r requirements.txt
     Report which packages installed cleanly and which (if any)
     failed. A failure here is a PARTIAL_PASS, not a FAIL — the
     static checks and regression assertion are what matter for
     this prompt.

  8. Confirm `llama-cli` is on PATH by running `llama-cli --version`
     or `where llama-cli` (Windows) / `which llama-cli` (Linux).
     If it is missing, report LLAMA_CLI_MISSING. Do NOT attempt
     to install it — that is out of scope.

  9. Optionally attempt to start the GUI with a short timeout
     (e.g. 5 seconds) and report whether the window appeared.
     On headless machines, skip this step and report
     HEADLESS_SKIP. Do not treat a failure here as a FAIL.

== OUTPUT FORMAT ==

Return a Markdown report with EXACTLY these sections, in this
order. Use the literal words PASS / FAIL / PARTIAL_PASS /
SKIPPED for the verdict.

    ## Validation Report

    **Repo:**   https://github.com/kushalmanshrestha789/llama-chat-gui
    **Commit:** <hash you checked out, or 'main HEAD'>
    **OS:**     <Linux | macOS | Windows | UNSUPPORTED_PLATFORM>
    **Python:** <version, e.g. 3.12.4>
    **Verdict:** <PASS | FAIL | PARTIAL_PASS | SKIPPED>

    ### Static checks
    - py_compile platform_compat.py:    <PASS | FAIL — paste error>
    - py_compile llama_controller.py:   <PASS | FAIL — paste error>
    - py_compile web_tools.py:          <PASS | FAIL — paste error>
    - llama_gui.py is intentionally NOT compiled here because
      it imports tkinter and psutil; that import is tested in
      'Runtime imports' below.

    ### platform_compat self-test
    <paste the full output of `python3 platform_compat.py`>

    ### Cross-platform regression assertion
    <paste the result; 'REGRESSION_OK' or the AssertionError>

    ### Dependency install
    - ddgs:                 <installed | failed — paste error>
    - requests:             <installed | failed — paste error>
    - beautifulsoup4:       <installed | failed — paste error>
    - psutil:               <installed | failed — paste error>
    - Pillow:               <installed | failed — paste error>
    - pystray:              <installed | failed — paste error>

    ### llama-cli
    - On PATH: <yes — version X.Y.Z | no — LLAMA_CLI_MISSING>

    ### Runtime imports
    - `import platform_compat`:  <PASS | FAIL — paste error>
    - `import web_tools`:        <PASS | FAIL — paste error>
    - `import llama_controller`: <PASS | FAIL — paste error>
    - `import llama_gui` (only if tkinter + psutil + pystray
      are importable):           <PASS | FAIL | SKIPPED — reason>

    ### GUI smoke (optional)
    <what happened when you tried to launch the GUI, or
    HEADLESS_SKIP>

    ### Notes
    <any observations a human reviewer would want to know:
    deprecation warnings, suspicious paths, anything that
    surprised you. Be concrete.>

== RULES ==

- Do not modify the repository. Read-only verification.
- Do not push, tag, or create releases.
- Do not invent output you did not observe. If a check did not
  run, mark it SKIPPED with the reason.
- Prefer real evidence (paste the command output) over
  paraphrase.
- If you cannot complete the task, report what you did manage
  and where you stopped. Do not silently skip steps.
- The verdict MUST be derived from the sections above:
      FAIL               — any static check or the regression
                            assertion failed
      PARTIAL_PASS       — static checks + regression pass, but
                            dependency install or runtime
                            import failed
      SKIPPED            — only the optional GUI smoke was
                            skipped; everything else passed
      PASS               — every section passed
```

---

## How To Use

1. **Pick a target machine** — ideally a clean Windows 11 VM or a fresh Linux container. The whole point is to test on the *target* OS, not on whatever you developed on.
2. **Open a fresh AI session** (Claude, GPT, etc.) and paste the prompt above.
3. **Optionally** add a line at the end specifying a commit hash:
   > "Check out commit `c01df2f` for this run."
4. **Run it.** The AI will return a Markdown report. Save the report under `docs/validation/` in your project (or wherever your CI stores artifacts) for the audit trail.

## When To Re-Run

- After every `feat:` commit that touches `llama_controller.py`, `llama_gui.py`, `web_tools.py`, or `platform_compat.py`
- After every `refactor:` commit
- Before any release tag (`v0.2.0`, `v0.3.0`, …)
- After upgrading Python, Tk, or any dependency in `requirements.txt`

## When NOT To Run

- For `docs:` commits only (README, AGENT_GUIDE, memory, history) — nothing executable changed
- For `chore:` commits that don't touch `.py` files (LICENSE, .gitignore, etc.)
