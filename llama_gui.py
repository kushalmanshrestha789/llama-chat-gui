#!/usr/bin/env python3
import os
import sys
import json
import csv
import re
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
from datetime import datetime
import glob
import threading
import subprocess

import pystray
from pystray import MenuItem as item
from llama_controller import (
    LlamaController, load_profile, save_profile,
    list_presets, load_preset, save_preset, delete_preset
)

import web_tools
from platform_compat import (
    is_dark_mode,
    history_dir,
    benchmark_dir,
    models_root,
    nvidia_smi_cmd,
)

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

DEFAULT_MODEL_PATH = "/home/cipher/.lmstudio/models/lmstudio-community/gemma-4-E2B-it-GGUF/gemma-4-E2B-it-Q4_K_M.gguf"
# MODEL_SEARCH_PATH is derived at runtime — see _populate_models()
HISTORY_DIR = str(history_dir()) + os.sep
BENCHMARK_DIR = str(benchmark_dir()) + os.sep


class ThemeManager:
    def __init__(self):
        self._mode = "auto"
        self._listeners = []
        self._update()

    def _detect_dark_mode(self):
        result = is_dark_mode()
        if result is None:
            return True  # default to dark if platform-specific source is unavailable
        return result

    def _get_palette(self):
        if self.dark_mode:
            return {
                "bg": "#1e1e1e",
                "fg": "#d4d4d4",
                "sidebar_bg": "#252526",
                "accent": "#007acc",
                "text_area": "#1e1e1e",
                "input_bg": "#3c3c3c",
                "input_fg": "#ffffff",
                "status_ok": "#4ec9b0"
            }
        else:
            return {
                "bg": "#ffffff",
                "fg": "#000000",
                "sidebar_bg": "#f3f3f3",
                "accent": "#005fb8",
                "text_area": "#ffffff",
                "input_bg": "#ffffff",
                "input_fg": "#000000",
                "status_ok": "#2e7d32"
            }

    def _update(self):
        if self._mode == "light":
            self.dark_mode = False
        elif self._mode == "dark":
            self.dark_mode = True
        else:
            self.dark_mode = self._detect_dark_mode()
        self.colors = self._get_palette()

    def set_mode(self, mode):
        if mode not in ("auto", "light", "dark"):
            return
        self._mode = mode
        self._update()
        for cb in self._listeners:
            cb(self.colors)

    def on_change(self, callback):
        self._listeners.append(callback)


class SessionTab:
    def __init__(self, parent, notebook, theme, model_path, ngl=0, ctx_size=2048, temp=0.7, top_p=0.9, system_prompt=""):
        self.theme = theme
        self.controller = LlamaController(model_path, ngl, ctx_size, temp, top_p, system_prompt)
        self.frame = ttk.Frame(notebook)
        self.metrics = {
            "prompt_speed": "--",
            "gen_speed": "--",
            "sample_speed": "--",
            "sample_runs": "--",
            "tokens": "0",
            "used_tokens": 0,
            "ctx": "--",
            "offload": "--",
        }
        self.turn_summary = []
        self.turn_speeds = []
        self.current_turn = 0
        self.speed_history = []
        self.graph_shown = False
        self.benchmark_enabled = False
        self.benchmark_file = None
        self.benchmark_writer = None
        self._in_thinking = False
        self._thinking_buffer = []
        self._gen_active = False
        self._gen_timeout = None
        self._last_user_msg = ""
        self._web_context = ""
        self._search_match_positions = []
        self._search_current = -1
        self._tool_mode = False
        self._tool_call_re = re.compile(r'\[TOOL_CALL\s+(\w+)\(([^)]*)\)\]')
        self._output_buffer = ""
        self._tool_executing = False
        self._base_system_prompt = system_prompt

        self.chat_display = scrolledtext.ScrolledText(
            self.frame, wrap=tk.WORD, state="disabled",
            font=("Consolas", 11),
            bg=theme.colors["text_area"], fg=theme.colors["fg"],
            insertbackground=theme.colors["fg"]
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 5))
        self.chat_display.bind("<Button-3>", self._show_context_menu)
        self.chat_display.tag_configure("search_highlight", background="#ffff00", foreground="#000000")
        self.chat_display.tag_configure("search_current", background="#ff9900", foreground="#000000")

        self.search_frame = tk.Frame(self.frame, bg=theme.colors["bg"])

        self.log_display = scrolledtext.ScrolledText(
            self.frame, height=8, state="disabled",
            font=("Monospace", 9), bg="#000000", fg="#00ff00",
        )
        self.log_display.pack(fill=tk.X, padx=10, pady=(0, 5))
        tk.Label(self.frame, text="System Logs", font=("Arial", 9, "italic"),
                 fg=theme.colors["fg"], bg=theme.colors["bg"]).pack(anchor=tk.W, padx=10)

        self.graph_canvas = tk.Canvas(self.frame, height=70, bg="#1a1a1a", highlightthickness=0)

        toolbar = tk.Frame(self.frame, bg=theme.colors["bg"])
        toolbar.pack(fill=tk.X, padx=10, pady=(0, 5))
        self.graph_btn = tk.Button(toolbar, text="\u25bc Graph", command=self._toggle_graph, width=8)
        self.graph_btn.pack(side=tk.LEFT, padx=2)

        input_frame = tk.Frame(self.frame, bg=theme.colors["bg"])
        input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(
            input_frame, textvariable=self.input_var,
            bg=theme.colors["input_bg"], fg=theme.colors["input_fg"],
            insertbackground=theme.colors["input_fg"]
        )
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.input_entry.bind("<Return>", self.send_message)

        tk.Button(input_frame, text="Send", command=self.send_message, width=10).pack(side=tk.LEFT, padx=2)
        tk.Button(input_frame, text="\u25a0 Stop", command=lambda: self.controller.stop_generation(),
                  fg="white", bg="#d32f2f").pack(side=tk.LEFT, padx=2)
        tk.Button(input_frame, text="Clear", command=self.clear_chat, width=10).pack(side=tk.LEFT, padx=2)

        self.think_mode = tk.BooleanVar(value=False)
        tk.Checkbutton(input_frame, text="Think", variable=self.think_mode,
                       bg=theme.colors["bg"], fg=theme.colors["fg"],
                       selectcolor=theme.colors["sidebar_bg"],
                       activebackground=theme.colors["bg"]).pack(side=tk.LEFT, padx=2)
        self.tool_mode_var = tk.BooleanVar(value=False)
        tk.Checkbutton(input_frame, text="\U0001f6e0 Tools", variable=self.tool_mode_var,
                       command=self._on_tool_mode_change,
                       bg=theme.colors["bg"], fg=theme.colors["fg"],
                       selectcolor=theme.colors["sidebar_bg"],
                       activebackground=theme.colors["bg"]).pack(side=tk.LEFT, padx=2)
        tk.Button(input_frame, text="\U0001f310 Web", command=self._web_search_dialog,
                  width=6).pack(side=tk.LEFT, padx=2)

        os.makedirs(HISTORY_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.history_path = os.path.join(HISTORY_DIR, f"{timestamp}.md")
        with open(self.history_path, "w") as f:
            f.write(f"# Chat Session: {timestamp}\n\n")

        notebook.add(self.frame, text=self._title())

    def _title(self):
        return os.path.basename(self.controller.model_path)[:25]

    def apply_theme(self, colors):
        self.theme.colors = colors
        self.chat_display.config(bg=colors["text_area"], fg=colors["fg"],
                                  insertbackground=colors["fg"])
        self.input_entry.config(bg=colors["input_bg"], fg=colors["input_fg"],
                                 insertbackground=colors["input_fg"])
        self.search_frame.config(bg=colors["bg"])

    def append_chat(self, txt):
        self.chat_display.configure(state="normal")
        self.chat_display.insert(tk.END, txt)
        self.chat_display.configure(state="disabled")
        self.chat_display.see(tk.END)

    def append_log(self, txt):
        self.log_display.configure(state="normal")
        self.log_display.insert(tk.END, txt + "\n")
        self.log_display.configure(state="disabled")
        self.log_display.see(tk.END)

    def clear_chat(self):
        self.chat_display.configure(state="normal")
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.configure(state="disabled")

    def send_message(self, event=None):
        msg = self.input_var.get().strip()
        if not msg:
            return

        if msg.startswith("/search ") or msg.startswith("/web "):
            prefix = "/search " if msg.startswith("/search ") else "/web "
            query = msg[len(prefix):].strip()
            if query:
                self._do_web_search(query)
                self.input_var.set("")
            return

        if msg.startswith("/fetch "):
            url = msg[7:].strip()
            if url:
                self._do_web_fetch(url)
                self.input_var.set("")
            return

        self._finalize_turn()
        self.current_turn += 1
        tag = ""
        if self.think_mode.get():
            actual_msg = (
                f"Let's think through this step by step.\n\n"
                f"{msg}\n\n"
                f"After reasoning through it, provide a clear answer."
            )
            tag = " [Thinking]"
        else:
            actual_msg = msg
        self._last_user_msg = actual_msg
        self.append_chat(f"> {msg}{tag}\n")
        self._log_to_history("User", msg)
        if self.controller.send(actual_msg):
            self.input_var.set("")
        else:
            self.append_chat("\n[Error: Could not send message to process]\n")

    def _log_to_history(self, role, text):
        timestamp = datetime.now().strftime("%H:%M:%S")
        try:
            with open(self.history_path, "a") as f:
                f.write(f"**{role}** [{timestamp}]: {text}\n\n")
        except Exception as e:
            print(f"History log error: {e}")

    def _show_context_menu(self, event):
        menu = tk.Menu(self.frame, tearoff=0)
        menu.add_command(label="Copy", command=self._copy_selection)
        menu.add_separator()
        menu.add_command(label="Clear Chat", command=self.clear_chat)
        if self._last_user_msg:
            menu.add_command(label="Regenerate", command=self._regenerate_last)
        menu.tk_popup(event.x_root, event.y_root)
        menu.grab_release()

    def _copy_selection(self):
        try:
            text = self.chat_display.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.clipboard_clear()
            self.clipboard_append(text)
        except tk.TclError:
            pass

    def _regenerate_last(self):
        if self._last_user_msg:
            self.append_chat(f"\n--- Regenerating ---\n")
            self.controller.send(self._last_user_msg)

    def _mark_generating(self):
        self._gen_active = True
        if self._gen_timeout:
            self.frame.after_cancel(self._gen_timeout)
        self._gen_timeout = self.frame.after(3000, self._mark_idle)

    def _mark_idle(self):
        self._gen_active = False
        self._gen_timeout = None

    def process_output(self, line, think_mode_on):
        if self._tool_mode and not self._tool_executing:
            self._output_buffer += line + "\n"
            m = self._tool_call_re.search(self._output_buffer)
            if m:
                self._handle_tool_call(m)
                return
        if "[Start thinking]" in line:
            self._in_thinking = True
            self._thinking_buffer = []
            if think_mode_on:
                self.append_chat(line + "\n")
                self.append_log(line)
            return
        if "[End thinking]" in line:
            self._in_thinking = False
            if think_mode_on:
                self.append_chat(line + "\n")
                self.append_log(line)
            else:
                self.append_chat("\n[Thinking hidden \u2014 toggle Think to view]\n")
            return
        if self._in_thinking:
            self._thinking_buffer.append(line)
            if think_mode_on:
                self.append_chat(line + "\n")
                self.append_log(line)
            return
        self.append_chat(line + "\n")
        self.append_log(line)

    def _get_system_prompt(self):
        base = self._base_system_prompt
        if not self._tool_mode:
            return base
        tools_def = (
            "You have access to the following tools. When you need to use a tool, "
            "output EXACTLY on a single line:\n"
            "[TOOL_CALL tool_name(arguments)]\n\n"
            "Available tools:\n"
            "- web_search(query): Search the web for current information.\n"
            "- fetch_url(url): Fetch and extract text content from a URL.\n\n"
            "When you receive a [TOOL_RESULT], use that information to answer "
            "the user's question. Do not repeat the tool call.\n"
        )
        return (tools_def + "\n" + base) if base else tools_def

    def _handle_tool_call(self, match):
        self._tool_executing = True
        tool_name = match.group(1)
        args_str = match.group(2).strip()
        self.append_chat(f"\n[Tool Call: {tool_name}({args_str})]\n")
        self.append_log(f"[TOOL] {tool_name}({args_str})")
        self.controller.stop_generation()

        def execute():
            try:
                if tool_name == "web_search":
                    query = args_str.strip("\"'")
                    success, result = web_tools.search_web(query)
                elif tool_name == "fetch_url":
                    url = args_str.strip("\"'")
                    success, result = web_tools.fetch_url(url)
                else:
                    result = f"Unknown tool: {tool_name}"
                    success = False
                if success:
                    self.frame.after(0, self._on_tool_result, result)
                else:
                    self.frame.after(0, self._on_tool_result, f"Error: {result}")
            except Exception as e:
                self.frame.after(0, self._on_tool_result, f"Error: {e}")

        threading.Thread(target=execute, daemon=True).start()

    def _on_tool_result(self, result):
        self.append_chat(f"[Tool Result]\n{result[:2000]}\n\n")
        self.append_log(f"[TOOL] Result received ({len(result)} chars)")
        tool_msg = f"[TOOL_RESULT]\n{result}"
        self.controller.send(tool_msg)
        self._output_buffer = ""
        self._tool_executing = False

    def _on_tool_mode_change(self):
        self._tool_mode = self.tool_mode_var.get()
        if self._tool_mode:
            prompt = self._get_system_prompt()
            self.controller.set_system_prompt(prompt)
            self.append_chat("\n--- Tool mode enabled ---\n")
        else:
            self.controller.set_system_prompt(self._base_system_prompt)
            self.append_chat("\n--- Tool mode disabled ---\n")

    def _finalize_turn(self):
        if self.turn_speeds:
            avg = sum(self.turn_speeds) / len(self.turn_speeds)
            self.turn_summary.append(
                f"Turn {self.current_turn}: {avg:.1f} t/s ({len(self.turn_speeds)} samples)"
            )
            self.turn_speeds = []

    def _record_gen_speed(self, speed):
        s = float(speed)
        self.turn_speeds.append(s)
        self.speed_history.append((time.time(), s))
        if len(self.speed_history) > 60:
            self.speed_history = self.speed_history[-60:]
        if self.graph_shown:
            self.after(10, self._draw_speed_graph)

    def _toggle_graph(self):
        self.graph_shown = not self.graph_shown
        if self.graph_shown:
            self.graph_canvas.pack(fill=tk.X, padx=10, pady=(0, 5))
            self.after(100, self._draw_speed_graph)
        else:
            self.graph_canvas.pack_forget()
        self.graph_btn.config(text="\u25b2 Graph" if self.graph_shown else "\u25bc Graph")

    def _draw_speed_graph(self):
        self.graph_canvas.delete("all")
        if len(self.speed_history) < 2:
            return
        w = self.graph_canvas.winfo_width()
        h = self.graph_canvas.winfo_height()
        if w < 10 or h < 10:
            return
        history = self.speed_history[-60:]
        max_speed = max(max(s for _, s in history), 1)
        points = []
        for i, (_, speed) in enumerate(history):
            x = int(w * i / (len(history) - 1))
            y = int(h * (1 - speed / max_speed))
            points.extend([x, y])
        self.graph_canvas.create_line(points, fill="#4ec9b0", width=2, smooth=True)
        for i in range(0, len(history), max(1, len(history) // 5)):
            x = int(w * i / (len(history) - 1))
            y = int(h * (1 - history[i][1] / max_speed))
            self.graph_canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill="#4ec9b0", outline="")

    def _write_benchmark(self, event_type, tokens, speed):
        if not self.benchmark_enabled or not self.benchmark_writer:
            return
        self.benchmark_writer.writerow([
            datetime.now().isoformat(),
            os.path.basename(self.controller.model_path),
            event_type, tokens, speed,
            self.controller.ctx_size, self.controller.ngl
        ])
        self.benchmark_file.flush()

    def _open_search(self):
        c = self.theme.colors
        self.search_frame.config(bg=c["bg"])
        for w in self.search_frame.winfo_children():
            w.destroy()
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *a: self._do_search())
        entry = tk.Entry(self.search_frame, textvariable=self.search_var,
                         bg=c["input_bg"], fg=c["input_fg"],
                         insertbackground=c["input_fg"])
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=2)
        entry.focus_set()
        entry.bind("<Escape>", lambda e: self._close_search())
        entry.bind("<Return>", lambda e: self._search_next())
        self.search_count_lbl = tk.Label(self.search_frame, text="", fg=c["fg"], bg=c["bg"])
        self.search_count_lbl.pack(side=tk.LEFT, padx=2)
        tk.Button(self.search_frame, text="\u25b2", command=self._search_prev, width=3).pack(side=tk.LEFT)
        tk.Button(self.search_frame, text="\u25bc", command=self._search_next, width=3).pack(side=tk.LEFT)
        tk.Button(self.search_frame, text="\u2715", command=self._close_search, width=3).pack(side=tk.LEFT)
        self.search_frame.pack(fill=tk.X, before=self.chat_display)

    def _close_search(self):
        self.search_frame.pack_forget()
        self.chat_display.tag_remove("search_highlight", "1.0", tk.END)
        self.chat_display.tag_remove("search_current", "1.0", tk.END)
        self._search_match_positions = []
        self._search_current = -1

    def _do_search(self):
        self.chat_display.tag_remove("search_highlight", "1.0", tk.END)
        self.chat_display.tag_remove("search_current", "1.0", tk.END)
        query = self.search_var.get()
        self._search_match_positions = []
        self._search_current = -1
        if not query:
            self.search_count_lbl.config(text="")
            return
        text = self.chat_display.get("1.0", tk.END)
        pos = "1.0"
        while True:
            pos = self.chat_display.search(query, pos, tk.END, nocase=True)
            if not pos:
                break
            end = f"{pos}+{len(query)}c"
            self._search_match_positions.append((pos, end))
            self.chat_display.tag_add("search_highlight", pos, end)
            pos = end
        if self._search_match_positions:
            self._search_current = 0
            self._jump_to_match(0)
            self.search_count_lbl.config(
                text=f"{len(self._search_match_positions)} match{'es' if len(self._search_match_positions) != 1 else ''}"
            )
        else:
            self.search_count_lbl.config(text="No matches")

    def _search_next(self):
        if not self._search_match_positions:
            return
        self._search_current = (self._search_current + 1) % len(self._search_match_positions)
        self._jump_to_match(self._search_current)

    def _search_prev(self):
        if not self._search_match_positions:
            return
        self._search_current = (self._search_current - 1) % len(self._search_match_positions)
        self._jump_to_match(self._search_current)

    def _jump_to_match(self, idx):
        self.chat_display.tag_remove("search_current", "1.0", tk.END)
        if 0 <= idx < len(self._search_match_positions):
            pos, end = self._search_match_positions[idx]
            self.chat_display.tag_add("search_current", pos, end)
            self.chat_display.see(pos)

    def _toggle_search(self, event=None):
        if self.search_frame.winfo_ismapped():
            self._close_search()
        else:
            self._open_search()

    def _web_search_dialog(self):
        query = simpledialog.askstring("Web Search", "Enter search query:",
                                        parent=self.frame)
        if query:
            self._do_web_search(query)

    def _do_web_search(self, query):
        self._web_context = ""
        self.append_chat(f"\n--- Searching for: {query} ---\n")
        self.append_log(f"[WEB] Searching: {query}")
        self._mark_generating()
        def task():
            success, results = web_tools.search_web(query)
            self.frame.after(0, self._on_web_results, query, results, success)
        threading.Thread(target=task, daemon=True).start()

    def _on_web_results(self, query, results, success):
        if not success:
            self.append_chat(f"Search failed: {results}\n")
            self.append_log(f"[WEB] Error: {results}")
            return
        self._web_context = (
            "[Web Search Results for \"{}\"]\n"
            "{}\n\n"
            "---\n"
            "User's question: {}\n\n"
            "Using the search results above, answer the user's question thoroughly."
        ).format(query, results, query)
        self.append_chat(f"[Web Search Results]\n{results}\n\n")
        self.append_chat("Context loaded. Ask your question or I'll answer now.\n")
        self.append_log(f"[WEB] Context stored ({len(results)} chars)")
        ok = self.controller.send(self._web_context)
        if not ok:
            self.append_chat("[Error: Failed to send search context to model]\n")

    def _do_web_fetch(self, url):
        self._web_context = ""
        self.append_chat(f"\n--- Fetching: {url} ---\n")
        self.append_log(f"[WEB] Fetching: {url}")
        self._mark_generating()
        def task():
            success, content = web_tools.fetch_url(url)
            self.frame.after(0, self._on_web_fetch_results, url, content, success)
        threading.Thread(target=task, daemon=True).start()

    def _on_web_fetch_results(self, url, content, success):
        if not success:
            self.append_chat(f"Fetch failed: {content}\n")
            self.append_log(f"[WEB] Error: {content}")
            return
        truncated = content[:4000]
        self._web_context = (
            "[Content from {}]\n"
            "{}\n\n"
            "---\n"
            "User's question about the above content: {}\n\n"
            "Using the fetched content above, answer the user's question."
        ).format(url, truncated, url)
        self.append_chat(f"[Fetched Content]\n{content[:2000]}\n\n")
        self.append_chat("Context loaded. Ask your question or I'll answer now.\n")
        self.append_log(f"[WEB] Context stored ({len(content)} chars)")
        ok = self.controller.send(self._web_context)
        if not ok:
            self.append_chat("[Error: Failed to send fetched content to model]\n")
        self.controller.send(context)


class LlamaChatGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.theme = ThemeManager()
        self.theme.on_change(self._retheme_all)
        self.title("Llama-cpp Chat GUI Pro")
        self.geometry("1000x800")
        self.configure(bg=self.theme.colors["bg"])

        self.sessions = []
        self.active_session = None
        self._syncing = False

        self._setup_ui()
        self._new_session()

        self.after(100, self.poll_queues)
        self.after(500, self._update_stream_indicator)
        if HAS_PSUTIL:
            self.after(2000, self._poll_hardware)

        self.tray_thread = threading.Thread(target=self._setup_tray, daemon=True)
        self.tray_thread.start()

        self.bind("<Control-f>", self._global_search)
        self.bind("<Control-F>", self._global_search)

    def _global_search(self, event):
        if self.active_session:
            self.active_session._toggle_search()

    def _setup_ui(self):
        main_container = tk.Frame(self, bg=self.theme.colors["bg"])
        main_container.pack(fill=tk.BOTH, expand=True)

        sidebar = tk.Frame(main_container, width=250, bg=self.theme.colors["sidebar_bg"])
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        sidebar.pack_propagate(False)

        y = 0
        tk.Label(sidebar, text="Settings", font=("Arial", 12, "bold"),
                 fg=self.theme.colors["fg"], bg=self.theme.colors["sidebar_bg"]).pack(pady=(10, 20))

        tk.Label(sidebar, text="Model:", fg=self.theme.colors["fg"],
                 bg=self.theme.colors["sidebar_bg"]).pack(anchor=tk.W)
        self.model_var = tk.StringVar()
        self.model_dropdown = ttk.Combobox(sidebar, textvariable=self.model_var, state="readonly")
        self.model_dropdown.pack(fill=tk.X, pady=(0, 15))
        self._populate_models()
        self.model_dropdown.bind("<<ComboboxSelected>>", self.on_model_change)

        tk.Label(sidebar, text="GPU Offload (ngl):", fg=self.theme.colors["fg"],
                 bg=self.theme.colors["sidebar_bg"]).pack(anchor=tk.W)
        self.ngl_var = tk.IntVar(value=0)
        self.ngl_slider = ttk.Scale(sidebar, from_=0, to=100, variable=self.ngl_var,
                                    orient=tk.HORIZONTAL, command=self.on_ngl_slide)
        self.ngl_slider.pack(fill=tk.X, pady=(0, 5))
        self.ngl_label = tk.Label(sidebar, text="Value: 0",
                                  fg=self.theme.colors["fg"], bg=self.theme.colors["sidebar_bg"])
        self.ngl_label.pack(pady=(0, 15))
        self.ngl_slider.bind("<ButtonRelease-1>", self.apply_ngl)

        tk.Label(sidebar, text="Temperature:", fg=self.theme.colors["fg"],
                 bg=self.theme.colors["sidebar_bg"]).pack(anchor=tk.W)
        self.temp_var = tk.DoubleVar(value=0.7)
        self.temp_slider = ttk.Scale(sidebar, from_=0.0, to=2.0, variable=self.temp_var,
                                     orient=tk.HORIZONTAL, command=self.on_temp_slide)
        self.temp_slider.pack(fill=tk.X, pady=(0, 5))
        self.temp_label = tk.Label(sidebar, text="0.70",
                                   fg=self.theme.colors["fg"], bg=self.theme.colors["sidebar_bg"])
        self.temp_label.pack(pady=(0, 15))
        self.temp_slider.bind("<ButtonRelease-1>", self.apply_temp)

        tk.Label(sidebar, text="Top-P:", fg=self.theme.colors["fg"],
                 bg=self.theme.colors["sidebar_bg"]).pack(anchor=tk.W)
        self.top_p_var = tk.DoubleVar(value=0.9)
        self.top_p_slider = ttk.Scale(sidebar, from_=0.0, to=1.0, variable=self.top_p_var,
                                      orient=tk.HORIZONTAL, command=self.on_top_p_slide)
        self.top_p_slider.pack(fill=tk.X, pady=(0, 5))
        self.top_p_label = tk.Label(sidebar, text="0.90",
                                    fg=self.theme.colors["fg"], bg=self.theme.colors["sidebar_bg"])
        self.top_p_label.pack(pady=(0, 15))
        self.top_p_slider.bind("<ButtonRelease-1>", self.apply_top_p)

        tk.Label(sidebar, text="Context Size:", fg=self.theme.colors["fg"],
                 bg=self.theme.colors["sidebar_bg"]).pack(anchor=tk.W)
        self.ctx_var = tk.IntVar(value=2048)
        self.ctx_dropdown = ttk.Combobox(sidebar, textvariable=self.ctx_var, state="readonly",
                                          values=[512, 1024, 2048, 4096, 8192, 16384, 32768])
        self.ctx_dropdown.pack(fill=tk.X, pady=(0, 15))
        self.ctx_dropdown.bind("<<ComboboxSelected>>", self.on_ctx_change)

        tk.Label(sidebar, text="System Prompt:", fg=self.theme.colors["fg"],
                 bg=self.theme.colors["sidebar_bg"]).pack(anchor=tk.W)
        self.sys_prompt_text = scrolledtext.ScrolledText(
            sidebar, height=4, wrap=tk.WORD,
            bg=self.theme.colors["input_bg"], fg=self.theme.colors["input_fg"],
            insertbackground=self.theme.colors["input_fg"]
        )
        self.sys_prompt_text.pack(fill=tk.X, pady=(0, 5))
        tk.Button(sidebar, text="Apply Prompt", command=self.apply_system_prompt).pack(pady=(0, 15))

        tk.Label(sidebar, text="Theme:", fg=self.theme.colors["fg"],
                 bg=self.theme.colors["sidebar_bg"]).pack(anchor=tk.W)
        self.theme_var = tk.StringVar(value="Auto")
        theme_dropdown = ttk.Combobox(sidebar, textvariable=self.theme_var, state="readonly",
                                       values=["Auto", "Light", "Dark"])
        theme_dropdown.pack(fill=tk.X, pady=(0, 15))
        theme_dropdown.bind("<<ComboboxSelected>>", self.on_theme_change)

        tk.Label(sidebar, text="Preset:", fg=self.theme.colors["fg"],
                 bg=self.theme.colors["sidebar_bg"]).pack(anchor=tk.W)
        preset_frame = tk.Frame(sidebar, bg=self.theme.colors["sidebar_bg"])
        preset_frame.pack(fill=tk.X, pady=(0, 15))
        self.preset_var = tk.StringVar()
        self.preset_dropdown = ttk.Combobox(preset_frame, textvariable=self.preset_var, state="readonly")
        self.preset_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.preset_dropdown.bind("<<ComboboxSelected>>", self.on_preset_select)
        tk.Button(preset_frame, text="Save", command=self._save_preset_dialog, width=5).pack(side=tk.LEFT, padx=(5, 0))
        self._refresh_presets()

        tk.Label(sidebar, text="Sessions", font=("Arial", 12, "bold"),
                 fg=self.theme.colors["fg"], bg=self.theme.colors["sidebar_bg"]).pack(pady=(10, 5))
        btn_frame = tk.Frame(sidebar, bg=self.theme.colors["sidebar_bg"])
        btn_frame.pack(fill=tk.X)
        tk.Button(btn_frame, text="+ New", command=self._new_session).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(btn_frame, text="\u00d7 Close", command=self._close_active_session).pack(side=tk.LEFT)

        self.turn_display = tk.Text(sidebar, height=6, width=28,
                                    bg=self.theme.colors["input_bg"],
                                    fg=self.theme.colors["input_fg"],
                                    state="disabled", font=("Monospace", 9))
        self.turn_display.pack(fill=tk.X, pady=(5, 5))

        self.status_label = tk.Label(sidebar, text="Status: Running",
                                     fg=self.theme.colors["status_ok"],
                                     bg=self.theme.colors["sidebar_bg"])
        self.status_label.pack(side=tk.BOTTOM, pady=20)

        chat_area = tk.Frame(main_container, bg=self.theme.colors["bg"])
        chat_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(chat_area)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        self.status_frame = tk.Frame(self, bg=self.theme.colors["sidebar_bg"])
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X, before=main_container)

        self.stream_label = tk.Label(self.status_frame, text="\u25cb Idle",
                                     fg="#888888", bg=self.theme.colors["sidebar_bg"])
        self.stream_label.pack(side=tk.LEFT, padx=5)

        self.token_label = tk.Label(self.status_frame, text="Waiting...",
                                    fg=self.theme.colors["fg"],
                                    bg=self.theme.colors["sidebar_bg"],
                                    anchor=tk.W)
        self.token_label.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)

        self.hw_label = tk.Label(self.status_frame, text="CPU: --% | RAM: --%",
                                 fg=self.theme.colors["fg"],
                                 bg=self.theme.colors["sidebar_bg"])
        self.hw_label.pack(side=tk.LEFT, padx=10)

        self.bench_btn = tk.Button(self.status_frame, text="Bench: OFF",
                                   command=self._toggle_benchmark)
        self.bench_btn.pack(side=tk.RIGHT, padx=10)

    def _refresh_presets(self):
        presets = list_presets()
        self.preset_dropdown['values'] = presets
        if presets:
            self.preset_dropdown.set("")
        else:
            self.preset_dropdown.set("(No presets)")

    def _save_preset_dialog(self):
        name = simpledialog.askstring("Save Preset", "Preset name:",
                                       parent=self)
        if not name:
            return
        ctrl = self.active_session.controller
        save_preset(name, {
            "model": os.path.basename(ctrl.model_path),
            "ngl": ctrl.ngl,
            "ctx_size": ctrl.ctx_size,
            "temp": ctrl.temp,
            "top_p": ctrl.top_p,
            "system_prompt": ctrl.system_prompt,
        })
        self._refresh_presets()
        self.preset_var.set(name)

    def on_preset_select(self, event):
        if self._syncing or not self.active_session:
            return
        name = self.preset_var.get()
        if not name or name == "(No presets)":
            return
        preset = load_preset(name)
        if not preset:
            return
        ctrl = self.active_session.controller
        if "ngl" in preset:
            ctrl.ngl = preset["ngl"]
        if "ctx_size" in preset:
            ctrl.ctx_size = preset["ctx_size"]
        if "temp" in preset:
            ctrl.temp = preset["temp"]
        if "top_p" in preset:
            ctrl.top_p = preset["top_p"]
        if "system_prompt" in preset:
            ctrl.system_prompt = preset["system_prompt"]
        if "model" in preset:
            path = self.model_map.get(preset["model"])
            if path:
                self.active_session.append_chat(f"\n--- Loading preset '{name}' with model {preset['model']}...\n")
                ctrl.model_path = path
            else:
                self.active_session.append_chat(f"\n--- Loading preset '{name}' (model not found, using current)...\n")
        else:
            self.active_session.append_chat(f"\n--- Loading preset '{name}'...\n")
        ctrl.restart()
        self._sync_sidebar_to_active_session()
        tab_idx = self.notebook.index(self.active_session.frame)
        self.notebook.tab(tab_idx, text=os.path.basename(ctrl.model_path)[:25])
        self.active_session.append_chat("--- Preset applied ---\n")

    def on_theme_change(self, event):
        mode_map = {"Auto": "auto", "Light": "light", "Dark": "dark"}
        self.theme.set_mode(mode_map.get(self.theme_var.get(), "auto"))

    def _retheme_all(self, colors):
        self.configure(bg=colors["bg"])
        self.status_frame.config(bg=colors["sidebar_bg"])
        self.stream_label.config(bg=colors["sidebar_bg"])
        self.token_label.config(bg=colors["sidebar_bg"])
        self.hw_label.config(bg=colors["sidebar_bg"])
        for session in self.sessions:
            session.apply_theme(colors)

    def _populate_models(self):
        # Use pathlib.rglob for portable recursive search (POSIX '**' glob
        # is fragile on Windows). Search the user's LM Studio model dir
        # resolved via platform_compat.
        models = sorted(str(p) for p in models_root().rglob("*.gguf"))
        if not models:
            models = [DEFAULT_MODEL_PATH]
        self.model_map = {os.path.basename(m): m for m in models}
        self.model_dropdown['values'] = list(self.model_map.keys())

    def _new_session(self, model_path=None):
        if model_path is None:
            model_path = DEFAULT_MODEL_PATH
        basename = os.path.basename(model_path)
        profile = load_profile(basename)
        session = SessionTab(
            self, self.notebook, self.theme,
            model_path=model_path,
            ngl=profile.get("ngl", 0),
            ctx_size=profile.get("ctx_size", 2048),
            temp=profile.get("temp", 0.7),
            top_p=profile.get("top_p", 0.9),
        )
        self.sessions.append(session)
        self.notebook.select(session.frame)
        self.active_session = session
        self._sync_sidebar_to_active_session()
        if not session.controller.start():
            session.append_chat("\n--- Failed to start llama-cli ---\n")
            self.status_label.config(text="Status: Error", fg="red")

    def _close_active_session(self):
        if not self.active_session or len(self.sessions) <= 1:
            return
        if self.active_session.benchmark_file:
            self.active_session.benchmark_file.close()
        self.active_session.controller.stop_process()
        self.active_session._finalize_turn()
        tab_idx = self.notebook.index(self.active_session.frame)
        self.sessions.remove(self.active_session)
        self.notebook.forget(tab_idx)
        self.active_session = self.sessions[-1]
        self.notebook.select(self.active_session.frame)
        self._sync_sidebar_to_active_session()

    def _sync_sidebar_to_active_session(self):
        if not self.active_session:
            return
        self._syncing = True
        ctrl = self.active_session.controller
        self.ngl_var.set(ctrl.ngl)
        self.ngl_label.config(text=f"Value: {ctrl.ngl}")
        self.temp_var.set(ctrl.temp)
        self.temp_label.config(text=f"{ctrl.temp:.2f}")
        self.top_p_var.set(ctrl.top_p)
        self.top_p_label.config(text=f"{ctrl.top_p:.2f}")
        self.ctx_var.set(ctrl.ctx_size)
        basename = os.path.basename(ctrl.model_path)
        if basename in self.model_map:
            self.model_var.set(basename)
        self.sys_prompt_text.delete(1.0, tk.END)
        shown = self.active_session._base_system_prompt if self.active_session._tool_mode else ctrl.system_prompt
        self.sys_prompt_text.insert(1.0, shown)
        status = "Running" if (ctrl.process and ctrl.process.poll() is None) else "Stopped"
        self.status_label.config(
            text=f"Status: {status}",
            fg=self.theme.colors["status_ok"] if status == "Running" else "red"
        )
        self.bench_btn.config(
            text=f"Bench: {'ON' if self.active_session.benchmark_enabled else 'OFF'}"
        )
        self._update_turn_display()
        self._update_metrics_display()
        self._syncing = False

    def _update_turn_display(self):
        if not self.active_session:
            return
        self.turn_display.config(state="normal")
        self.turn_display.delete(1.0, tk.END)
        items = self.active_session.turn_summary[-10:]
        for line in items:
            self.turn_display.insert(tk.END, line + "\n")
        if self.active_session.turn_speeds:
            curr = sum(self.active_session.turn_speeds) / len(self.active_session.turn_speeds)
            count = len(self.active_session.turn_speeds)
            self.turn_display.insert(tk.END, f"Current: {curr:.1f} t/s ({count})")
        self.turn_display.config(state="disabled")

    def on_tab_changed(self, event):
        if not self.sessions:
            return
        selected = self.notebook.select()
        for session in self.sessions:
            if str(session.frame) == selected:
                self.active_session = session
                break
        self._sync_sidebar_to_active_session()

    def on_ngl_slide(self, value):
        self.ngl_label.config(text=f"Value: {int(float(value))}")

    def apply_ngl(self, event):
        if self._syncing or not self.active_session:
            return
        val = self.ngl_var.get()
        self.active_session.append_chat(f"\n--- Updating GPU offload to {val}...\n")
        self.active_session.controller.set_ngl(val)
        self.active_session.append_chat("--- GPU offload updated ---\n")

    def on_temp_slide(self, value):
        self.temp_label.config(text=f"{float(value):.2f}")

    def apply_temp(self, event):
        if self._syncing or not self.active_session:
            return
        val = self.temp_var.get()
        self.active_session.append_chat(f"\n--- Setting temperature to {val:.2f}...\n")
        self.active_session.controller.set_temp(val)

    def on_top_p_slide(self, value):
        self.top_p_label.config(text=f"{float(value):.2f}")

    def apply_top_p(self, event):
        if self._syncing or not self.active_session:
            return
        val = self.top_p_var.get()
        self.active_session.append_chat(f"\n--- Setting top-p to {val:.2f}...\n")
        self.active_session.controller.set_top_p(val)

    def on_ctx_change(self, event):
        if self._syncing or not self.active_session:
            return
        val = self.ctx_var.get()
        self.active_session.append_chat(f"\n--- Setting context size to {val}...\n")
        self.active_session.controller.set_ctx_size(val)

    def apply_system_prompt(self):
        if not self.active_session:
            return
        prompt = self.sys_prompt_text.get(1.0, tk.END).strip()
        self.active_session._base_system_prompt = prompt
        self.active_session.append_chat("\n--- Applying system prompt...\n")
        if self.active_session._tool_mode:
            combined = self.active_session._get_system_prompt()
            self.active_session.controller.set_system_prompt(combined)
        else:
            self.active_session.controller.set_system_prompt(prompt)
        self.active_session.append_chat("--- System prompt applied ---\n")

    def on_model_change(self, event):
        if self._syncing or not self.active_session:
            return
        selected_name = self.model_var.get()
        path = self.model_map.get(selected_name)
        if not path:
            return
        old_basename = os.path.basename(self.active_session.controller.model_path)
        save_profile(old_basename, {
            "ngl": self.active_session.controller.ngl,
            "ctx_size": self.active_session.controller.ctx_size,
            "temp": self.active_session.controller.temp,
            "top_p": self.active_session.controller.top_p,
        })
        profile = load_profile(selected_name)
        ctrl = self.active_session.controller
        ctrl.ngl = profile.get("ngl", ctrl.ngl)
        ctrl.ctx_size = profile.get("ctx_size", ctrl.ctx_size)
        ctrl.temp = profile.get("temp", ctrl.temp)
        ctrl.top_p = profile.get("top_p", ctrl.top_p)
        self.active_session.append_chat(f"\n--- Switching model to {selected_name}...\n")
        ctrl.set_model(path)
        self._sync_sidebar_to_active_session()
        tab_idx = self.notebook.index(self.active_session.frame)
        self.notebook.tab(tab_idx, text=selected_name[:25])
        save_profile(selected_name, {
            "ngl": ctrl.ngl,
            "ctx_size": ctrl.ctx_size,
            "temp": ctrl.temp,
            "top_p": ctrl.top_p,
        })
        self.active_session.append_chat("--- Model updated ---\n")

    def poll_queues(self):
        for session in self.sessions:
            messages = session.controller.poll_messages()
            for msg in messages:
                if msg == "[LLAMA EXITED]":
                    session.append_chat("\n--- Llama process terminated ---\n")
                    session.append_log("[LLAMA EXITED]")
                    if session is self.active_session:
                        self.status_label.config(text="Status: Stopped", fg="red")
                elif msg.startswith("[META]"):
                    self._parse_meta(session, msg)
                    session.append_log(msg)
                else:
                    session.process_output(msg, session.think_mode.get())
            session.controller.poll_logs()
        self.after(100, self.poll_queues)

    def _parse_meta(self, session, msg):
        parts = msg.split()
        meta_type = parts[1].split("=")[1]
        kv = {}
        for pair in parts[2:]:
            if "=" in pair:
                k, v = pair.split("=", 1)
                kv[k] = v
        speed = kv.get("speed", "--")
        tokens = kv.get("tokens", "0")
        if meta_type == "prompt_eval":
            session.metrics["prompt_speed"] = speed
            session.metrics["tokens"] = tokens
            session.metrics["used_tokens"] = max(session.metrics["used_tokens"], int(tokens))
            session._write_benchmark("prompt_eval", tokens, speed)
        elif meta_type == "eval":
            session.metrics["gen_speed"] = speed
            session.metrics["tokens"] = tokens
            session.metrics["used_tokens"] = max(session.metrics["used_tokens"], int(tokens))
            session._record_gen_speed(speed)
            session._mark_generating()
            session._write_benchmark("gen", tokens, speed)
        elif meta_type == "sample":
            session.metrics["sample_speed"] = speed
            session.metrics["sample_runs"] = tokens
            session._write_benchmark("sample", tokens, speed)
        elif meta_type == "load":
            for k, v in kv.items():
                if k in session.metrics:
                    session.metrics[k] = v
        if session is self.active_session:
            self._update_metrics_display()
            self._update_turn_display()

    def _update_metrics_display(self):
        if not self.active_session:
            return
        m = self.active_session.metrics
        gen = m.get("gen_speed", "--")
        prompt = m.get("prompt_speed", "--")
        sample = m.get("sample_speed", "--")
        tokens = m.get("tokens", "0")
        used = m.get("used_tokens", 0)
        ctx = self.active_session.controller.ctx_size
        parts = []
        if prompt != "--":
            parts.append(f"P: {prompt} t/s")
        if gen != "--":
            parts.append(f"G: {gen} t/s")
        if sample != "--":
            parts.append(f"S: {sample} t/s")
        parts.append(f"Tok: {used}/{ctx}")
        text = " | ".join(parts) if parts else "Waiting..."
        try:
            g = float(gen)
            if g > 50:
                fg = "#4ec9b0"
            elif g > 20:
                fg = "#dcdcaa"
            else:
                fg = "#f44747"
        except (ValueError, TypeError):
            fg = self.theme.colors["fg"]
        self.token_label.config(text=text, fg=fg)

    def _update_stream_indicator(self):
        session = self.active_session
        if session and session._gen_active:
            self.stream_label.config(text="\u25cf Generating", fg="#4ec9b0")
        else:
            self.stream_label.config(text="\u25cb Idle", fg="#888888")
        self.after(500, self._update_stream_indicator)

    def _poll_hardware(self):
        if HAS_PSUTIL:
            cpu = psutil.cpu_percent(interval=0)
            ram = psutil.virtual_memory().percent
            gpu_str = ""
            try:
                out = subprocess.check_output(
                    nvidia_smi_cmd() + [
                        "--query-gpu=utilization.gpu,memory.used,memory.total",
                        "--format=csv,noheader,nounits",
                    ],
                    text=True, timeout=2
                ).strip()
                gpu_util, mem_used, mem_total = out.split(", ")
                gpu_str = f" | GPU: {gpu_util}% ({mem_used}/{mem_total} MB)"
            except Exception:
                pass
            self.hw_label.config(text=f"CPU: {cpu}% | RAM: {ram}%{gpu_str}")
        self.after(2000, self._poll_hardware)

    def _toggle_benchmark(self):
        session = self.active_session
        if not session:
            return
        session.benchmark_enabled = not session.benchmark_enabled
        if session.benchmark_enabled:
            os.makedirs(BENCHMARK_DIR, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            model = os.path.basename(session.controller.model_path).replace(".gguf", "")
            path = os.path.join(BENCHMARK_DIR, f"{model}_{ts}.csv")
            session.benchmark_file = open(path, "w", newline="")
            session.benchmark_writer = csv.writer(session.benchmark_file)
            session.benchmark_writer.writerow(
                ["timestamp", "model", "type", "tokens", "speed_tps", "ctx", "ngl"]
            )
            session.append_chat(f"\n--- Benchmark logging to {os.path.basename(path)} ---\n")
        else:
            if session.benchmark_file:
                session.benchmark_file.close()
                session.benchmark_file = None
                session.benchmark_writer = None
            session.append_chat("\n--- Benchmark logging stopped ---\n")
        self.bench_btn.config(text=f"Bench: {'ON' if session.benchmark_enabled else 'OFF'}")

    def _setup_tray(self):
        icon = pystray.Icon(
            "llama-gui",
            icon=LlamaController.create_icon(),
            title="Llama-cpp Chat",
            menu=pystray.Menu(
                item("Show", self.show_window),
                item("Hide", self.hide_window),
                item("Quit", self.quit_app)
            )
        )
        icon.run()

    def show_window(self):
        self.deiconify()
        self.after(0, self.focus_force)

    def hide_window(self):
        self.withdraw()

    def focus_force(self):
        self.focus_set()
        self.lift()

    def quit_app(self):
        self.after(0, self.on_close)

    def on_close(self):
        for session in self.sessions:
            if session.benchmark_file:
                session.benchmark_file.close()
            session.controller.stop_process()
        self.destroy()


if __name__ == "__main__":
    app = LlamaChatGUI()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
