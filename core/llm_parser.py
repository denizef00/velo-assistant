# core/llm_parser.py

import json
import urllib.request


class LocalCommandParser:
    def __init__(self, model_name: str = "qwen2.5:1.5b", ollama_url: str = "http://localhost:11434/api/generate"):
        self.model_name = model_name
        self.url = ollama_url

        self.system_prompt = """You are Velo, a friendly, sharp, and helpful desktop AI assistant.
Analyze the user's English input and return ONLY a valid JSON object with two keys: "intent" and "parameter".

Available intents:
- "LAUNCH_APP": User wants to open or run a software, game, or website (parameter: exact app/site name, e.g., "Spotify", "Discord").
- "PLAY_MEDIA": User wants to play a specific song, artist, or video on YouTube (parameter: search query, e.g., "Linkin Park Numb").
- "WEB_SEARCH": ONLY use this when the user explicitly says "search", "google", "look up", or "find online" (parameter: search query).
- "SYSTEM_STATUS": User asks about CPU, RAM, or PC performance (parameter: "").
- "MEDIA_CTRL": User wants to control playback, seeking, or volume (parameter: "volume_up", "volume_down", "play_pause", "next", "previous", "seek_forward", "seek_backward").
- "CHAT": Use this for greetings, small talk ("how are you", "what's up", "good morning"), personal updates ("my day was great", "I'm tired"), and ALL general knowledge questions. Respond warmly, naturally, and concisely (1-2 sentences) as Velo in "parameter".

Rules:
1. Output ONLY raw JSON. No markdown, no explanations.
2. Never use "WEB_SEARCH" for casual chat or normal questions; handle them with "CHAT".

Examples:
User: "How are you doing today?" -> {"intent": "CHAT", "parameter": "I'm running smoothly at full capacity! How has your day been going so far?"}
User: "My day was pretty good, just coding a bit" -> {"intent": "CHAT", "parameter": "That sounds like a productive day! Let me know if you need me to open any tools or put on some background music."}
User: "Skip ahead 5 seconds" -> {"intent": "MEDIA_CTRL", "parameter": "seek_forward"}
User: "Could you fire up Steam for me?" -> {"intent": "LAUNCH_APP", "parameter": "Steam"}
User: "What is the speed of light?" -> {"intent": "CHAT", "parameter": "The speed of light in a vacuum is roughly 299,792 kilometers per second."}
"""

    def parse(self, user_text: str) -> dict:
        payload = {
            "model": self.model_name,
            "prompt": f"{self.system_prompt}\nUser: \"{user_text}\"\nJSON:",
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.3,  # Sohbet yanıtlarının daha doğal ve çeşitli olması için 0.3
                "num_predict": 100
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