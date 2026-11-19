# core/llm_parser.py

import json
import urllib.request
from collections import deque
from typing import Optional, Tuple, List, Dict, Any


class LocalCommandParser:
    def __init__(self, model_name: str = "qwen2.5:1.5b", ollama_url: str = "http://localhost:11434/api/generate"):
        self.model_name = model_name
        self.url = ollama_url
        # Sliding window memory storing recent (user, assistant) message pairs
        self.history: deque = deque(maxlen=6)

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
3. Use the recent conversation context to understand follow-up replies and personal status updates naturally.

Examples:
User: "How are you doing today?" -> {"intent": "CHAT", "parameter": "I'm running smoothly at full capacity! How has your day been going so far?"}
User: "My day was pretty good, just coding a bit" -> {"intent": "CHAT", "parameter": "That sounds like a productive day! Let me know if you need me to open any tools or put on some background music."}
User: "Skip ahead 5 seconds" -> {"intent": "MEDIA_CTRL", "parameter": "seek_forward"}
User: "Could you fire up Steam for me?" -> {"intent": "LAUNCH_APP", "parameter": "Steam"}
User: "What is the speed of light?" -> {"intent": "CHAT", "parameter": "The speed of light in a vacuum is roughly 299,792 kilometers per second."}
"""

    def add_history(self, user_msg: str, assistant_msg: str) -> None:
        """Stores a recent (user, assistant) message pair in the sliding window memory."""
        self.history.append((user_msg.strip(), assistant_msg.strip()))

    def get_history_context(self) -> str:
        """Formats the sliding window memory into a conversational history string."""
        if not self.history:
            return ""

        context_lines = []
        for user, assistant in self.history:
            if user:
                context_lines.append(f"User: \"{user}\"")
            if assistant:
                context_lines.append(f"Velo: \"{assistant}\"")

        return "\n".join(context_lines)

    def parse(self, user_text: str) -> dict:
        history_context = self.get_history_context()
        if history_context:
            full_prompt = (
                f"{self.system_prompt}\n\n"
                f"Recent Conversation History:\n{history_context}\n\n"
                f"User: \"{user_text}\"\nJSON:"
            )
        else:
            full_prompt = f"{self.system_prompt}\nUser: \"{user_text}\"\nJSON:"

        payload = {
            "model": self.model_name,
            "prompt": full_prompt,
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

    def explain_snippet(self, code_or_error: str, prompt_hint: str = "") -> str:
        """Asks Ollama to concisely summarize or explain a code snippet or error in 1-2 spoken sentences."""
        cleaned = code_or_error.strip()
        if not cleaned:
            return "Your clipboard is currently empty."

        system_instruction = (
            "You are Velo, an expert voice assistant for programmers. "
            "Explain or summarize the following code snippet, error message, or text in 1 to 2 spoken sentences. "
            "Be direct, conversational, and clear. Do not use code blocks, markdown syntax, or bullet points."
        )

        user_prompt = f"Snippet:\n{cleaned[:2000]}\n\nExplain in 1-2 concise spoken sentences for voice output:"
        if prompt_hint:
            user_prompt = f"{prompt_hint}\n{user_prompt}"

        payload = {
            "model": self.model_name,
            "prompt": f"{system_instruction}\n\n{user_prompt}",
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 120
            }
        }

        try:
            req = urllib.request.Request(
                self.url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=7) as response:
                result = json.loads(response.read().decode("utf-8"))
                explanation = result.get("response", "").strip()
                if explanation:
                    explanation = explanation.replace("```", "").replace("\n", " ").strip()
                    return explanation
        except Exception as e:
            print(f"[LLM Explain Error]: {e}")

        # Fallback summary if Ollama is not accessible
        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        line_count = len(lines)
        if any(err_word in cleaned.lower() for err_word in ["traceback", "error", "exception", "failed"]):
            last_line = lines[-1] if lines else "an error"
            return f"You copied an error traceback. The main issue indicates: {last_line[:120]}."
        else:
            return f"You copied a snippet containing {line_count} lines of code or text."
