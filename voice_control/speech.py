import io
import logging
import tempfile
from faster_whisper import WhisperModel
from . import config

logger = logging.getLogger(__name__)


class SpeechEngine:
    def __init__(self):
        self._model: WhisperModel | None = None

    def load_model(self):
        logger.info(
            "Loading faster-whisper model '%s' on %s (%s)...",
            config.WHISPER_MODEL_SIZE,
            config.WHISPER_DEVICE,
            config.WHISPER_COMPUTE_TYPE,
        )
        self._model = WhisperModel(
            config.WHISPER_MODEL_SIZE,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE_TYPE,
        )
        logger.info("Whisper model loaded.")

    def transcribe(self, audio_bytes: bytes) -> str:
        if self._model is None:
            raise RuntimeError("Whisper model not loaded")

        with tempfile.NamedTemporaryFile(suffix=".webm", delete=True) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()
            segments, _ = self._model.transcribe(
                tmp.name,
                language="en",
                beam_size=1,
                vad_filter=True,
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()

        logger.info("Transcribed: '%s'", text)
        return text
