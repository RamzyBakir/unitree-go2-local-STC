import logging
import tempfile

import numpy as np
import sounddevice as sd
import soundfile as sf

from . import config

logger = logging.getLogger(__name__)


class AudioRecorder:
    def __init__(self):
        self.samplerate = config.AUDIO_SAMPLE_RATE
        self.channels = config.AUDIO_CHANNELS
        self.dtype = config.AUDIO_DTYPE
        self._frames: list[np.ndarray] = []
        self._stream: sd.RawInputStream | None = None
        self._recording = False

    def _callback(self, indata, frames, time_info, status):
        if status:
            logger.warning("Audio status: %s", status)
        self._frames.append(indata.copy())

    def start(self):
        self._frames = []
        self._recording = True
        self._stream = sd.RawInputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            dtype=self.dtype,
            callback=self._callback,
        )
        self._stream.start()
        logger.info("Recording started (%d Hz, %d ch)", self.samplerate, self.channels)

    def stop(self) -> str:
        if not self._recording or self._stream is None:
            return ""
        self._stream.stop()
        self._stream.close()
        self._recording = False

        if not self._frames:
            logger.warning("No audio recorded")
            return ""

        audio = np.concatenate(self._frames, axis=0)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            sf.write(tmp.name, audio, self.samplerate, format="WAV")
            logger.info("Saved %d samples to %s", len(audio), tmp.name)
            return tmp.name

    @property
    def is_recording(self) -> bool:
        return self._recording
