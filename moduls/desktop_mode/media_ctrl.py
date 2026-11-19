# modules/desktop_mode/media_ctrl.py

import ctypes
import time

VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_LEFT = 0x25   # 5 saniye geri
VK_RIGHT = 0x27  # 5 saniye ileri

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002


class MediaController:
    def __init__(self):
        self.user32 = ctypes.windll.user32

    def _press_key(self, vk_code: int, repeat: int = 1, extended: bool = True):
        flags_down = KEYEVENTF_EXTENDEDKEY if extended else 0
        flags_up = (KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP) if extended else KEYEVENTF_KEYUP

        for _ in range(repeat):
            self.user32.keybd_event(vk_code, 0, flags_down, 0)
            self.user32.keybd_event(vk_code, 0, flags_up, 0)
            time.sleep(0.02)

    def volume_up(self, steps: int = 5) -> str:
        self._press_key(VK_VOLUME_UP, repeat=steps)
        return "Volume increased."

    def volume_down(self, steps: int = 5) -> str:
        self._press_key(VK_VOLUME_DOWN, repeat=steps)
        return "Volume decreased."

    def toggle_system_mute(self) -> str:
        self._press_key(VK_VOLUME_MUTE, repeat=1)
        return "System audio toggled."

    def play_pause(self) -> str:
        self._press_key(VK_MEDIA_PLAY_PAUSE, repeat=1)
        return "Playback toggled."

    def next_track(self) -> str:
        self._press_key(VK_MEDIA_NEXT_TRACK, repeat=1)
        return "Skipping to next track."

    def previous_track(self) -> str:
        self._press_key(VK_MEDIA_PREV_TRACK, repeat=1)
        return "Playing previous track."

    def seek_forward(self, steps: int = 1) -> str:
        """Videoyu 5 saniye (veya katları) ileri sarar."""
        self._press_key(VK_RIGHT, repeat=steps, extended=False)
        return f"Skipped forward {steps * 5} seconds."

    def seek_backward(self, steps: int = 1) -> str:
        """Videoyu 5 saniye (veya katları) geri sarar."""
        self._press_key(VK_LEFT, repeat=steps, extended=False)
        return f"Rewound {steps * 5} seconds."

    def handle_command(self, command: str) -> str:
        cmd = command.lower().strip().rstrip(".,!?")

        # 1. Videoyu İleri / Geri Sarma (5 sn)
        if any(k in cmd for k in ["forward", "skip 5", "ahead", "fast forward", "ileri"]):
            steps = 2 if "10" in cmd else 1
            return self.seek_forward(steps=steps)

        elif any(k in cmd for k in ["rewind", "back 5", "go back", "backward", "geri"]):
            steps = 2 if "10" in cmd else 1
            return self.seek_backward(steps=steps)

        # 2. Ses Artırma
        elif any(k in cmd for k in [
            "volume up", "valium up", "increase volume", "turn up",
            "louder", "raise volume", "sound up"
        ]):
            steps = 10 if any(w in cmd for w in ["a lot", "max", "way up"]) else 5
            return self.volume_up(steps=steps)

        # 3. Ses Kısma
        elif any(k in cmd for k in [
            "volume down", "valium down", "decrease volume", "turn down",
            "lower volume", "quieter", "sound down"
        ]):
            steps = 10 if any(w in cmd for w in ["a lot", "min", "way down"]) else 5
            return self.volume_down(steps=steps)

        # 4. Sistem Sesini Kapatma / Açma
        elif any(k in cmd for k in [
            "mute system", "unmute system", "mute volume", "unmute volume",
            "mute pc", "system mute"
        ]):
            return self.toggle_system_mute()

        # 5. Medya Duraklatma / Devam Ettirme
        elif cmd in [
            "pause", "pose", "paws", "pause music", "pause video", "stop music",
            "resume", "resume music", "continue", "play", "play music"
        ]:
            return self.play_pause()

        # 6. Sonraki / Önceki Parça
        elif any(k in cmd for k in ["next track", "next song", "skip track", "skip song", "next video", "next"]):
            return self.next_track()

        elif any(k in cmd for k in ["previous track", "previous song", "last song", "previous"]):
            return self.previous_track()

        return None