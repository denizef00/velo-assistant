# audio/stt.py

import os
from collections import deque
import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel


class SpeechToText:
    def __init__(self, model_size="base.en", device_index=2):
        os.makedirs("logs", exist_ok=True)
        print(f"[STT] Loading Whisper '{model_size}' model...")
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        self.sample_rate = 16000
        self.device_index = device_index

    def listen_and_get_audio(self, silence_threshold=550, silence_duration=0.75, max_duration=8.0) -> np.ndarray:
        """
        Konuşma başladığı an kaydeder ve 0.75 sn sessizlik algıladığında kaydı durdurur.
        """
        chunk_duration = 0.1
        chunk_samples = int(self.sample_rate * chunk_duration)
        max_chunks = int(max_duration / chunk_duration)
        silence_limit = int(silence_duration / chunk_duration)

        pre_roll = deque(maxlen=4)  # Kelime başlarını kaçırmamak için 400ms ön tampon
        audio_chunks = []
        speech_started = False
        silent_chunks = 0

        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype='int16', device=self.device_index) as stream:
                for _ in range(max_chunks):
                    chunk, _ = stream.read(chunk_samples)
                    amplitude = np.max(np.abs(chunk))

                    if amplitude > silence_threshold:
                        if not speech_started:
                            speech_started = True
                            audio_chunks.extend(pre_roll)
                        silent_chunks = 0
                        audio_chunks.append(chunk)
                    else:
                        if not speech_started:
                            pre_roll.append(chunk)
                        else:
                            audio_chunks.append(chunk)
                            silent_chunks += 1
                            if silent_chunks >= silence_limit:
                                break

        except Exception as e:
            print(f"[STT Stream Error]: {e}")
            return None

        if not audio_chunks:
            return None

        audio_array = np.concatenate(audio_chunks, axis=0).flatten()
        return audio_array.astype(np.float32) / 32768.0

    def transcribe(self, audio_float32: np.ndarray, prompt: str = "") -> str:
        """Aksan toleransı artırılmış transkripsiyon."""
        if audio_float32 is None or len(audio_float32) == 0:
            return ""

        default_prompt = (
            "Velo, Hey Velo, open Spotify, open Chrome, open VS Code, "
            "play music, pause, resume, next track, previous track, "
            "volume up, volume down, mute, unmute, system status, "
            "game mode, desktop mode, dev mode, quit, bye bye."
        )

        try:
            segments, _ = self.model.transcribe(
                audio_float32,
                language="en",
                beam_size=2,
                best_of=2,
                without_timestamps=True,
                condition_on_previous_text=False,
                vad_filter=True,
                initial_prompt=prompt if prompt else default_prompt
            )
            return "".join([segment.text for segment in segments]).strip()
        except Exception as e:
            print(f"[STT Error]: {e}")
            return ""