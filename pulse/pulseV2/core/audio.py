"""Audio playback and real-time analysis. No GUI imports."""
import os
import sys
import threading
import time

import numpy as np

SR = 44100
FFT = 2048
COLS = 37  # spectrum columns, mirrored: bass in the middle, treble at both ends


def _add(out, start, sig):
    end = min(len(out), start + len(sig))
    if end > start:
        out[start:end] += sig[: end - start]


def make_demo(seconds=32, bpm=112):
    """Synthesize a short looping beat (kick, hat, bass, lead)."""
    out = np.zeros(SR * seconds, np.float32)
    beat = 60.0 / bpm
    rng = np.random.default_rng(1)
    bass_notes = [55.0, 55.0, 65.41, 49.0]
    lead = [220.0, 261.63, 329.63, 293.66, 392.0, 329.63, 261.63, 196.0]
    for k in range(int(seconds / beat)):
        t0 = int(k * beat * SR)
        t = np.arange(int(0.4 * SR)) / SR
        _add(out, t0, np.sin(2 * np.pi * np.cumsum(42 + 88 * np.exp(-t * 28)) / SR) * np.exp(-t * 9))
        th = np.arange(int(0.06 * SR)) / SR
        _add(out, t0 + int(beat / 2 * SR), np.diff(rng.standard_normal(len(th) + 1)) * np.exp(-th * 70) * 0.35)
        f = bass_notes[(k // 4) % 4]
        tb = np.arange(int(beat / 2 * SR)) / SR
        for s in range(2):
            w = 2 * np.pi * f * (1 + s) * tb
            _add(out, t0 + int(s * beat / 2 * SR), (np.sin(w) + 0.4 * np.sin(2 * w)) * np.exp(-tb * 7) * 0.3)
        if k >= 8 and k % 2 == 0:
            tl = np.arange(int(beat * 1.8 * SR)) / SR
            _add(out, t0, np.sin(2 * np.pi * lead[(k // 2) % 8] * tl) * np.exp(-tl * 3) * 0.18)
    out *= 0.85 / max(1e-6, float(np.abs(out).max()))
    return np.column_stack([out, out])


def decode(path):
    """Decode an audio file to (stereo float32 array, sample_rate, title)."""
    import soundfile as sf
    data, sr = sf.read(path, dtype="float32", always_2d=True)
    if data.shape[1] == 1:
        data = np.repeat(data, 2, axis=1)
    return np.ascontiguousarray(data[:, :2]), sr, os.path.splitext(os.path.basename(path))[0]


def _ease(cur, target, up, down, dt):
    k = np.where(target > cur, up, down)
    return cur + (target - cur) * (1.0 - (1.0 - k) ** (dt * 30.0))


class Player:
    """Plays a decoded track and exposes smoothed analysis values for visuals."""

    def __init__(self):
        self.data = np.zeros((SR, 2), np.float32)
        self.sr, self.pos, self.volume = SR, 0, 0.8
        self.playing, self.loop, self.title, self.error = False, False, "Pulse", ""
        self.stream, self._stream_sr = None, 0
        self._lock = threading.Lock()
        self.lv = np.zeros(COLS)
        self.bass = self.mid = self.hi = self.energy = self.peak = 0.0
        self.beat_pulse = self.spin = 0.0
        self.waves, self._ivs = [], []
        self._last_beat = self._prev_bass = 0.0
        self._bins = 1 + (np.abs(np.linspace(-1, 1, COLS)) ** 2 * 400).astype(int)
        self._win = np.hanning(FFT)

    # ---- transport ----
    def load(self, path):
        self.set_track(*decode(path))

    def load_demo(self):
        self.set_track(make_demo(), SR, "Demo", loop=True)

    def set_track(self, data, sr, title, loop=False):
        with self._lock:
            self.playing = False
            self.data, self.sr, self.pos, self.title, self.loop = data, sr, 0, title, loop
        self._ivs.clear()
        self._open_stream()
        self.playing = True

    def toggle(self):
        if not self.playing and self.pos >= len(self.data) - 1:
            self.pos = 0
        self.playing = not self.playing

    def seek(self, delta):
        self.pos = int(np.clip(self.pos + delta * self.sr, 0, len(self.data) - 1))

    def seek_to(self, fraction):
        self.pos = int(np.clip(fraction, 0, 1) * (len(self.data) - 1))

    @property
    def position(self):
        return self.pos / self.sr

    @property
    def duration(self):
        return len(self.data) / self.sr

    @property
    def bpm(self):
        if len(self._ivs) < 4:
            return 0.0
        bpm = 60.0 / float(np.median(self._ivs))
        while bpm < 70:
            bpm *= 2
        while bpm > 180:
            bpm /= 2
        return bpm

    def close(self):
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def _open_stream(self):
        if self.stream is not None and self._stream_sr == self.sr:
            return
        self.close()
        try:
            import sounddevice as sd
            self.stream = sd.OutputStream(samplerate=self.sr, channels=2, dtype="float32",
                                          blocksize=1024, callback=self._callback)
            self.stream.start()
            self._stream_sr = self.sr
        except Exception as exc:  # no audio device or missing PortAudio
            self.stream, self.error = None, str(exc)
            print("audio output unavailable:", exc, file=sys.stderr)

    def _callback(self, out, frames, time_info, status):
        with self._lock:
            if not self.playing:
                out.fill(0)
                return
            chunk = self.data[self.pos:self.pos + frames]
            n = len(chunk)
            out[:n] = chunk * self.volume
            out[n:] = 0
            self.pos += n
            if n < frames:
                self.pos = 0
                self.playing = self.loop

    # ---- analysis ----
    def analyse(self, dt):
        """Update smoothed bands, spectrum columns and beat state. Call once per frame."""
        dt = min(max(dt, 1e-3), 0.05)
        now = time.monotonic()
        raw = np.zeros(COLS)
        b = m = h = pk = 0.0
        if self.playing:
            seg = self.data[max(0, self.pos - FFT):self.pos].mean(axis=1)
            if len(seg) < FFT:
                seg = np.pad(seg, (FFT - len(seg), 0))
            spec = np.abs(np.fft.rfft(seg * self._win)) / (FFT / 4)
            v = np.clip((20 * np.log10(spec + 1e-9) + 80) / 60, 0, 1)
            b, m, h, pk = float(v[2:8].mean()), float(v[28:160].mean()), float(v[160:480].mean()), float(v.max())
            raw = v[self._bins] ** 2 * 1.25
        smooth = np.convolve(np.pad(raw, 1, mode="edge"), [0.25, 0.5, 0.25], mode="valid")
        self.lv = _ease(self.lv, smooth, 0.5, 0.1, dt)
        self.bass = float(_ease(self.bass, b, 0.5, 0.1, dt))
        self.mid = float(_ease(self.mid, m, 0.25, 0.1, dt))
        self.hi = float(_ease(self.hi, h, 0.3, 0.12, dt))
        self.peak = float(_ease(self.peak, pk, 0.3, 0.1, dt))
        self.energy = self.bass * 0.6 + self.mid * 0.3 + self.hi * 0.1
        self.beat_pulse *= 0.88 ** (dt * 30)
        self.spin *= 0.92 ** (dt * 30)
        if self.playing and b - self._prev_bass > 0.07 and now - self._last_beat > 0.28:
            if self._last_beat:
                self._ivs = (self._ivs + [now - self._last_beat])[-16:]
            self._last_beat = now
            self.waves = (self.waves + [now])[-3:]
            self.beat_pulse, self.spin = 1.0, self.spin + 1.0
        self._prev_bass = b
