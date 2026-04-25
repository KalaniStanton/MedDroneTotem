from __future__ import annotations
import collections
import threading

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 44100
CHUNK = 1024


class AudioCapture:
    def __init__(self):
        self._buf: collections.deque[np.ndarray] = collections.deque(maxlen=8)
        self._lock = threading.Lock()
        self._stream: sd.InputStream | None = None
        self._latest = np.zeros(CHUNK)

    def start(self):
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            blocksize=CHUNK,
            dtype="float32",
            callback=self._callback,
        )
        self._stream.start()

    def stop(self):
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def _callback(self, indata: np.ndarray, frames, time_info, status):
        self._latest = indata[:, 0].copy()

    def get_fft_bands(self, n_bands: int = 32) -> np.ndarray:
        samples = self._latest
        windowed = samples * np.hanning(len(samples))
        spectrum = np.abs(np.fft.rfft(windowed))
        spectrum = spectrum[: len(spectrum) // 2]
        if len(spectrum) == 0:
            return np.zeros(n_bands)
        bands = np.array_split(spectrum, n_bands)
        magnitudes = np.array([b.mean() for b in bands])
        peak = magnitudes.max()
        if peak > 0:
            magnitudes = magnitudes / peak
        return magnitudes

    def get_waveform(self) -> np.ndarray:
        return self._latest.copy()
