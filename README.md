# Velo Assistant

**Low-latency, hands-free desktop voice assistant built with Python.**  
Velo combines a zero-latency deterministic rule engine with local LLM intent parsing (Ollama), Faster-Whisper STT, and dynamic Windows OS automation—operating completely free of paid cloud APIs.

---

## ✨ Key Features

- **Hands-Free Wake-Word & VAD:** Continuous background listening with a 400ms pre-roll audio buffer (preventing clipped first syllables) and automatic silence cut-off (`0.75s`). Supports single-shot commands (e.g., *"Velo open Spotify"*).
- **Hybrid Intent Engine:**
  - **Fast Path (0ms latency):** Instant execution for hardware media keys, system volume, CPU/RAM telemetry, and direct triggers.
  - **Smart Path (Local LLM):** Falls back to a local `qwen2.5:1.5b` model via Ollama to parse unstructured natural language into structured JSON intents (`LAUNCH_APP`, `PLAY_MEDIA`, `WEB_SEARCH`, `MEDIA_CTRL`, `CHAT`).
- **Dynamic Windows App Launcher:** Automatically indexes Windows Start Menu shortcuts (`.lnk`) and Registry `App Paths` with fuzzy matching (`difflib`) to launch any installed software without hardcoded paths.
- **Zero-Latency Media & System Control:** Uses native Windows `ctypes` Virtual-Key events for instant volume and playback control across all active media players, plus direct YouTube video playback and search.
- **Multi-Mode Modular Architecture:**
  - **Desktop Mode:** Dynamic app launcher, media controls, web searching, and system performance.
  - **Game Mode:** Assetto Corsa Windows Shared Memory telemetry (fuel, tire temps, gear, speed, lap time), multi-app racing launcher (Content Manager + Discord), and hardware thermal monitoring.
  - **Dev Mode:** VS Code workspace launcher with optional lo-fi focus beats, plus intelligent clipboard code/error debugging.
- **Short-Term Conversation Memory:** Sliding window deque (maxlen=6) preserving conversational context for natural follow-ups and seamless daily check-ins.
- **Modern Dark UI:** Built with `CustomTkinter`, featuring a real-time command terminal, mode switching (`Desktop`, `Game`, `Dev`), and one-click `Mic` and `Voice` toggles.

---

## 🧠 Architecture Flow

```text
[Microphone Audio] ──► [VAD + Pre-Roll Buffer] ──► [Faster-Whisper (base.en)]
                                                              │
                                                     Wake-Word Detection
                                                              │
                                                              ▼
                                                  [StateManager Router]
                                                     ├──► Fast Rule Engine (Media / Status / Direct Apps) ──► [Execute]
                                                     └──► Local Ollama LLM (qwen2.5:1.5b JSON Parser) ────► [Execute]
                                                                                                                │
                                                                                      [Edge-TTS + Pygame RAM] ◄─┘
```

---

## 🛠️ Tech Stack

- **Speech-to-Text (STT):** `faster-whisper` (`base.en`, `int8` CPU quantization) + `sounddevice`
- **Text-to-Speech (TTS):** `edge-tts` (`en-GB-RyanNeural`) + `pygame-ce` (in-memory stream playback)
- **Local Intelligence:** Ollama (`qwen2.5:1.5b`)
- **System & OS Control:** `psutil`, `ctypes` (Win32 API), `winreg`
- **GUI Framework:** `customtkinter`

---

## 📂 Project Structure

```text
velo-assistant/
├── audio/
│   ├── stt.py                 # VAD audio capture & Faster-Whisper transcription
│   └── tts.py                 # Async Edge-TTS & in-memory audio playback
├── config/
│   └── theme.py               # UI colors, fonts, and layout configuration
├── core/
│   ├── llm_parser.py          # Local Ollama JSON intent & parameter extractor
│   └── state_manager.py       # Central command router, modes, and lifecycle control
├── modules/
│   └── desktop_mode/
│       ├── app_launcher.py    # Dynamic Start Menu & Registry app scanner
│       ├── media_ctrl.py      # Win32 Virtual-Key volume & playback controller
│       └── system_ctrl.py     # Desktop command handler & YouTube engine
└── main.py                    # Application entry point
```

---

## 🚀 Setup & Installation

### 1. Prerequisites
- **Python 3.10+** (Windows)
- **Ollama** installed locally ([ollama.com](https://ollama.com))

### 2. Pull the Local LLM
Open PowerShell and download the lightweight intent model:
```powershell
ollama run qwen2.5:1.5b
```
*(Once downloaded and the `>>>` prompt appears, type `/bye` to exit. Ollama will keep running in the background.)*

### 3. Clone & Install Dependencies
```powershell
git clone https://github.com/denizef00/velo-assistant.git
cd velo-assistant

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install customtkinter faster-whisper sounddevice numpy edge-tts pygame-ce psutil
```

### 4. Run the Assistant
```powershell
python main.py
```
Click **`🎙️ Auto Listen`** in the interface to enable hands-free wake-word detection.

---

## 🎙️ Example Commands

| Category | Example Voice / Text Input | Action |
| :--- | :--- | :--- |
| **App Launching** | *"Velo, fire up Discord"* / *"Open Calculator"* | Finds and launches the app dynamically |
| **Direct Media** | *"Velo,i play Linkin Park Numb"* | Fetches and plays the top YouTube result |
| **Media & Volume** | *"Velo, volume up"* / *"Pause"* / *"Next track"* | Triggers Win32 media/volume keys |
| **Web Search** | *"Velo, look up Python asyncio tutorials"* | Opens Google search results |
| **System Telemetry** | *"Velo, system status"* | Reports real-time CPU & RAM usage |
| **General Q&A** | *"Velo, what is the speed of light?"* | Answers directly via local LLM |
| **Assistant Control** | *"Mute"* / *"Unmute"* / *"Quit"* / *"Bye bye"* | Toggles TTS audio or cleanly exits app |

---

## 🗺️ Roadmap

- [x] Hands-free VAD wake-word pipeline & accent optimization
- [x] Dynamic Windows application indexing
- [x] Hybrid Rule-Based + Local Ollama LLM intent parser
- [x] Short-Term Conversation Memory (`deque(maxlen=6)`)
- [x] **Game Mode:** Live sim-racing telemetry integration (Assetto Corsa shared memory), hardware status, and racing profile launcher
- [x] **Dev Mode:** Workspace launcher and AI-powered clipboard debugger
- [ ] Configurable wake-word and microphone device selector in UI