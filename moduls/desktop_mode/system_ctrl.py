# modules/desktop_mode/system_ctrl.py

import re
import urllib.parse
import urllib.request
import webbrowser
import psutil
from moduls.desktop_mode.app_launcher import DynamicAppLauncher
from moduls.desktop_mode.media_ctrl import MediaController


class SystemController:
    def __init__(self):
        self.app_launcher = DynamicAppLauncher()
        self.media_ctrl = MediaController()

    def get_system_status(self) -> str:
        """CPU ve RAM kullanım oranını döndürür."""
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory().percent
        return f"CPU usage is at {cpu} percent, and RAM usage is at {ram} percent."

    def search_youtube(self, query: str) -> str:
        """YouTube üzerinde verilen ifadeyi aratır ve sonuç sayfasını açar."""
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.youtube.com/results?search_query={encoded_query}"
        webbrowser.open(url)
        return f"Searching YouTube for {query}."

    def play_youtube(self, query: str) -> str:
        """YouTube üzerinde arama yapıp ilk çıkan videoyu doğrudan başlatır."""
        encoded_query = urllib.parse.quote(query)
        search_url = f"https://www.youtube.com/results?search_query={encoded_query}"

        try:
            req = urllib.request.Request(
                search_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            html = urllib.request.urlopen(req).read().decode()
            video_ids = re.findall(r"watch\?v=([\w-]{11})", html)

            if video_ids:
                first_video_url = f"https://www.youtube.com/watch?v={video_ids[0]}"
                webbrowser.open(first_video_url)
                return f"Playing {query} on YouTube."
        except Exception as e:
            print(f"[YouTube Play Error]: {e}")

        return self.search_youtube(query)

    def handle_command(self, command: str) -> str:
        """Gelen komutu analiz edip uygun sistem fonksiyonunu çalıştırır."""
        cmd = command.lower().strip()

        # 0. Sabit Ses & Medya Kontrolleri (En yüksek öncelik)
        media_response = self.media_ctrl.handle_command(cmd)
        if media_response:
            return media_response

        # 1. System Status
        if any(k in cmd for k in ["system status", "cpu", "ram", "performance", "how is the pc"]):
            return self.get_system_status()

        # 2. Uygulama Önbelleğini Yenileme
        elif any(k in cmd for k in ["refresh apps", "scan apps", "update app list"]):
            self.app_launcher.refresh_apps()
            return f"Application index refreshed. {len(self.app_launcher.app_cache)} apps available."

        # 3. Direct Video Play ("play <şarkı adı>")
        elif cmd.startswith("play ") or "play " in cmd:
            search_term = cmd
            for remove_word in ["play", "on youtube", "youtube", "video"]:
                search_term = search_term.replace(remove_word, "")
            search_term = search_term.strip()

            if search_term:
                return self.play_youtube(search_term)
            else:
                webbrowser.open("https://www.youtube.com")
                return "Opening YouTube."

        # 4. Search Engine (YouTube & Google)
        elif any(k in cmd for k in ["search", "find", "google"]):
            search_term = cmd
            for remove_word in [
                "search youtube for", "search google for", "search for",
                "search youtube", "search google", "on youtube", "on google",
                "find", "google", "search", "youtube"
            ]:
                search_term = search_term.replace(remove_word, "")
            search_term = search_term.strip()

            if search_term:
                if "google" in cmd and "youtube" not in cmd:
                    encoded_query = urllib.parse.quote(search_term)
                    webbrowser.open(f"https://www.google.com/search?q={encoded_query}")
                    return f"Searching Google for {search_term}."
                else:
                    return self.search_youtube(search_term)
            else:
                webbrowser.open("https://www.youtube.com")
                return "Opening YouTube."

        # 5. Dinamik Uygulama ve Web Başlatma
        elif any(cmd.startswith(prefix) for prefix in ["open ", "launch ", "start ", "run "]):
            app_name = cmd
            for prefix in ["open ", "launch ", "start ", "run "]:
                if app_name.startswith(prefix):
                    app_name = app_name[len(prefix):].strip()
                    break

            app_name = app_name.rstrip(".,!?")

            if app_name == "youtube":
                webbrowser.open("https://www.youtube.com")
                return "Opening YouTube."
            elif app_name in ["google", "browser"]:
                webbrowser.open("https://www.google.com")
                return "Opening web browser."

            return self.app_launcher.launch(app_name)

        return None
    def execute_llm_intent(self, parsed_data: dict) -> str:
        """Yerel LLM'den dönen JSON niyetini çalıştırır."""
        intent = parsed_data.get("intent", "UNKNOWN")
        param = parsed_data.get("parameter", "").strip()

        if intent == "LAUNCH_APP" and param:
            if param.lower() == "youtube":
                webbrowser.open("https://www.youtube.com")
                return "Opening YouTube."
            return self.app_launcher.launch(param)

        elif intent == "PLAY_MEDIA" and param:
            return self.play_youtube(param)

        elif intent == "WEB_SEARCH" and param:
            encoded_query = urllib.parse.quote(param)
            webbrowser.open(f"https://www.google.com/search?q={encoded_query}")
            return f"Searching the web for {param}."

        elif intent == "SYSTEM_STATUS":
            return self.get_system_status()

        elif intent == "MEDIA_CTRL":
            mapping = {
                "volume_up": self.media_ctrl.volume_up,
                "volume_down": self.media_ctrl.volume_down,
                "play_pause": self.media_ctrl.play_pause,
                "next": self.media_ctrl.next_track,
                "previous": self.media_ctrl.previous_track,
            }
            action = mapping.get(param)
            if action:
                return action()

        elif intent == "CHAT" and param:
            return param

        return None