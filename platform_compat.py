"""
platform_compat.py
==================

Cross-platform helpers for the Llama-cpp Chat GUI Pro.

This module centralises every OS-specific assumption the project used to
make inline, so the rest of the codebase can stay portable. It is the
single source of truth for:

  * Where per-user config / data files live (XDG on Linux, %APPDATA% /
    %LOCALAPPDATA% on Windows).
  * How the model directory is located (POSIX `~` glob vs. Windows
    `%USERPROFILE%\\.lmstudio\\models`).
  * How dark mode is detected (gsettings on Linux, Windows registry on
    Windows, both with graceful fallbacks).
  * Where to find the `nvidia-smi` binary.
  * Whether to spawn subprocesses with `CREATE_NO_WINDOW` so launching
    a model does not flash a console on Windows.

Design rules
------------
* No Tkinter imports. This module is unit-testable in pure Python.
* No side effects on import — every helper is a function call.
* Every helper that touches the filesystem is allowed to fail; callers
  must already be wrapping I/O in try/except.
* Helpers return `pathlib.Path` (or lists of them) — not strings — so
  callers do not have to remember which is which.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Platform flag
# ---------------------------------------------------------------------------
IS_WINDOWS: bool = sys.platform == "win32"
IS_LINUX: bool = sys.platform.startswith("linux")


# ---------------------------------------------------------------------------
# Filesystem locations
# ---------------------------------------------------------------------------
def config_dir() -> Path:
    """Per-user config directory.

    Linux:   ~/.config
    Windows: %APPDATA% (e.g. C:\\Users\\<user>\\AppData\\Roaming)

    The directory is *not* created here — callers do that, so this
    function stays side-effect free.
    """
    if IS_WINDOWS:
        base = os.environ.get("APPDATA")
        if not base:
            base = str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "llama-chat"
    return Path(os.path.expanduser("~/.config"))


def data_dir() -> Path:
    """Per-user data directory (benchmarks, caches, etc.).

    Linux:   ~/.local/share
    Windows: %LOCALAPPDATA% (e.g. C:\\Users\\<user>\\AppData\\Local)
    """
    if IS_WINDOWS:
        base = os.environ.get("LOCALAPPDATA")
        if not base:
            base = str(Path.home() / "AppData" / "Local")
        return Path(base) / "llama-chat"
    return Path(os.path.expanduser("~/.local/share"))


def documents_dir() -> Path:
    """User's Documents directory.

    Linux:   ~/Documents (or $XDG_DOCUMENTS_DIR if set)
    Windows: %USERPROFILE%\\Documents, or the OneDrive-redirected path
             via the Win32 Known Folders API if available.
    """
    if IS_WINDOWS:
        # Try the known-folder API first — handles the common case where
        # the user has redirected Documents to OneDrive.
        try:
            import ctypes
            from ctypes import wintypes

            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            # FOLDERID_Documents = {FDD39AD0-238F-46AF-ADB4-6C85480369C7}
            FOLDERID_Documents = "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}"
            SHGetKnownFolderPath = ctypes.windll.shell32.SHGetKnownFolderPath
            SHGetKnownFolderPath.argtypes = [
                ctypes.c_wchar_p, wintypes.DWORD, wintypes.HANDLE, ctypes.POINTER(ctypes.c_wchar_p)
            ]
            SHGetKnownFolderPath.restype = ctypes.HRESULT
            ptr = ctypes.c_wchar_p()
            hr = SHGetKnownFolderPath(FOLDERID_Documents, 0, 0, ctypes.byref(ptr))
            if hr == 0 and ptr.value:
                return Path(ptr.value)
        except Exception:
            pass
        return Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Documents"
    xdg_docs = os.environ.get("XDG_DOCUMENTS_DIR")
    if xdg_docs:
        return Path(xdg_docs)
    return Path(os.path.expanduser("~/Documents"))


def models_root() -> Path:
    """Root directory that holds user-downloaded GGUF chat models.

    Both Linux and Windows put user-downloaded models under
    `~/.lmstudio/models/` (LM Studio's user tree). We deliberately
    *don't* walk the whole `~/.lmstudio/` directory, because it also
    contains `.internal/bundled-models/` (LM Studio's own embedding
    models and other tooling) which we don't want surfaced as chat
    model choices.

    If a future user has models elsewhere, they can set the
    LLAMA_CHAT_MODELS_DIR env var to override.
    """
    override = os.environ.get("LLAMA_CHAT_MODELS_DIR")
    if override:
        return Path(override)

    if IS_WINDOWS:
        profile = os.environ.get("USERPROFILE", str(Path.home()))
        return Path(profile) / ".lmstudio" / "models"
    return Path(os.path.expanduser("~/.lmstudio/models"))


def history_dir() -> Path:
    """Where per-session chat history markdown files are written."""
    return documents_dir() / "ChatArchive" / "llama_chat_project" / "history"


def benchmark_dir() -> Path:
    """Where benchmark CSVs are written."""
    return data_dir() / "llama-chat" / "benchmarks"


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------
def nvidia_smi_cmd() -> list[str]:
    """Return the argv prefix that should be used to invoke nvidia-smi.

    Linux:   ['nvidia-smi'] (assumes the binary is on PATH)
    Windows: searches the two common install locations, then falls back
             to letting PATH resolve it.
    """
    if IS_WINDOWS:
        candidates = [
            r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe",
            r"C:\Windows\System32\nvidia-smi.exe",
        ]
        for path in candidates:
            if Path(path).is_file():
                return [path]
        # Fall through to PATH — shutil.which will validate at call time.
        return ["nvidia-smi.exe"]
    return ["nvidia-smi"]


def subprocess_no_window_kwargs() -> dict:
    """Extra kwargs for `subprocess.Popen` to suppress a console flash.

    On Windows, every `subprocess.Popen` spawns a new console window by
    default. For an app that frequently restarts `llama-cli` (model
    change, ngl change, context-size change, etc.) this is a constant
    flash. Adding `creationflags=0x08000000` (`CREATE_NO_WINDOW`) hides
    the console. On other platforms this returns an empty dict so the
    caller can splat it unconditionally.
    """
    if IS_WINDOWS:
        # CREATE_NO_WINDOW = 0x08000000. Defining it as a hex literal
        # avoids importing subprocess just for one constant.
        return {"creationflags": 0x08000000}
    return {}


# ---------------------------------------------------------------------------
# Theme detection
# ---------------------------------------------------------------------------
def is_dark_mode() -> bool | None:
    """Best-effort dark-mode detection.

    Returns True / False if a clear answer is available, or None if the
    platform-specific source is unavailable — the GUI's ThemeManager
    already treats None as "use the manual override".
    """
    if IS_WINDOWS:
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            )
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return value == 0  # 0 = dark, 1 = light
        except Exception:
            return None

    # Linux / other Unix: try gsettings (GNOME), then xdg (portals).
    try:
        if shutil.which("gsettings"):
            out = subprocess.check_output(
                [
                    "gsettings",
                    "get",
                    "org.gnome.desktop.interface",
                    "color-scheme",
                ],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            if "dark" in out.lower():
                return True
            if "light" in out.lower():
                return False
    except Exception:
        pass

    return None


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Run with `python platform_compat.py` to sanity-check the helpers
    # on the current OS.
    print(f"IS_WINDOWS = {IS_WINDOWS}")
    print(f"IS_LINUX   = {IS_LINUX}")
    print(f"config_dir()  = {config_dir()}")
    print(f"data_dir()    = {data_dir()}")
    print(f"documents_dir = {documents_dir()}")
    print(f"models_root() = {models_root()}")
    print(f"history_dir() = {history_dir()}")
    print(f"benchmark_dir = {benchmark_dir()}")
    print(f"nvidia_smi_cmd() = {nvidia_smi_cmd()}")
    print(f"subprocess_no_window_kwargs() = {subprocess_no_window_kwargs()}")
    print(f"is_dark_mode() = {is_dark_mode()}")
