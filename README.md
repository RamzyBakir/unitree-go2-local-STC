# Unitree Go2 — Voice Control Dashboard

A **web-based voice & text control interface** for the Unitree Go2 robot, built on top of [`unitree_sdk2_python`](https://github.com/unitreerobotics/unitree_sdk2_python).

![dashboard](voice_control/static/screenshot.png)

## Features
- **Voice commands** — natural speech recognition via OpenAI Whisper (`faster-whisper`)
- **Text commands** — type commands directly in the web UI
- **Hold-to-speak** — press and hold the microphone button (or `Space` key) to record
- **Real-time dashboard** — WebSocket-powered status, command history, and robot state
- **~30 built-in motions** — stand, sit, dance, walk, jump, stretch, and more
- **Optional login** — session-based auth with configurable username / password
- **TLS support** — serve over HTTPS with custom certificates
- **Mock mode** — test the full UI without a physical robot connected

---

## Quick Start

### 1. Prerequisites
- Python ≥ 3.8
- cyclonedds == 0.10.2 (compiled & installed)
- Linux (for `evdev` keyboard listener; optional)
- Microphone access

### 2. Install
```bash
# Clone this fork
git clone https://github.com/YOUR_USERNAME/unitree-go2-voice-control.git
cd unitree-go2-voice-control

# Install base SDK
pip3 install -e .

# Install voice control dependencies
pip3 install -r voice_control/requirements.txt
```

### 3. Configure
Create a `.env` file in the repo root:
```bash
# Network
GO2_NETWORK_INTERFACE=enp2s0          # DDS interface (leave empty for default)
GO2_SERVER_HOST=0.0.0.0
GO2_SERVER_PORT=8000

# Auth (recommended for shared networks)
GO2_AUTH_USERNAME=admin
GO2_AUTH_PASSWORD=your_secure_password
GO2_SESSION_SECRET=change_me_in_production

# Whisper / Speech-to-Text
GO2_WHISPER_MODEL=tiny                # tiny / base / small / medium / large
GO2_WHISPER_DEVICE=cpu                # cpu or cuda
GO2_WHISPER_COMPUTE_TYPE=float32      # float32 / float16 / int8

# Audio
GO2_AUDIO_SAMPLE_RATE=16000
GO2_AUDIO_CHANNELS=1
GO2_KEYBIND_KEY=KEY_SPACE             # Keyboard key to trigger recording

# Robot
GO2_ROBOT_TIMEOUT=10.0

# Testing without a real robot
GO2_MOCK_MODE=false

# TLS (optional)
GO2_TLS_CERT=/path/to/cert.pem
GO2_TLS_KEY=/path/to/key.pem
```

### 4. Run
```bash
python3 run.py
```
Open your browser at `http://localhost:8000` (or `https` if TLS is enabled).

---

## Supported Commands

The parser recognizes natural language for the following motions:

| Motion | Example Phrases |
|--------|-----------------|
| Stand Up | "stand up", "get up", "rise" |
| Sit Down | "sit down", "sit", "take a seat" |
| Stretch | "stretch", "reach out" |
| Hello / Greet | "hello", "wave", "say hi" |
| Heart | "love", "heart", "i love you" |
| Dance 1 / Dance 2 | "dance", "do a dance", "dance two" |
| Walk Forward | "walk forward", "go ahead", "move forward" |
| Walk Backward | "walk backward", "step back", "go back" |
| Turn Left / Right | "turn left", "spin right" |
| Move Left / Right | "move left", "strafe right" |
| Stop | "stop", "halt", "freeze" |
| Balance Stand | "balance", "balance stand" |
| Recovery Stand | "recovery", "get up" |
| Squat | "squat", "crouch" |
| Jump | "jump", "hop" |
| Step | "step", "take a step" |
| Skateboard | "skateboard" |
| Fingertip Stand | "fingertip" |
| One-legged Stand | "one leg", "one-legged" |
| Handstand | "handstand" |
| Damped | "damped", "limp" |
| Stand Out | "stand out" |
| Wiggle Hips | "wiggle", "wiggle hips" |

---

## Architecture

```
┌──────────────┐     WebSocket / HTTP      ┌──────────────┐     DDS      ┌────────┐
│  Browser UI  │  ◄────────────────────►  │  FastAPI     │  ◄──────►  │  Go2   │
│  (static/)   │   hold-to-speak / text    │  (server.py) │   SportClient│ Robot  │
└──────────────┘                           └──────────────┘              └────────┘
                                                  │
                                            ┌─────┴─────┐
                                            ▼           ▼
                                     ┌──────────┐  ┌──────────┐
                                     │  faster  │  │ command  │
                                     │ whisper  │  │ parser   │
                                     └──────────┘  └──────────┘
```

### Component Overview

| File | Purpose |
|------|---------|
| `run.py` | Entry point — loads `.env` and starts Uvicorn |
| `voice_control/server.py` | FastAPI app, auth middleware, WebSocket, REST endpoints |
| `voice_control/speech.py` | `faster-whisper` wrapper for speech-to-text |
| `voice_control/speech_mock.py` | Offline STT mock for testing without a model |
| `voice_control/audio_recorder.py` | Microphone capture via `sounddevice` |
| `voice_control/keyboard_listener.py` | Linux `evdev` listener for hardware key triggers |
| `voice_control/command_parser.py` | Natural language → robot motion mapping |
| `voice_control/robot_controller.py` | DDS `SportClient` wrapper with mock support |
| `voice_control/config.py` | Environment-based configuration |
| `voice_control/static/` | Frontend (HTML / CSS / JS) with glassmorphism design |

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `GO2_NETWORK_INTERFACE` | *(empty)* | DDS network interface name |
| `GO2_SERVER_HOST` | `0.0.0.0` | Server bind address |
| `GO2_SERVER_PORT` | `8000` | Server bind port |
| `GO2_AUTH_USERNAME` | `admin` | Login username |
| `GO2_AUTH_PASSWORD` | *(empty)* | Login password (empty = no auth) |
| `GO2_SESSION_SECRET` | random | Session cookie signing key |
| `GO2_SESSION_TTL` | `604800` | Session lifetime in seconds (7 days) |
| `GO2_WHISPER_MODEL` | `tiny` | Whisper model size |
| `GO2_WHISPER_DEVICE` | `cpu` | Inference device |
| `GO2_WHISPER_COMPUTE_TYPE` | `float32` | Quantization type |
| `GO2_AUDIO_SAMPLE_RATE` | `16000` | Recording sample rate |
| `GO2_AUDIO_CHANNELS` | `1` | Recording channels |
| `GO2_AUDIO_DTYPE` | `int16` | Recording bit depth |
| `GO2_AUDIO_DEVICE` | *(empty)* | Specific audio device index |
| `GO2_KEYBIND_KEY` | `KEY_SPACE` | Keyboard trigger key |
| `GO2_ROBOT_TIMEOUT` | `10.0` | DDS client timeout |
| `GO2_MOCK_MODE` | `false` | Run without real robot |
| `GO2_TLS_CERT` | *(empty)* | Path to TLS certificate |
| `GO2_TLS_KEY` | *(empty)* | Path to TLS private key |

---

## Dependencies

### Base SDK
- `cyclonedds == 0.10.2`
- `numpy`
- `opencv-python`

### Voice Control
- `fastapi`
- `uvicorn[standard]`
- `python-multipart`
- `faster-whisper`
- `sounddevice`
- `soundfile`
- `evdev`
- `python-dotenv`

---

## License

This fork retains the original license of [`unitree_sdk2_python`](https://github.com/unitreerobotics/unitree_sdk2_python). Voice control additions are provided under the same terms.
