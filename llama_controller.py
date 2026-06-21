import subprocess
import threading
import queue
import os
import json
import re
import logging
from PIL import Image, ImageDraw

PROFILES_PATH = os.path.expanduser("~/.config/llama-chat-profiles.json")
PRESETS_PATH = os.path.expanduser("~/.config/llama-chat-presets.json")

TIMING_RE = re.compile(
    r"(prompt eval|eval)\s+time.*?(\d+)\s+tokens.*?(\d+\.?\d*)\s+tokens per second",
    re.IGNORECASE | re.DOTALL
)
CTX_RE = re.compile(r"n_ctx\s*=\s*(\d+)")
OFFLOAD_RE = re.compile(r"offload\s+(\d+)\s+layers")
SAMPLE_RE = re.compile(
    r"sample\s+time.*?(\d+)\s+runs\s*.*?(\d+\.?\d*)\s+tokens per second",
    re.IGNORECASE | re.DOTALL
)


def load_profile(model_basename):
    try:
        with open(PROFILES_PATH) as f:
            return json.load(f).get(model_basename, {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_profile(model_basename, params):
    try:
        with open(PROFILES_PATH) as f:
            profiles = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        profiles = {}
    profiles[model_basename] = params
    with open(PROFILES_PATH, "w") as f:
        json.dump(profiles, f, indent=2)


def list_presets():
    try:
        with open(PRESETS_PATH) as f:
            return sorted(json.load(f).keys())
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def load_preset(name):
    try:
        with open(PRESETS_PATH) as f:
            return json.load(f).get(name, {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_preset(name, params):
    try:
        with open(PRESETS_PATH) as f:
            presets = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        presets = {}
    presets[name] = params
    with open(PRESETS_PATH, "w") as f:
        json.dump(presets, f, indent=2)
    return True

def delete_preset(name):
    try:
        with open(PRESETS_PATH) as f:
            presets = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return False
    if name in presets:
        del presets[name]
        with open(PRESETS_PATH, "w") as f:
            json.dump(presets, f, indent=2)
        return True
    return False


class LlamaController:
    def __init__(self, model_path, ngl=0, ctx_size=2048, temp=0.7, top_p=0.9, system_prompt=""):
        self.model_path = model_path
        self.ngl = ngl
        self.ctx_size = ctx_size
        self.temp = temp
        self.top_p = top_p
        self.system_prompt = system_prompt
        self.process = None
        self.msg_queue = queue.Queue()
        self.log_queue = queue.Queue()
        self.stop_event = threading.Event()

    def start(self):
        self.stop_process()
        self.stop_event.clear()

        cmd = [
            "llama-cli",
            "-m", self.model_path,
            "-ngl", str(self.ngl),
            "-c", str(self.ctx_size),
            "--temp", str(self.temp),
            "--top-p", str(self.top_p),
            "--conversation"
        ]

        if self.system_prompt:
            cmd += ["-p", self.system_prompt]

        try:
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            threading.Thread(target=self._read_stdout, daemon=True).start()
            return True
        except FileNotFoundError:
            logging.error("llama-cli binary not found in PATH")
            return False
        except Exception as e:
            logging.error(f"Failed to start llama-cli: {e}")
            return False

    def _read_stdout(self):
        if not self.process or not self.process.stdout:
            return

        for line in self.process.stdout:
            if self.stop_event.is_set():
                break
            self.msg_queue.put(line.rstrip("\n"))
            self.log_queue.put(line.rstrip("\n"))

            m = TIMING_RE.search(line)
            if m:
                timing_type = m.group(1).strip().lower().replace(" ", "_")
                tokens = m.group(2)
                speed = m.group(3)
                meta = f"[META] type={timing_type} tokens={tokens} speed={speed}"
                self.msg_queue.put(meta)
                self.log_queue.put(meta)

            m2 = CTX_RE.search(line)
            if m2:
                self.msg_queue.put(f"[META] type=load ctx={m2.group(1)}")
                self.log_queue.put(f"[META] type=load ctx={m2.group(1)}")

            m3 = OFFLOAD_RE.search(line)
            if m3:
                self.msg_queue.put(f"[META] type=load offload={m3.group(1)}")
                self.log_queue.put(f"[META] type=load offload={m3.group(1)}")

            m4 = SAMPLE_RE.search(line)
            if m4:
                meta = f"[META] type=sample tokens={m4.group(1)} speed={m4.group(2)}"
                self.msg_queue.put(meta)
                self.log_queue.put(meta)

        self.msg_queue.put("[LLAMA EXITED]")
        self.log_queue.put("[LLAMA EXITED]")

    def send(self, text):
        if not self.process or self.process.poll() is not None:
            return False
        try:
            self.process.stdin.write(text + "\n")
            self.process.stdin.flush()
            return True
        except (BrokenPipeError, OSError):
            return False

    def stop_generation(self):
        if self.process and self.process.poll() is None:
            self.process.stdin.write("\x03\n")
            self.process.stdin.flush()

    def set_model(self, path):
        if self.model_path != path:
            self.model_path = path
            self.restart()

    def set_ngl(self, value):
        if self.ngl != value:
            self.ngl = value
            self.restart()

    def set_ctx_size(self, value):
        if self.ctx_size != value:
            self.ctx_size = value
            self.restart()

    def set_temp(self, value):
        if abs(self.temp - value) > 0.01:
            self.temp = value
            self.restart()

    def set_top_p(self, value):
        if abs(self.top_p - value) > 0.01:
            self.top_p = value
            self.restart()

    def set_system_prompt(self, prompt):
        if self.system_prompt != prompt:
            self.system_prompt = prompt
            self.restart()

    def restart(self):
        self.start()

    def stop_process(self):
        self.stop_event.set()
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                if self.process:
                    self.process.kill()
            self.process = None

    def poll_messages(self):
        messages = []
        try:
            while True:
                messages.append(self.msg_queue.get_nowait())
        except queue.Empty:
            pass
        return messages

    def poll_logs(self):
        logs = []
        try:
            while True:
                logs.append(self.log_queue.get_nowait())
        except queue.Empty:
            pass
        return logs

    @staticmethod
    def create_icon():
        image = Image.new("RGB", (64, 64), (50, 150, 250))
        dc = ImageDraw.Draw(image)
        dc.rectangle([16, 16, 48, 48], fill=(255, 255, 255))
        return image
