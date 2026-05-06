"""Mock speech engine for testing without ONNX runtime issues"""
import logging
from . import config

logger = logging.getLogger(__name__)


class MockSpeechEngine:
    """Mock speech engine that returns predefined transcriptions"""
    def __init__(self):
        self._model = "mock"

    def load_model(self):
        logger.info("Mock speech engine loaded (no ONNX runtime needed)")
        pass

    def transcribe_file(self, filepath: str) -> str:
        """Return mock transcription based on file path or just return empty"""
        logger.info(f"Mock transcribing: {filepath}")
        # In real use, this would be replaced with actual Whisper
        # For testing, we can return a test phrase
        return ""  # Return empty to simulate no speech detected

    def transcribe(self, audio_bytes: bytes) -> str:
        return self.transcribe_file("")
