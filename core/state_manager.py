# core/state_manager.py

import datetime
import os
import threading
import time
from enum import Enum
from typing import Optional, Union
from audio.tts import TextToSpeech
from core.llm_parser import LocalCommandParser
from modules.desktop_mode.routine_ctrl import RoutineController
from modules.desktop_mode.system_ctrl import SystemController
from modules.game_mode.game_ctrl import GameController
from modules.dev_mode.dev_ctrl import DevController


class VeloMode(Enum):
    GAME = "Game Mode"
    DESKTOP = "Desktop Mode"
    DEV = "Dev Mode"
    TEST = "Dev Mode"  # Geriye dönük uyumluluk alias'ı


class StateManager:
    def __init__(self, ui_callback=None, exit_callback=None, mute_ui_callback=None):
        self.current_mode = VeloMode.DESKTOP
        self.ui_callback = ui_callback
        self.exit_callback = exit_callback
        self.tts = TextToSpeech(on_mute_change=mute_ui_callback)
        self.llm_parser = LocalCommandParser(model_name="qwen2.5:1.5b")

        # Mod Kontrolcüleri
        self.desktop_ctrl = SystemController()
        self.game_ctrl = GameController(llm_parser=self.llm_parser)
        self.dev_ctrl = DevController(llm_parser=self.llm_parser)

        # Geriye dönük uyumluluk için referans
        self.system_ctrl = self.desktop_ctrl
        self.routine_ctrl = RoutineController(state_manager=self)
        self.routine_ctrl.start_context_watcher()
        
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
        # Karşılama mesajını kayan pencere hafızasına kaydet
        self.llm_parser.add_history("", greeting)

    def set_mode(self, new_mode: Union[str, VeloMode]) -> str:
        target_mode = None

        if isinstance(new_mode, str):
            clean_str = new_mode.strip().lower()
            if any(k in clean_str for k in ["game", "gaming"]):
                target_mode = VeloMode.GAME
            elif any(k in clean_str for k in ["desktop", "normal"]):
                target_mode = VeloMode.DESKTOP
            elif any(k in clean_str for k in ["dev", "work", "code", "coding", "developer", "test", "sandbox"]):
                target_mode = VeloMode.DEV
            else:
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
        return msg

    def process_command(self, command_text: str) -> str:
        cmd = command_text.strip().lower().rstrip(".,!?;:")
        # 0. SESSİZ BİLGİ VE YARDIM KOMUTLARI (TTS kullanmaz)
        if cmd in ["info", "commands", "command list", "show commands"]:
            info_text = self._get_mode_info()
            self._log(info_text)
            return info_text

        elif cmd in ["help", "detailed help", "guide", "manual"]:
            help_text = self._get_detailed_help()
            self._log(help_text)
            return help_text
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

        # 2. VELO SESİ AÇMA / KAPATMA (TTS Mute)
        elif any(k in cmd for k in ["unmute", "sound on", "enable audio", "speak again"]):
            self.tts.set_mute(False)
            response = "Voice output enabled."
            self._log(f"[{self.current_mode.value}]: {response}")
            self.tts.speak(response)
            return response

        elif any(k in cmd for k in ["mute", "be quiet", "silence", "sound off", "disable audio"]):
            self.tts.set_mute(True)
            response = "Voice output muted."
            self._log(f"[{self.current_mode.value}]: {response}")
            self.tts.speak(response)
            return response

        # 3. MOD DEĞİŞTİRME KOMUTLARI
        if any(k in cmd for k in ["game mode", "switch to game", "gaming mode"]):
            return self.set_mode(VeloMode.GAME)
        elif any(k in cmd for k in ["desktop mode", "switch to desktop", "normal mode"]):
            return self.set_mode(VeloMode.DESKTOP)
        elif any(k in cmd for k in [
            "dev mode", "switch to dev", "developer mode",
            "work mode", "coding mode", "test mode", "sandbox"
        ]):
            return self.set_mode(VeloMode.DEV)
        # 3.5 ÖZEL KOMUTLAR VE OTOMATİK RUTİNLER (Tüm modlarda 0ms öncelikli)
        routine_response = self.routine_ctrl.handle_command(cmd)
        if routine_response:
            self._log(f"[Routine]: {routine_response}")
            self.tts.speak(routine_response)
            return routine_response
        # 4. AKTİF MODA GÖRE DİNAMİK YÖNLENDİRME (Kural Motoru -> Yerel LLM)
        if self.current_mode == VeloMode.GAME:
            controller = self.game_ctrl
        elif self.current_mode == VeloMode.DEV:
            controller = self.dev_ctrl
        else:
            controller = self.desktop_ctrl

        
        # Önce sıfır gecikmeli kural motorunu dene
        result = controller.handle_command(cmd)

        # Kural eşleşmediyse yerel LLM (Qwen2.5 1.5B) üzerinden yorumla
        if not result:
            parsed_intent = self.llm_parser.parse(command_text)
            result = controller.execute_llm_intent(parsed_intent)

        response = result if result else f"I'm not sure how to help with '{command_text}'."

        # Kısa vadeli konuşma hafızasına kaydet
        self.llm_parser.add_history(command_text, response)

        self._log(f"[{self.current_mode.value}]: {response}")
        self.tts.speak(response)
        return response

    def _log(self, message: str):
        if self.ui_callback:
            self.ui_callback(message)
    def _get_mode_info(self) -> str:
        custom_triggers = list(self.routine_ctrl.config.get("single_actions", {}).keys())
        routine_triggers = list(self.routine_ctrl.config.get("routines", {}).keys())
        custom_str = ", ".join(custom_triggers + routine_triggers) if (custom_triggers or routine_triggers) else "None"

        if self.current_mode == VeloMode.DESKTOP:
            mode_cmds = (
                "• App & Web: open <app>, play <song/video>, search <query>\n"
                "• Media: volume up/down, pause, resume, next, skip forward, rewind\n"
                "• System: system status, refresh apps, mute/unmute, quit"
            )
        elif self.current_mode == VeloMode.GAME:
            mode_cmds = (
                "• Sim Racing: check telemetry, fuel status, tire temp, start racing\n"
                "• Hardware: system status, hardware temp, CPU/RAM usage\n"
                "• Media: volume up/down, pause, resume, next, skip forward, rewind"
            )
        else:  # DEV MODE
            mode_cmds = (
                "• Workspace: start coding, open dev workspace\n"
                "• Clipboard AI: explain what I copied, read clipboard, debug this error\n"
                "• Media & Apps: open <app>, play <music>, volume controls"
            )

        return (
            f"\n--- [{self.current_mode.value.upper()} - COMMAND LIST] ---\n"
            f"{mode_cmds}\n"
            f"• Custom & Routines: {custom_str}\n"
            f"• Navigation: game mode | desktop mode | dev mode | help\n"
            f"-------------------------------------------"
        )

    def _get_detailed_help(self) -> str:
        return (
            "\n================ VELO ASSISTANT HELP ================\n"
            "1. WAKE WORDS & HOTKEYS:\n"
            "   - Wake Words : 'Velo', 'Hey Velo', 'Service'\n"
            "   - Ctrl + R   : Instant Hot-Reload (preserves chat history)\n"
            "   - Close (X)  : Minimizes Velo to Windows System Tray\n\n"
            "2. DESKTOP MODE COMMANDS:\n"
            "   - 'open <app>'        : Launches apps/sites (e.g., 'open spotify', 'open vscode')\n"
            "   - 'play <query>'      : Plays top matching video/song on YouTube\n"
            "   - 'skip forward'      : Skips 5 seconds ahead in active video\n"
            "   - 'rewind'            : Rewinds 5 seconds back in active video\n"
            "   - 'volume up / down'  : Adjusts Windows master volume\n"
            "   - 'system status'     : Reports live CPU and RAM usage\n\n"
            "3. GAME MODE COMMANDS:\n"
            "   - 'start racing'      : Launches Content Manager + Discord together\n"
            "   - 'check telemetry'   : Reads live Assetto Corsa fuel & tire temps\n"
            "   - 'hardware temp'     : Checks system CPU/thermal status\n\n"
            "4. DEV MODE COMMANDS:\n"
            "   - 'start coding'      : Opens Visual Studio Code workspace\n"
            "   - 'explain what I copied' : Summarizes copied code/error from clipboard\n\n"
            "5. CUSTOM ROUTINES (config/custom_commands.json):\n"
            "   - 'play my playlist'  : Opens your configured Spotify playlist URI\n"
            "   - 'focus session'     : Switches to Dev Mode + VS Code + Lo-fi music\n"
            "   - 'night drive'       : Switches to Game Mode + Content Manager + Discord\n"
            "====================================================="
        )
