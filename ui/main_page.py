# ui/main_page.py

import datetime
import os
import re
import threading
import time
import pygame
import customtkinter as ctk
import importlib
import audio.stt
import audio.tts
import core.llm_parser
import core.state_manager
import modules.desktop_mode.app_launcher
import modules.desktop_mode.media_ctrl
import modules.desktop_mode.system_ctrl
import modules.game_mode.ac_telemetry
import modules.game_mode.game_ctrl
import modules.dev_mode.dev_ctrl
from config.theme import THEME_CONFIG
from core.state_manager import StateManager, VeloMode
from audio.stt import SpeechToText
from ui.tray_manager import TrayManager

ctk.set_appearance_mode(THEME_CONFIG["appearance_mode"])
ctk.set_default_color_theme(THEME_CONFIG["color_theme"])


class VeloUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Velo - Control Center")
        self.geometry("700x530")
        self.minsize(580, 430)
        self.configure(fg_color=THEME_CONFIG["bg_dark"])

        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.stt = None
        self.is_hands_free_active = False

        self._build_top_bar()
        self._build_terminal()

        self.state_manager = StateManager(
            ui_callback=self.write_to_terminal,
            exit_callback=self.quit_app,
            mute_ui_callback=self._sync_voice_button
        )
        self.bind("<Control-r>", lambda event: self.hot_reload())
        self.tray = TrayManager(
            on_show=self.restore_from_tray,
            on_toggle_mic=lambda: self.after(0, self.toggle_hands_free),
            on_quit=lambda: self.after(0, self.quit_app),
        )
        self.tray.start()

        # Penceredeki X tuşuna basınca kapatmak yerine sağ alt köşeye küçült
        self.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)    
        # Açılışta otomatik mikrofon başlatma ve gününü sorma
        threading.Thread(target=self._boot_sequence, daemon=True).start()

    def _boot_sequence(self):
        self.write_to_terminal("Initializing Velo audio & intelligence engines...")
        self.stt = SpeechToText(model_size="base.en", device_index=2)
        self.is_hands_free_active = True
        self.after(0, lambda: self.btn_mic.configure(text="🎙️ Mic: ON", fg_color="#2B8A3E", hover_color="#237032"))
        self.state_manager.greet_user()
        self._hands_free_loop()

    def _build_top_bar(self):
        self.top_frame = ctk.CTkFrame(self, fg_color=THEME_CONFIG["card_bg"], corner_radius=12)
        self.top_frame.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="ew")
        self.top_frame.grid_columnconfigure((0, 1, 2), weight=1)

        btn_game = THEME_CONFIG["buttons"]["game"]
        self.btn_game = ctk.CTkButton(
            self.top_frame, text="🎮 GAME MODE", font=THEME_CONFIG["fonts"]["button"],
            fg_color=btn_game["fg"], hover_color=btn_game["hover"], text_color=btn_game["text"],
            height=40, corner_radius=8, command=lambda: self.on_mode_button_click(VeloMode.GAME)
        )
        self.btn_game.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        btn_desk = THEME_CONFIG["buttons"]["desktop"]
        self.btn_desktop = ctk.CTkButton(
            self.top_frame, text="💻 DESKTOP MODE", font=THEME_CONFIG["fonts"]["button"],
            fg_color=btn_desk["fg"], hover_color=btn_desk["hover"], text_color=btn_desk["text"],
            height=40, corner_radius=8, command=lambda: self.on_mode_button_click(VeloMode.DESKTOP)
        )
        self.btn_desktop.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        btn_dev = THEME_CONFIG["buttons"].get("dev", THEME_CONFIG["buttons"].get("test"))
        self.btn_dev = ctk.CTkButton(
            self.top_frame, text="🛠️ DEV MODE", font=THEME_CONFIG["fonts"]["button"],
            fg_color=btn_dev["fg"], hover_color=btn_dev["hover"], text_color=btn_dev["text"],
            height=40, corner_radius=8, command=lambda: self.on_mode_button_click(VeloMode.DEV)
        )
        self.btn_dev.grid(row=0, column=2, padx=10, pady=10, sticky="ew")
        self.btn_test = self.btn_dev  # Geriye dönük uyumluluk

    def _build_terminal(self):
        self.terminal_frame = ctk.CTkFrame(self, fg_color=THEME_CONFIG["card_bg"], corner_radius=12)
        self.terminal_frame.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")

        self.terminal_frame.grid_rowconfigure(0, weight=1)
        self.terminal_frame.grid_rowconfigure(1, weight=0)
        self.terminal_frame.grid_columnconfigure(0, weight=1)

        self.terminal_output = ctk.CTkTextbox(
            self.terminal_frame, fg_color=THEME_CONFIG["terminal"]["bg"],
            text_color=THEME_CONFIG["terminal"]["text"], font=THEME_CONFIG["fonts"]["terminal"],
            corner_radius=8, wrap="word", border_width=1, border_color=THEME_CONFIG["terminal"]["border_color"]
        )
        self.terminal_output.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew")

        self.input_frame = ctk.CTkFrame(self.terminal_frame, fg_color="transparent")
        self.input_frame.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)

        self.cmd_input = ctk.CTkEntry(
            self.input_frame, placeholder_text="Type a command or chat with Velo...",
            fg_color=THEME_CONFIG["terminal"]["input_bg"], border_color=THEME_CONFIG["terminal"]["border_color"],
            font=THEME_CONFIG["fonts"]["terminal"], height=35, corner_radius=6
        )
        self.cmd_input.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        self.cmd_input.bind("<Return>", lambda event: self.on_send_command())

        # Mikrofon Aç/Kapa Butonu
        self.btn_mic = ctk.CTkButton(
            self.input_frame, text="🎙️ Mic: ON", font=THEME_CONFIG["fonts"]["button"],
            fg_color="#2B8A3E", hover_color="#237032", width=95, height=35, corner_radius=6,
            command=self.toggle_hands_free
        )
        self.btn_mic.grid(row=0, column=1, padx=(0, 5), sticky="e")

        # Velo Sesini Aç/Kapa (TTS Mute) Butonu
        self.btn_voice = ctk.CTkButton(
            self.input_frame, text="🔊 Voice: ON", font=THEME_CONFIG["fonts"]["button"],
            fg_color="#1F7A8C", hover_color="#14525E", width=105, height=35, corner_radius=6,
            command=self.toggle_velo_voice
        )
        self.btn_voice.grid(row=0, column=2, padx=(0, 5), sticky="e")

        self.btn_send = ctk.CTkButton(
            self.input_frame, text="Send", font=THEME_CONFIG["fonts"]["button"],
            width=65, height=35, corner_radius=6, command=self.on_send_command
        )
        self.btn_send.grid(row=0, column=3, sticky="e")

    def toggle_velo_voice(self):
        """UI butonundan Velo'nun sesli yanıtını açar/kapatır."""
        is_muted = self.state_manager.tts.toggle_mute()
        state_msg = "Voice output muted." if is_muted else "Voice output enabled."
        self.write_to_terminal(f"[System] {state_msg}")

    def _sync_voice_button(self, is_muted: bool):
        """Sesli komutla mute/unmute yapıldığında UI butonunu günceller."""
        if is_muted:
            self.after(0, lambda: self.btn_voice.configure(text="🔇 Voice: OFF", fg_color="#E03131", hover_color="#B02525"))
        else:
            self.after(0, lambda: self.btn_voice.configure(text="🔊 Voice: ON", fg_color="#1F7A8C", hover_color="#14525E"))

    def toggle_hands_free(self):
        if not self.is_hands_free_active:
            self.is_hands_free_active = True
            self.btn_mic.configure(text="🎙️ Mic: ON", fg_color="#2B8A3E", hover_color="#237032")
            self.write_to_terminal("[System] Microphone listening enabled.")
            threading.Thread(target=self._hands_free_loop, daemon=True).start()
        else:
            self.is_hands_free_active = False
            self.btn_mic.configure(text="🔇 Mic: OFF", fg_color="#E03131", hover_color="#B02525")
            self.write_to_terminal("[System] Microphone muted.")

    def _extract_command_after_wake_word(self, text: str):
        """Sadece Velo türevleri ve Service kelimesini uyanma kelimesi olarak yakalar."""
        pattern = r"\b(?:hey|hello|hi)?\s*(?:velo|velow|welo|fellow|service)\b[,.\s!?:;-]*"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            return False, ""

        command_part = text[match.end():].strip()
        return True, command_part

    def _hands_free_loop(self):
        while self.is_hands_free_active:
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                time.sleep(0.05)
                continue

            audio = self.stt.listen_and_get_audio(silence_threshold=550, silence_duration=0.75, max_duration=8.0)
            if not self.is_hands_free_active:
                break

            if audio is not None:
                raw_text = self.stt.transcribe(audio)
                if not raw_text:
                    continue

                woke_up, command = self._extract_command_after_wake_word(raw_text)

                if woke_up:
                    if command:
                        self.write_to_terminal(f"You (Voice): '{command}'")
                        self.state_manager.process_command(command)
                    else:
                        self.write_to_terminal("🤖 [Velo]: Yes?")
                        self.state_manager.tts.speak("Yes?")
                        time.sleep(0.4)

                        follow_audio = self.stt.listen_and_get_audio(silence_threshold=550, silence_duration=0.75, max_duration=6.0)
                        if follow_audio is not None and self.is_hands_free_active:
                            follow_cmd = self.stt.transcribe(follow_audio)
                            if follow_cmd:
                                self.write_to_terminal(f"You (Voice): '{follow_cmd}'")
                                self.state_manager.process_command(follow_cmd)

            time.sleep(0.05)

    def write_to_terminal(self, text: str):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        prompt = THEME_CONFIG["terminal"]["prompt_symbol"]

        self.terminal_output.configure(state="normal")
        self.terminal_output.insert("end", f"[{now}] {prompt}{text}\n")
        self.terminal_output.see("end")
        self.terminal_output.configure(state="disabled")

    def minimize_to_tray(self):
        self.withdraw()
        self.write_to_terminal("[System] Minimized to system tray. Listening in background.")

    def restore_from_tray(self):
        self.after(0, self._show_window)

    def _show_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def quit_app(self):
        self.is_hands_free_active = False
        if hasattr(self, "tray") and self.tray:
            self.tray.stop()
        self.destroy()
        os._exit(0)
    def on_mode_button_click(self, mode: VeloMode):
        self.state_manager.set_mode(mode)

    def on_send_command(self):
        user_text = self.cmd_input.get().strip()
        if user_text:
            self.write_to_terminal(f"You: {user_text}")
            self.state_manager.process_command(user_text)
            self.cmd_input.delete(0, "end")
            
    def hot_reload(self):
        self.write_to_terminal("[Hot-Reload] Reloading modules...")

        # 1. Mevcut sohbet hafızasını, aktif modu ve ses durumunu yedekle
        old_history = list(self.state_manager.llm_parser.history)
        current_mode = self.state_manager.current_mode
        is_tts_muted = self.state_manager.tts.is_muted
        current_device = self.stt.device_index if self.stt else 2

        # 2. Alt modüllerden üst modüllere doğru sırayla yenile
        modules_to_reload = [
            modules.desktop_mode.app_launcher,
            modules.desktop_mode.media_ctrl,
            modules.desktop_mode.system_ctrl,
            modules.game_mode.ac_telemetry,
            modules.game_mode.game_ctrl,
            modules.dev_mode.dev_ctrl,
            audio.stt,
            audio.tts,
            core.llm_parser,
            core.state_manager,
        ]
        for mod in modules_to_reload:
            importlib.reload(mod)

        # 3. STT ve StateManager'ı sıfırdan kur (Whisper RAM'den 0ms'de gelir)
        self.stt = audio.stt.SpeechToText(model_size="base.en", device_index=current_device)
        self.state_manager = core.state_manager.StateManager(
            ui_callback=self.write_to_terminal,
            exit_callback=self.quit_app,
            mute_ui_callback=self._sync_voice_button
        )

        # 4. Yedeklenen sohbet geçmişini, modu ve ses durumunu geri yükle
        self.state_manager.llm_parser.history.extend(old_history)
        self.state_manager.current_mode = current_mode
        self.state_manager.tts.is_muted = is_tts_muted

        self.write_to_terminal("[Hot-Reload] Done in 0.1s! History & mode preserved.")

# Alias for main.py entry point
VeloUI = VeloUI