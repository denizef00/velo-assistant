# ui/tray_manager.py

import os
import sys
import threading
import winreg
from PIL import Image, ImageDraw
import pystray

REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "VeloAssistant"


class TrayManager:
    def __init__(self, on_show, on_toggle_mic, on_quit):
        self.on_show = on_show
        self.on_toggle_mic = on_toggle_mic
        self.on_quit = on_quit
        self.icon = None

    def _create_icon_image(self) -> Image.Image:
        """Harici dosya gerektirmeden Velo için turkuaz halka ikonu çizer."""
        img = Image.new("RGBA", (64, 64), (11, 15, 23, 255))
        draw = ImageDraw.Draw(img)
        draw.ellipse((6, 6, 58, 58), outline=(0, 245, 212, 255), width=6)
        draw.ellipse((22, 22, 42, 42), fill=(0, 187, 249, 255))
        return img

    def is_autostart_enabled(self) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, APP_NAME)
                return True
        except FileNotFoundError:
            return False

    def toggle_autostart(self, icon=None, item=None):
        if self.is_autostart_enabled():
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.DeleteValue(key, APP_NAME)
            except Exception as e:
                print(f"[AutoStart Remove Error]: {e}")
        else:
            try:
                python_exe = sys.executable.replace("python.exe", "pythonw.exe")
                if not os.path.exists(python_exe):
                    python_exe = sys.executable
                script_path = os.path.abspath("main.py")
                cmd = f'"{python_exe}" "{script_path}"'

                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
            except Exception as e:
                print(f"[AutoStart Add Error]: {e}")

    def start(self):
        if self.icon is not None:
            return

        menu = pystray.Menu(
            pystray.MenuItem("Open Velo", lambda icon, item: self.on_show(), default=True),
            pystray.MenuItem("Toggle Microphone", lambda icon, item: self.on_toggle_mic()),
            pystray.MenuItem(
                "Start with Windows",
                self.toggle_autostart,
                checked=lambda item: self.is_autostart_enabled(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit Completely", lambda icon, item: self.on_quit()),
        )

        self.icon = pystray.Icon("Velo", self._create_icon_image(), "Velo Assistant", menu)
        threading.Thread(target=self.icon.run, daemon=True).start()

    def stop(self):
        if self.icon:
            self.icon.stop()
            self.icon = None