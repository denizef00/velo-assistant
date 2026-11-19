# audio/tts.py

import asyncio
import io
import threading
import pygame
import edge_tts

VOICE = "en-GB-RyanNeural"

pygame.mixer.init()


class TextToSpeech:
    def __init__(self, voice: str = VOICE):
        self.voice = voice
        self.is_muted = False  # Mute durum değişkeni

    async def _generate_and_play(self, text: str):
        try:
            communicate = edge_tts.Communicate(text, self.voice)
            
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]

            if not audio_data:
                return

            audio_buffer = io.BytesIO(audio_data)
            pygame.mixer.music.load(audio_buffer)
            pygame.mixer.music.play()

            clock = pygame.time.Clock()
            while pygame.mixer.music.get_busy():
                clock.tick(20)

        except Exception as e:
            print(f"[TTS Error]: {e}")

    def speak(self, text: str):
        """Sessiz modda değilse sesi çalar."""
        if self.is_muted:
            print(f"[TTS Muted]: '{text}'")
            return

        def run_async():
            asyncio.run(self._generate_and_play(text))

        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()


if __name__ == "__main__":
    tts = TextToSpeech()
    tts.speak("Velo voice engine is online.")
    import time
    time.sleep(3)