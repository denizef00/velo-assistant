# core/state_manager.py

import datetime
import os
import threading
import time
from enum import Enum
from audio.tts import TextToSpeech
from core.llm_parser import LocalCommandParser
from moduls.desktop_mode.system_ctrl import SystemController


class JarvisMode(Enum):
    GAME = "Game Mode"
    DESKTOP = "Desktop Mode"
    TEST = "Test Mode"


class StateManager:
    def __init__(self, ui_callback=None, exit_callback=None, mute_ui_callback=None):
        self.current_mode = JarvisMode.DESKTOP
        self.ui_callback = ui_callback
        self.exit_callback = exit_callback
        self.tts = TextToSpeech(on_mute_change=mute_ui_callback)
        self.system_ctrl = SystemController()
        self.llm_parser = LocalCommandParser(model_name="qwen2.5:1.5b")

    def greet_user(self):
        """Uygulama açılışında saate göre selam verir ve gününü sorar."""
        hour = datetime.datetime.now().hour
        if 5 <= hour < 12:
            greeting = "Good morning! Velo is online. How is your morning going?"
        elif 12 <= hour < 18:
            greeting = "Good afternoon! Velo is ready. How is your day going so far?"
        else:
            greeting = "Good evening! Velo is online. How was your day?"

        self._log(f"[Velo]: {greeting}")
        self.tts.speak(greeting)

    def set_mode(self, new_mode) -> str:
        target_mode = None

        if isinstance(new_mode, str):
            clean_str = new_mode.strip().lower()
            for mode in JarvisMode:
                if (clean_str in mode.value.lower()) or (clean_str in mode.name.lower()):
                    target_mode = mode
                    break
        elif isinstance(new_mode, JarvisMode):
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
        return msg

    def process_command(self, command_text: str) -> str:
        cmd = command_text.strip().lower()

        # 1. KAPANIŞ KOMUTLARI
        if any(k in cmd for k in ["quit", "bye bye", "bye", "exit", "kill yourself", "close velo", "goodbye"]):
            response = "Goodbye. Shutting down Velo."
            self._log(f"[{self.current_mode.value}]: {response}")
            self.tts.speak(response)

            def shutdown():
                time.sleep(1.4)
                if self.exit_callback:
                    self.exit_callback()
                else:
                    os._exit(0)

            threading.Thread(target=shutdown, daemon=True).start()
            return response

        # 2. VELO SESİ AÇMA / KAPATMA
        elif any(k in cmd for k in ["unmute", "sound on", "enable audio", "speak again"]):
            self.tts.set_mute(False)
            response = "Voice output enabled."
            self._log(f"[{self.current_mode.value}]: {response}")
            self.tts.speak(response)
            return response

        elif any(k in cmd for k in ["mute", "be quiet", "silence", "sound off", "disable audio"]):
            response = "Voice output muted."
            self._log(f"[{self.current_mode.value}]: {response}")
            self.tts.set_mute(True)
            return response

        # 3. MOD DEĞİŞTİRME
        if any(k in cmd for k in ["game mode", "switch to game", "gaming mode"]):
            return self.set_mode(JarvisMode.GAME)
        elif any(k in cmd for k in ["desktop mode", "switch to desktop", "normal mode"]):
            return self.set_mode(JarvisMode.DESKTOP)
        elif any(k in cmd for k in ["test mode", "switch to test", "sandbox"]):
            return self.set_mode(JarvisMode.TEST)

        # 4. MASAÜSTÜ MODU (Hızlı Kural -> Yerel LLM)
        if self.current_mode == JarvisMode.DESKTOP:
            result = self.system_ctrl.handle_command(cmd)

            if not result:
                parsed_intent = self.llm_parser.parse(command_text)
                result = self.system_ctrl.execute_llm_intent(parsed_intent)

            response = result if result else f"I'm not sure how to help with '{command_text}'."

        elif self.current_mode == JarvisMode.GAME:
            response = f"Game mode command received: '{command_text}'"
        else:
            response = f"Test mode command received: '{command_text}'"

        self._log(f"[{self.current_mode.value}]: {response}")
        self.tts.speak(response)
        return response

    def _log(self, message: str):
        if self.ui_callback:
            self.ui_callback(message)