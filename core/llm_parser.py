# core/llm_parser.py

import json
import urllib.request


class LocalCommandParser:
    def __init__(self, model_name: str = "qwen2.5:1.5b", ollama_url: str = "http://localhost:11434/api/generate"):
        self.model_name = model_name
        self.url = ollama_url

        self.system_prompt = """You are the intent parser and brain for a desktop AI assistant named Jarvis.
Analyze the user's English command and return ONLY a valid JSON object with two keys: "intent" and "parameter".

Available intents:
- "LAUNCH_APP": User wants to open or run a software, game, or website (parameter: exact app/site name, e.g., "Spotify", "Discord").
- "PLAY_MEDIA": User wants to play a specific song, artist, or video on YouTube (parameter: search query, e.g., "Linkin Park Numb").
- "WEB_SEARCH": ONLY use this when the user explicitly says "search", "google", "look up", or "find online" (parameter: search query).
- "SYSTEM_STATUS": User asks about CPU, RAM, or PC performance (parameter: "").
- "MEDIA_CTRL": User wants to control playback or volume (parameter: "volume_up", "volume_down", "play_pause", "next", "previous").
- "CHAT": Use this for ALL general knowledge questions ("what is", "who is", "why", "how", "tell me") and casual conversation. Answer directly in "parameter" as a brief, polite, 1-sentence Jarvis response.

Rules:
1. Output ONLY raw JSON. No markdown, no explanations.
2. Do NOT use "WEB_SEARCH" for normal questions; answer them yourself using "CHAT".

Examples:
User: "Could you fire up Steam for me?" -> {"intent": "LAUNCH_APP", "parameter": "Steam"}
User: "I feel like listening to Bohemian Rhapsody" -> {"intent": "PLAY_MEDIA", "parameter": "Bohemian Rhapsody"}
User: "Look up Python asyncio tutorials" -> {"intent": "WEB_SEARCH", "parameter": "Python asyncio tutorials"}
User: "What is the speed of light?" -> {"intent": "CHAT", "parameter": "The speed of light in a vacuum is approximately 299,792 kilometers per second, sir."}
User: "Tell me a fun fact about Formula 1" -> {"intent": "CHAT", "parameter": "A modern Formula 1 car generates enough downforce to theoretically drive upside down on a ceiling at high speeds, sir."}
"""
    def parse(self, user_text: str) -> dict:
        """Kullanıcı metnini yerel Ollama modeline gönderip JSON niyet çıktısı alır."""
        payload = {
            "model": self.model_name,
            "prompt": f"{self.system_prompt}\nUser: \"{user_text}\"\nJSON:",
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.1,  # Tutarlı ve deterministik JSON çıktısı için düşük sıcaklık
                "num_predict": 80    # Kısa yanıt limiti (maksimum hız)
            }
        }

        try:
            req = urllib.request.Request(
                self.url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                result = json.loads(response.read().decode("utf-8"))
                parsed_json = json.loads(result.get("response", "{}"))
                print(f"[LLM Parser]: {parsed_json}")
                return parsed_json
        except Exception as e:
            print(f"[LLM Parser Error]: {e}")
            return {"intent": "UNKNOWN", "parameter": ""}