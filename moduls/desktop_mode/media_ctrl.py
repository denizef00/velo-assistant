# modules/desktop_mode/media_ctrl.py

import ctypes
import time

# Windows Virtual-Key Kodları
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002


class MediaController:
    def __init__(self):
        self.user32 = ctypes.windll.user32

    def _press_key(self, vk_code: int, repeat: int = 1):
        """Windows sanal tuş basma olayını tetikler."""
        for _ in range(repeat):
            self.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
            self.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
            time.sleep(0.02)

    def volume_up(self, steps: int = 5) -> str:
        """Sistem sesini artırır (Her adım Windows'ta +2 birim artırır, 5 adım = %10)."""
        self._press_key(VK_VOLUME_UP, repeat=steps)
        return "Volume increased."

    def volume_down(self, steps: int = 5) -> str:
        """Sistem sesini kısar (5 adım = %10)."""
        self._press_key(VK_VOLUME_DOWN, repeat=steps)
        return "Volume decreased."

    def toggle_system_mute(self) -> str:
        """Windows sistem sesini tamamen kapatır veya açar."""
        self._press_key(VK_VOLUME_MUTE, repeat=1)
        return "System audio toggled."

    def play_pause(self) -> str:
        """Aktif medyayı duraklatır veya devam ettirir."""
        self._press_key(VK_MEDIA_PLAY_PAUSE, repeat=1)
        return "Playback toggled."

    def next_track(self) -> str:
        """Sonraki şarkıya/videoya geçer."""
        self._press_key(VK_MEDIA_NEXT_TRACK, repeat=1)
        return "Skipping to next track."

    def previous_track(self) -> str:
        """Önceki şarkıya/videoya döner."""
        self._press_key(VK_MEDIA_PREV_TRACK, repeat=1)
        return "Playing previous track."
    def handle_command(self, command: str) -> str:
        """Sabit ses ve medya komutlarını aksan toleransıyla yakalar."""
        cmd = command.lower().strip().rstrip(".,!?")

        # 1. Ses Artırma ("volume" -> bazen "valium" olarak algılanır)
        if any(k in cmd for k in [
            "volume up", "valium up", "increase volume", "turn up",
            "louder", "raise volume", "sound up"
        ]):
            steps = 10 if any(w in cmd for w in ["a lot", "max", "way up"]) else 5
            return self.volume_up(steps=steps)

        # 2. Ses Kısma
        elif any(k in cmd for k in [
            "volume down", "valium down", "decrease volume", "turn down",
            "lower volume", "quieter", "sound down"
        ]):
            steps = 10 if any(w in cmd for w in ["a lot", "min", "way down"]) else 5
            return self.volume_down(steps=steps)

        # 3. Sistem Sesini Kapatma / Açma
        elif any(k in cmd for k in [
            "mute system", "unmute system", "mute volume", "unmute volume",
            "mute pc", "system mute"
        ]):
            return self.toggle_system_mute()

        # 4. Medya Duraklatma / Devam Ettirme ("pause" -> bazen "pose" veya "paws" algılanır)
        elif cmd in [
            "pause", "pose", "paws", "pause music", "pause video", "stop music",
            "resume", "resume music", "continue", "play", "play music"
        ]:
            return self.play_pause()

        # 5. Sonraki / Önceki Parça
        elif any(k in cmd for k in ["next track", "next song", "skip track", "skip song", "next video", "next"]):
            return self.next_track()

        elif any(k in cmd for k in ["previous track", "previous song", "last song", "go back", "previous"]):
            return self.previous_track()

        return None
        """Sabit ses ve medya komutlarını yakalar."""
        cmd = command.lower().strip().rstrip(".,!?")

        # 1. Ses Artırma
        if any(k in cmd for k in ["volume up", "increase volume", "turn up the volume", "louder", "raise volume"]):
            steps = 10 if any(w in cmd for w in ["a lot", "max", "way up"]) else 5
            return self.volume_up(steps=steps)

        # 2. Ses Kısma
        elif any(k in cmd for k in ["volume down", "decrease volume", "turn down the volume", "lower volume", "quieter"]):
            steps = 10 if any(w in cmd for w in ["a lot", "min", "way down"]) else 5
            return self.volume_down(steps=steps)

        # 3. Sistem Sesini Kapatma / Açma (Jarvis'in kendi 'mute' komutuyla çakışmaması için)
        elif any(k in cmd for k in ["mute system", "unmute system", "mute volume", "unmute volume", "mute pc", "system mute"]):
            return self.toggle_system_mute()

        # 4. Medya Duraklatma / Devam Ettirme
        # Not: Tek başına "play" denirse medyayı devam ettirir; "play <şarkı>" denirse YouTube'a gider.
        elif cmd in ["pause", "pause music", "pause video", "stop music", "resume", "resume music", "continue", "play", "play music"]:
            return self.play_pause()

        # 5. Sonraki / Önceki Parça
        elif any(k in cmd for k in ["next track", "next song", "skip track", "skip song", "next video"]):
            return self.next_track()

        elif any(k in cmd for k in ["previous track", "previous song", "last song", "go back track"]):
            return self.previous_track()

        return None