# Agent Handover: Llama-cpp Chat GUI Pro

## 🎯 Project Overview
This project is a Python/Tkinter wrapper around the `llama-cli` binary from `llama.cpp`. It provides a graphical interface for chat interactions, model management, and hardware configuration.

## 🛠 Technical Architecture

### 1. `llama_controller.py` (The Engine)
The `LlamaController` class manages the lifecycle of the `llama-cli` subprocess.
- **Process Handling**: Uses `subprocess.Popen` with `stdin=PIPE` and `stdout=PIPE`.
- **Async I/O**: Implements a reader thread that pushes lines into two separate `queue.Queue` objects:
    - `msg_queue`: Used for the main chat display.
    - `log_queue`: Used for the system log viewer.
- **Configuration**: Methods like `set_model()` and `set_ngl()` update parameters and trigger a `restart()`, which kills the existing process and spawns a new one with updated flags.

### 2. `llama_gui.py` (The Interface)
The `LlamaChatGUI` class inherits from `tk.Tk` and handles the presentation layer.
- **Theme System**: The `ThemeManager` class detects GTK dark/light mode via `gsettings` and maps them to a color palette used across all widgets.
- **Main Loop**: Uses `self.after(100, self.poll_queues)` to periodically check the controller's queues and update the UI without blocking the main thread.
- **System Tray**: Integrates `pystray` in a background daemon thread to provide "Show/Hide/Quit" functionality.

## 🚀 Guidance for New Features

### Adding a New Configuration Flag
If you want to add a new `llama-cli` flag (e.g., `-t` for threads or `--temp` for temperature):
1. **Update `LlamaController.__init__`**: Add the parameter to the constructor.
2. **Update `LlamaController.start`**: Include the new parameter in the `cmd` list.
3. **Add a Setter**: Create a method `set_thread_count(self, val)` that updates the value and calls `self.restart()`.
4. **Update GUI**: Add a corresponding widget (Slider/Entry) in `llama_gui.py` and bind it to the setter.

### Implementing New UI Panels
The UI uses a `main_container` with a `sidebar` (left) and `chat_area` (right). 
- To add a new settings panel: Add widgets to the `sidebar` frame.
- To add a new data display: Add a `scrolledtext` widget to the `chat_area` (similar to `log_display`).

### Extending History/Persistence
The current implementation writes to simple Markdown files. To implement a database (e.g., SQLite), modify the `_log_to_history` method in `LlamaChatGUI` and create a new persistence module.

## ⚠️ Critical Pitfalls
- **Subprocess Blocking**: Never call `process.stdout.read()` or `process.wait()` on the main GUI thread. Always use the `queue` pattern.
- **Environment Mismatches**: The app relies on `pystray` and `Pillow`. Ensure these are installed in the specific Python environment used to launch the app.
- **Process Leaks**: Always ensure `controller.stop_process()` is called during the `on_close` event to prevent orphaned `llama-cli` zombies.
