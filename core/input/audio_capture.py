from __future__ import annotations
import collections

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 44100
CHUNK = 2048        # larger = better freq resolution (~21.5 Hz/bin)
MIN_FREQ = 80       # Hz — skip DC and sub-bass
MAX_FREQ = 14000    # Hz — cap at 14kHz


class AudioCapture:
    def __init__(self):
        self._stream: sd.InputStream | None = None
        self._latest = np.zeros(CHUNK, dtype="float32")

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

    def get_fft_bands(self, n_bands: int = 24) -> np.ndarray:
        samples = self._latest
        windowed = samples * np.hanning(len(samples))
        spectrum = np.abs(np.fft.rfft(windowed))

        nyquist = SAMPLE_RATE / 2
        freq_per_bin = nyquist / len(spectrum)

        min_bin = max(1, int(MIN_FREQ / freq_per_bin))
        max_bin = min(len(spectrum) - 1, int(MAX_FREQ / freq_per_bin))

        if max_bin <= min_bin:
            return np.zeros(n_bands)

        # Log-spaced bin boundaries — low freqs get proportionally more bins
        bounds = np.unique(
            np.round(
                np.logspace(np.log10(min_bin), np.log10(max_bin), n_bands + 1)
            ).astype(int)
        )

        n_actual = len(bounds) - 1
        magnitudes = np.zeros(n_bands)
        for i in range(min(n_actual, n_bands)):
            lo, hi = bounds[i], bounds[i + 1]
            if hi > lo:
                magnitudes[i] = spectrum[lo:hi].mean()

        peak = magnitudes.max()
        if peak > 1e-6:
            magnitudes /= peak

        return magnitudes

    def get_amplitude(self) -> float:
        """RMS amplitude of the latest chunk."""
        return float(np.sqrt(np.mean(self._latest ** 2)))
