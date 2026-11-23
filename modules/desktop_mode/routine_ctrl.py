# modules/desktop_mode/routine_ctrl.py

import json
import os
import threading
import time
import webbrowser
import psutil


class RoutineController:
    def __init__(self, state_manager, config_path: str = "config/custom_commands.json"):
        self.state_manager = state_manager
        self.config_path = config_path
        self.config = self._load_config()
        self._last_auto_mode = None
        self._watcher_running = False

    def _load_config(self) -> dict:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[RoutineConfig Error]: {e}")
        return {"single_actions": {}, "routines": {}, "auto_context": {}}

    def reload_config(self):
        self.config = self._load_config()

    def handle_command(self, command: str) -> str:
        cmd = command.lower().strip().rstrip(".,!?")

        # 1. Tekil Özel Komutlar (Spotify URI, URL, Uygulama)
        single_actions = self.config.get("single_actions", {})
        for trigger, data in single_actions.items():
            if trigger.lower() in cmd:
                action_type = data.get("type")
                target = data.get("target")
                if action_type == "uri" and target:
                    os.startfile(target)
                elif action_type == "url" and target:
                    webbrowser.open(target)
                elif action_type == "app" and target:
                    self.state_manager.desktop_ctrl.app_launcher.launch(target)
                return data.get("response", f"Executed {trigger}.")

        # 2. Çoklu Adımlı Rutinler (Makrolar)
        routines = self.config.get("routines", {})
        for trigger, data in routines.items():
            if trigger.lower() in cmd:
                steps = data.get("steps", [])
                threading.Thread(target=self._execute_steps, args=(steps,), daemon=True).start()
                return data.get("response", f"Running {trigger} routine.")

        return None

    def _execute_steps(self, steps: list):
        for step in steps:
            action = step.get("action")
            val = step.get("value", "")

            if action == "mode":
                self.state_manager.set_mode(val)
            elif action == "launch":
                self.state_manager.desktop_ctrl.app_launcher.launch(val)
            elif action == "play_youtube":
                self.state_manager.desktop_ctrl.play_youtube(val)
            elif action == "uri":
                os.startfile(val)

            time.sleep(0.4)

    # --- Otomatik Bağlam Algılama (Auto-Context Watcher) ---
    def start_context_watcher(self):
        if self._watcher_running:
            return
        self._watcher_running = True
        threading.Thread(target=self._watch_processes, daemon=True).start()

    def _watch_processes(self):
        while self._watcher_running:
            try:
                auto_map = self.config.get("auto_context", {})
                if auto_map:
                    running_names = {p.info["name"] for p in psutil.process_iter(["name"]) if p.info["name"]}
                    detected_mode = None

                    for proc_name, target_mode in auto_map.items():
                        if proc_name in running_names:
                            detected_mode = target_mode
                            break

                    # Yeni bir hedef uygulama açıldıysa modu otomatik değiştir
                    if detected_mode and detected_mode != self._last_auto_mode:
                        self._last_auto_mode = detected_mode
                        self.state_manager.set_mode(detected_mode)
                    elif not detected_mode:
                        self._last_auto_mode = None
            except Exception:
                pass

            time.sleep(4.0)  # CPU yormamak için 4 saniyede bir kontrol