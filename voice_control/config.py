import os
import secrets as _secrets

AUTH_USERNAME = os.environ.get("GO2_AUTH_USERNAME", "admin")
AUTH_PASSWORD = os.environ.get("GO2_AUTH_PASSWORD", "")

# Persisted across restarts only if you set GO2_SESSION_SECRET in .env.
# Otherwise sessions die on restart (everyone has to log in again).
SESSION_SECRET = os.environ.get("GO2_SESSION_SECRET") or _secrets.token_urlsafe(32)
SESSION_COOKIE = "go2_session"
SESSION_TTL_SECONDS = int(os.environ.get("GO2_SESSION_TTL", str(60 * 60 * 24 * 7)))  # 7 days

TLS_CERT = os.environ.get("GO2_TLS_CERT", "")
TLS_KEY = os.environ.get("GO2_TLS_KEY", "")

NETWORK_INTERFACE = os.environ.get("GO2_NETWORK_INTERFACE", "")
WHISPER_MODEL_SIZE = os.environ.get("GO2_WHISPER_MODEL", "tiny")
WHISPER_DEVICE = os.environ.get("GO2_WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.environ.get("GO2_WHISPER_COMPUTE_TYPE", "float32")
SERVER_HOST = os.environ.get("GO2_SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.environ.get("GO2_SERVER_PORT", "8000"))
ROBOT_TIMEOUT = float(os.environ.get("GO2_ROBOT_TIMEOUT", "10.0"))
MOCK_MODE = os.environ.get("GO2_MOCK_MODE", "false").lower() == "true"

KEYBIND_KEY = os.environ.get("GO2_KEYBIND_KEY", "KEY_SPACE")
AUDIO_SAMPLE_RATE = int(os.environ.get("GO2_AUDIO_SAMPLE_RATE", "16000"))
AUDIO_CHANNELS = int(os.environ.get("GO2_AUDIO_CHANNELS", "1"))
AUDIO_DTYPE = os.environ.get("GO2_AUDIO_DTYPE", "int16")
AUDIO_DEVICE = os.environ.get("GO2_AUDIO_DEVICE", "")
