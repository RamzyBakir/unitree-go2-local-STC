import logging
import tempfile
import os

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
        self._stream: sd.InputStream | None = None
        self._recording = False

    def _callback(self, indata, frames, time_info, status):
        if status:
            logger.warning("Audio status: %s", status)
        audio_array = np.frombuffer(indata, dtype=self.dtype)
        audio_array = audio_array.reshape(-1, self.channels)
        self._frames.append(audio_array.copy())

    def start(self):
        self._frames = []
        self._recording = True
        
        # Try PulseAudio (device 24) which supports mono input
        tried_devices = [24, 25, 4]  # pulse, default, first APE
        stream = None
        
        for dev in tried_devices:
            try:
                info = sd.query_devices(dev)
                if info['max_input_channels'] >= self.channels:
                    self._stream = sd.InputStream(
                        device=dev,
                        samplerate=self.samplerate,
                        channels=self.channels,
                        dtype=self.dtype,
                        callback=self._callback,
                    )
                    logger.info("Using audio device %d: %s", dev, info['name'])
                    break
            except Exception as e:
                logger.warning("Device %d failed: %s", dev, e)
                continue
        
        if self._stream is None:
            raise RuntimeError("No working audio input device found")
        
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
        duration = len(audio) / self.samplerate

        if duration < 0.5:
            logger.warning("Audio too short (%.3fs), ignoring", duration)
            return ""

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            sf.write(tmp.name, audio, self.samplerate, format="WAV")
            logger.info("Saved %d samples (%.2fs) to %s", len(audio), duration, tmp.name)
            return tmp.name

    @property
    def is_recording(self) -> bool:
        return self._recording
