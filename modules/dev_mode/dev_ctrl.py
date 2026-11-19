# modules/dev_mode/dev_ctrl.py

from typing import Optional
import pyperclip

try:
    from modules.desktop_mode.system_ctrl import SystemController
except ImportError:
    from moduls.desktop_mode.system_ctrl import SystemController


class DevController(SystemController):
    """Dev / Work Mode controller for workspace launching and clipboard assistance."""

    def __init__(self, llm_parser=None):
        super().__init__()
        self.llm_parser = llm_parser

    def launch_workspace(self, play_music: bool = False) -> str:
        """Launches Visual Studio Code and optionally starts lo-fi / focus music."""
        # Try finding Visual Studio Code or Code
        launch_res = self.app_launcher.launch("Visual Studio Code")
        if "couldn't find" in launch_res.lower():
            launch_res = self.app_launcher.launch("Code")

        if play_music:
            self.play_youtube("lofi hip hop radio beats to relax study to")
            return "Opening Visual Studio Code workspace with lo-fi focus music."

        return "Opening Visual Studio Code workspace."

    def analyze_clipboard(self, hint: str = "") -> str:
        """Reads clipboard text and passes it to LLM for concise 1-2 sentence spoken explanation."""
        try:
            text = pyperclip.paste()
        except Exception as e:
            return f"Unable to access clipboard: {e}"

        if not text or not text.strip():
            return "Your clipboard is currently empty."

        clean_text = text.strip()

        if self.llm_parser and hasattr(self.llm_parser, "explain_snippet"):
            return self.llm_parser.explain_snippet(clean_text, prompt_hint=hint)

        # Clean fallback if no LLM parser attached
        lines = [line.strip() for line in clean_text.splitlines() if line.strip()]
        if any(w in clean_text.lower() for w in ["traceback", "error", "exception"]):
            return f"You copied an error traceback with {len(lines)} lines. Last line indicates: {lines[-1][:120]}."
        return f"You copied a snippet containing {len(lines)} lines of text or code."

    def handle_command(self, command: str) -> Optional[str]:
        cmd = command.lower().strip()

        # 0. Sabit Ses & Medya Kontrolleri
        media_response = self.media_ctrl.handle_command(cmd)
        if media_response:
            return media_response

        # 1. Clipboard Assistant Komutları
        if any(k in cmd for k in [
            "debug this error", "debug error", "debug clipboard", "debug the error", "debug this"
        ]):
            return self.analyze_clipboard(hint="Debug and explain the root cause of this error briefly:")

        elif any(k in cmd for k in [
            "explain what i copied", "explain clipboard", "what did i copy",
            "read clipboard", "explain copied", "analyze clipboard", "summarize clipboard"
        ]):
            return self.analyze_clipboard(hint="Summarize or explain what this snippet does:")

        # 2. Workspace Launcher Komutları
        if any(k in cmd for k in [
            "start coding", "open dev workspace", "dev workspace",
            "start work", "open workspace", "coding mode", "launch workspace", "launch dev workspace"
        ]):
            wants_music = any(m in cmd for m in ["music", "lofi", "lo-fi", "beat", "beats", "song"])
            return self.launch_workspace(play_music=wants_music)

        # 3. Genel Masaüstü / Sistem Komutlarına Düşme
        return super().handle_command(command)
