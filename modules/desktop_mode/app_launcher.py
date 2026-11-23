# modules/desktop_mode/app_launcher.py

import os
import difflib
import shutil
import subprocess
if os.name == "nt":
    import winreg

ALIASES = {
    "vscode": "visual studio code",
    "vs code": "visual studio code",
    "code": "visual studio code",
    "vs": "visual studio 2022",
    "visual studio": "visual studio 2022",
    "ac": "content manager",
    "assetto": "content manager",
}

DIRECT_EXECUTABLES = {
    "visual studio code": [
        shutil.which("code"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
        r"C:\Program Files\Microsoft VS Code\Code.exe",
    ]
}
# modules/desktop_mode/app_launcher.py

URI_APPS = {
    "spotify": "spotify:",
    "settings": "ms-settings:",
    "calculator": "calculator:",
}
class DynamicAppLauncher:
    
    def __init__(self):
        self.app_cache = {}
        self.refresh_apps()

    def refresh_apps(self):
        """Sistemdeki kurulu uygulamaları tarar ve önbelleğe alır."""
        self.app_cache.clear()
        if os.name == "nt":
            self._scan_start_menu()
            self._scan_registry_app_paths()
        print(f"[AppLauncher] {len(self.app_cache)} applications indexed.")

    def _scan_start_menu(self):
        """Windows Başlat Menüsü kısayollarını (.lnk) tarar."""
        shortcut_dirs = [
            r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
            os.path.expanduser(r"~\AppData\Roaming\Microsoft\Windows\Start Menu\Programs")
        ]

        # Yanlışlıkla kaldırma/yardım dosyalarını açmamak için kara liste
        ignore_words = ["uninstall", "unins000", "readme", "help", "manual", "website", "documentation"]

        for base_dir in shortcut_dirs:
            if not os.path.exists(base_dir):
                continue

            for root, _, files in os.walk(base_dir):
                for file in files:
                    if file.lower().endswith(".lnk"):
                        clean_name = file[:-4].strip().lower()

                        if any(bad in clean_name for bad in ignore_words):
                            continue

                        full_path = os.path.join(root, file)
                        self.app_cache[clean_name] = full_path

    def _scan_registry_app_paths(self):
        """Windows Registry'deki kayıtlı .exe yollarını tarar (Discord, Steam, Chrome vb.)."""
        reg_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
        ]

        for hive, subkey_path in reg_paths:
            try:
                with winreg.OpenKey(hive, subkey_path) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        exe_name = winreg.EnumKey(key, i)
                        app_key = exe_name.lower().replace(".exe", "")

                        if app_key in self.app_cache:
                            continue

                        with winreg.OpenKey(key, exe_name) as subkey:
                            exe_path, _ = winreg.QueryValueEx(subkey, "")
                            exe_path = exe_path.strip('"')
                            if os.path.exists(exe_path):
                                self.app_cache[app_key] = exe_path
            except Exception:
                continue

    def launch(self, app_name: str) -> str:
        query = app_name.lower().strip()
        query = ALIASES.get(query, query)
        
        # 0. Doğrudan Windows URI Protokolü (Spotify vb. UWP uygulamaları için kesin çözüm)
        if query in URI_APPS:
            os.startfile(URI_APPS[query])
            return f"Opening {query.title()}."
        # 1. Doğrudan EXE / PATH kontrolü (VS Code vb. için kesin çözüm)
        if query in DIRECT_EXECUTABLES:
            for exe_path in DIRECT_EXECUTABLES[query]:
                if exe_path and os.path.exists(exe_path):
                    subprocess.Popen([exe_path], shell=True)
                    return f"Opening {query.title()}."

        # 2. Tam isim eşleşmesi
        if query in self.app_cache:
            os.startfile(self.app_cache[query])
            return f"Opening {query.title()}."

        # 3. İçinde tam geçen en kısa eşleşme
        exact_contains = [name for name in self.app_cache if query in name]
        if exact_contains:
            best_match = min(exact_contains, key=len)
            os.startfile(self.app_cache[best_match])
            return f"Opening {best_match.title()}."

        # 4. Yüksek eşikli fuzzy match (0.85 ile VS <-> VS Code karışmasını önler)
        matches = difflib.get_close_matches(query, self.app_cache.keys(), n=1, cutoff=0.85)
        if matches:
            os.startfile(self.app_cache[matches[0]])
            return f"Opening {matches[0].title()}."

        return f"I couldn't find an application named {app_name}."

    def _execute(self, app_name: str, path: str) -> str:
        try:
            os.startfile(path)
            return f"Launching {app_name.title()}."
        except Exception as e:
            return f"Found {app_name.title()}, but failed to launch it: {e}"

