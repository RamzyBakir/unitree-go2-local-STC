import logging
import os

# Limit ONNX threads to prevent crashes
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['ORT_DISABLE_THREADING'] = '1'

logger = logging.getLogger(__name__)

_WHISPER_MODEL_SIZE = os.environ.get("GO2_WHISPER_MODEL", "tiny")


class SpeechEngine:
    def __init__(self):
        self._model = None
        self._model_size = _WHISPER_MODEL_SIZE

    def load_model(self):
        logger.info("Loading faster-whisper model: %s", self._model_size)
        
        try:
            from faster_whisper import WhisperModel
            # Try with minimal settings to prevent crashes
            self._model = WhisperModel(
                self._model_size, 
                device="cpu", 
                compute_type="float32",  # Use float32 instead of int8
                num_workers=1  # Single thread
            )
            logger.info("Whisper model loaded on CPU (float32, single-threaded)")
        except Exception as e:
            logger.warning("Failed to load Whisper with float32: %s", e)
            # Try with int8 anyway - might work on better CPU
            try:
                self._model = WhisperModel(self._model_size, device="cpu", compute_type="int8", num_workers=1)
                logger.info("Whisper model loaded on CPU (int8)")
            except Exception as e2:
                logger.error("Failed to load Whisper: %s", e2)
                raise

    def transcribe_file(self, filepath: str) -> str:
        if self._model is None:
            raise RuntimeError("Whisper model not loaded")

        if not filepath:
            return ""

        try:
            # Use the same parameters as working test
            segments, _ = self._model.transcribe(
                filepath,
                language="en",
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
            logger.info("Transcribed audio file '%s' -> '%s'", filepath, text)
            return text
        except Exception as e:
            logger.error("Transcription failed: %s", e)
            return ""