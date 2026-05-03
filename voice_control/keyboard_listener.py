import asyncio
import logging
import threading
import time

logger = logging.getLogger(__name__)


try:
    from evdev import InputDevice, list_devices, ecodes
    _EVDEV_AVAILABLE = True
except ImportError:
    _EVDEV_AVAILABLE = False
    logger.warning("evdev not installed — keyboard input disabled")


class KeyboardListener:
    def __init__(self, key_name="KEY_SPACE"):
        self.key_name = key_name
        self.key_code = None
        self.device = None
        self._thread: threading.Thread | None = None
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False

        if _EVDEV_AVAILABLE:
            self.key_code = getattr(ecodes, key_name, None)
            if self.key_code is None:
                raise ValueError(f"Unknown key: {key_name}")

    def find_keyboard(self):
        if not _EVDEV_AVAILABLE:
            return None
        for path in list_devices():
            try:
                dev = InputDevice(path)
                caps = dev.capabilities()
                if ecodes.EV_KEY in caps:
                    logger.info("Found keyboard: %s at %s", dev.name, path)
                    return dev
            except (PermissionError, OSError):
                continue
        return None

    def start(self) -> bool:
        self.device = self.find_keyboard()
        if self.device is None:
            logger.error(
                "No keyboard found. "
                "Make sure a USB keyboard is plugged in and you have read access to /dev/input/event* "
                "(try: sudo usermod -aG input $USER && newgrp input)"
            )
            return False
        self._running = True
        loop = asyncio.get_running_loop()
        self._thread = threading.Thread(target=self._thread_loop, args=(loop,), daemon=True)
        self._thread.start()
        return True

    def _thread_loop(self, loop):
        while self._running:
            try:
                for event in self.device.read():
                    if not self._running:
                        return
                    if event.type == ecodes.EV_KEY and event.code == self.key_code:
                        if event.value == 1:
                            asyncio.run_coroutine_threadsafe(
                                self._queue.put(("press", None)), loop
                            )
                        elif event.value == 0:
                            asyncio.run_coroutine_threadsafe(
                                self._queue.put(("release", None)), loop
                            )
            except Exception as e:
                logger.error("Keyboard read error: %s", e)
                time.sleep(0.5)

    async def get_event(self):
        return await self._queue.get()

    def stop(self):
        self._running = False
