# modules/desktop_mode/app_launcher.py

import os
import subprocess
import difflib

if os.name == "nt":
    import winreg


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

    def launch(self, query: str) -> str:
        """Verilen uygulama adını tam, kısmi veya benzer eşleşmeyle bulup açar."""
        target = query.strip().lower()
        if not target:
            return "Please specify an application name."

        # 1. Tam Eşleşme (Örn: "spotify" -> "spotify")
        if target in self.app_cache:
            return self._execute(target, self.app_cache[target])

        # 2. İçeren Eşleşme (Örn: "code" -> "visual studio code", "assetto" -> "assetto corsa")
        partial_matches = [name for name in self.app_cache if target in name]
        if partial_matches:
            # En kısa/en yakın isimli eşleşmeyi seç
            best_partial = min(partial_matches, key=len)
            return self._execute(best_partial, self.app_cache[best_partial])

        # 3. Yakın Kelime Eşleşmesi / Fuzzy Match (STT ufak harf hatası yaparsa)
        fuzzy_matches = difflib.get_close_matches(target, self.app_cache.keys(), n=1, cutoff=0.55)
        if fuzzy_matches:
            best_fuzzy = fuzzy_matches[0]
            return self._execute(best_fuzzy, self.app_cache[best_fuzzy])

        # 4. Sistem komutu olarak çalıştırmayı dene (calc, cmd, taskmgr, ms-settings: vb.)
        try:
            subprocess.Popen(f"start {target}", shell=True)
            return f"Attempting to start {target}."
        except Exception:
            return f"I couldn't find an application named {query}."

    def _execute(self, app_name: str, path: str) -> str:
        try:
            os.startfile(path)
            return f"Launching {app_name.title()}."
        except Exception as e:
            return f"Found {app_name.title()}, but failed to launch it: {e}"