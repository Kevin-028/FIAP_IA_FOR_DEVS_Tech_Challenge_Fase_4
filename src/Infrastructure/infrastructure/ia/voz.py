"""Pausa, energia da fala, fadiga e esforço respiratório."""
from __future__ import annotations

import numpy as np

FRAME_MS = 30
SILENCE_RMS = 0.02
FATIGUE_PAUSE = 0.40
RESPIRATORY_SPEECH_RMS = 0.05


def vocal_features(samples, sample_rate: int) -> dict:
    samples = np.asarray(samples, dtype=np.float64)
    frame = max(1, int(sample_rate * FRAME_MS / 1000))
    usable = len(samples) - (len(samples) % frame)
    if usable == 0:
        return {"pause_ratio": 1.0, "speech_rms": 0.0, "fatigue": True, "respiratory_effort": False}
    windows = samples[:usable].reshape(-1, frame)
    rms = np.sqrt(np.mean(windows ** 2, axis=1))
    silence = rms < SILENCE_RMS
    pause_ratio = float(np.mean(silence))
    speech = rms[~silence]
    speech_rms = float(np.mean(speech)) if len(speech) else 0.0
    fatigue = pause_ratio > FATIGUE_PAUSE
    respiratory = bool(fatigue and len(speech) > 0 and speech_rms < RESPIRATORY_SPEECH_RMS)
    return {
        "pause_ratio": pause_ratio,
        "speech_rms": speech_rms,
        "fatigue": fatigue,
        "respiratory_effort": respiratory,
    }
