# core/state_manager.py

import os
import threading
import time
from enum import Enum
from audio.tts import TextToSpeech
from core.llm_parser import LocalCommandParser
from moduls.desktop_mode.system_ctrl import SystemController


class VeloMode(Enum):
    GAME = "Game Mode"
    DESKTOP = "Desktop Mode"
    TEST = "Test Mode"


class StateManager:
    def __init__(self, ui_callback=None, exit_callback=None):
        self.current_mode = VeloMode.DESKTOP
        self.ui_callback = ui_callback
        self.exit_callback = exit_callback
        self.tts = TextToSpeech()
        self.system_ctrl = SystemController()
        self.llm_parser = LocalCommandParser(model_name="qwen2.5:1.5b")

    def set_mode(self, new_mode) -> str:
        target_mode = None

        if isinstance(new_mode, str):
            clean_str = new_mode.strip().lower()
            for mode in VeloMode:
                if (clean_str in mode.value.lower()) or (clean_str in mode.name.lower()):
                    target_mode = mode
                    break
        elif isinstance(new_mode, VeloMode):
            target_mode = new_mode

        if not target_mode:
            msg = f"Error: Invalid mode -> '{new_mode}'"
            self._log(msg)
            return msg

        if self.current_mode == target_mode:
            msg = f"[{target_mode.value}] is already active."
            self._log(msg)
            return msg

        old_mode = self.current_mode
        self.current_mode = target_mode

        msg = f"Mode Changed: {old_mode.value} ---> [{self.current_mode.value}]"
        self._log(msg)

        self.tts.speak(f"{self.current_mode.value} activated.")
        self._on_mode_changed(old_mode, self.current_mode)
        return msg

    def _on_mode_changed(self, old_mode: VeloMode, new_mode: VeloMode):
        if new_mode == VeloMode.GAME:
            self._log("[Game Mode] Telemetry services online.")
        elif new_mode == VeloMode.DESKTOP:
            self._log("[Desktop Mode] System controller and Local LLM ready.")
        elif new_mode == VeloMode.TEST:
            self._log("[Test Mode] Sandbox environment active.")

    def process_command(self, command_text: str) -> str:
        cmd = command_text.strip().lower()

        # 1. KAPANIŞ KOMUTLARI (Quit, Bye, Kill yourself vb.)
        if any(k in cmd for k in ["quit", "bye bye", "bye", "exit", "kill yourself", "close velo", "goodbye"]):
            response = "Goodbye sir. Shutting down system."
            self._log(f"[{self.current_mode.value}]: {response}")
            self.tts.speak(response)

            def shutdown():
                time.sleep(1.5)
                if self.exit_callback:
                    self.exit_callback()
                else:
                    os._exit(0)

            threading.Thread(target=shutdown, daemon=True).start()
            return response

        # 2. MUTE / UNMUTE KOMUTLARI
        elif any(k in cmd for k in ["unmute", "sound on", "enable audio"]):
            self.tts.is_muted = False
            response = "Audio unmuted, sir."
            self._log(f"[{self.current_mode.value}]: {response}")
            self.tts.speak(response)
            return response

        elif any(k in cmd for k in ["mute", "be quiet", "silence", "sound off", "disable audio"]):
            response = "Muting audio response."
            self.tts.speak(response)
            self.tts.is_muted = True
            self._log(f"[{self.current_mode.value}]: {response}")
            return response

        # 3. MOD DEĞİŞTİRME KOMUTLARI
        if any(k in cmd for k in ["game mode", "switch to game", "gaming mode"]):
            return self.set_mode(VeloMode.GAME)
        elif any(k in cmd for k in ["desktop mode", "switch to desktop", "normal mode"]):
            return self.set_mode(VeloMode.DESKTOP)
        elif any(k in cmd for k in ["test mode", "switch to test", "sandbox"]):
            return self.set_mode(VeloMode.TEST)

        # 4. MASAÜSTÜ MODU İŞLEYİCİSİ (Hibrit Yapı: Hızlı Kural -> Yerel LLM)
        if self.current_mode == VeloMode.DESKTOP:
            # 1. Aşama: Hızlı Kural & Sabit Komut Kontrolü (0 ms gecikme)
            result = self.system_ctrl.handle_command(cmd)

            # 2. Aşama: Eşleşme yoksa Yerel LLM (Ollama) ile doğal dil analizi
            if not result:
                self._log("[System] Analyzing natural command via Local LLM...")
                parsed_intent = self.llm_parser.parse(command_text)
                result = self.system_ctrl.execute_llm_intent(parsed_intent)

            if result:
                response = result
            else:
                response = f"I'm not sure how to help with '{command_text}', sir."

        # 5. OYUN VEYA TEST MODU İŞLEYİCİLERİ
        elif self.current_mode == VeloMode.GAME:
            response = f"Game mode command received: '{command_text}'"
        else:
            response = f"Test mode command received: '{command_text}'"

        self._log(f"[{self.current_mode.value}]: {response}")
        self.tts.speak(response)
        return response

    def _log(self, message: str):
        if self.ui_callback:
            self.ui_callback(message)