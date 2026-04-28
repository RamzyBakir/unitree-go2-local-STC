import os

NETWORK_INTERFACE = os.environ.get("GO2_NETWORK_INTERFACE", "")
WHISPER_MODEL_SIZE = os.environ.get("GO2_WHISPER_MODEL", "base")
WHISPER_DEVICE = os.environ.get("GO2_WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.environ.get("GO2_WHISPER_COMPUTE_TYPE", "int8")
SERVER_HOST = os.environ.get("GO2_SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.environ.get("GO2_SERVER_PORT", "8000"))
ROBOT_TIMEOUT = float(os.environ.get("GO2_ROBOT_TIMEOUT", "10.0"))
MOCK_MODE = os.environ.get("GO2_MOCK_MODE", "false").lower() == "true"
