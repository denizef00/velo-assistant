# audio/tts.py

import asyncio
import io
import threading
import pygame
import edge_tts

VOICE = "en-GB-RyanNeural"
pygame.mixer.init()


class TextToSpeech:
    def __init__(self, voice: str = VOICE, on_mute_change=None):
        self.voice = voice
        self.is_muted = False
        self.on_mute_change = on_mute_change

    def set_mute(self, muted: bool):
        self.is_muted = muted
        if muted:
            self.stop()
        if self.on_mute_change:
            self.on_mute_change(self.is_muted)

    def toggle_mute(self) -> bool:
        self.set_mute(not self.is_muted)
        return self.is_muted

    def stop(self):
        """O an çalan sesi anında durdurur."""
        try:
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
        except Exception:
            pass

    async def _generate_and_play(self, text: str):
        try:
            # Konuşma hızını +12% yaparak daha seri bir tepki süresi sağlar
            communicate = edge_tts.Communicate(text, self.voice, rate="+12%")

            audio_data = b""
            async for chunk in communicate.stream():
                if self.is_muted:
                    return
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]

            if not audio_data or self.is_muted:
                return

            audio_buffer = io.BytesIO(audio_data)
            pygame.mixer.music.load(audio_buffer)
            pygame.mixer.music.play()

            clock = pygame.time.Clock()
            while pygame.mixer.music.get_busy():
                if self.is_muted:
                    pygame.mixer.music.stop()
                    break
                clock.tick(30)

        except Exception as e:
            print(f"[TTS Error]: {e}")

    def speak(self, text: str):
        if self.is_muted or not text:
            return

        def run_async():
            asyncio.run(self._generate_and_play(text))

        threading.Thread(target=run_async, daemon=True).start()