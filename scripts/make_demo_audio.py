"""Gera hospital_data/fase4/samples/consulta.wav em 16 kHz mono."""
from __future__ import annotations

import os
import subprocess
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WAV_PATH = os.path.join(ROOT, "hospital_data", "fase4", "samples", "consulta.wav")

PS = r"""
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$synth.SetOutputToWaveFile($env:FASE4_WAV, $fmt)
$synth.Speak("Estou muito cansado e com falta de ar desde ontem.")
$synth.Dispose()
"""


def wav_is_demo(path: str) -> bool:
    if not os.path.isfile(path):
        return False
    with wave.open(path, "rb") as handle:
        return handle.getnchannels() == 1 and handle.getframerate() == 16000 and handle.getnframes() > 8000


def main() -> None:
    os.makedirs(os.path.dirname(WAV_PATH), exist_ok=True)
    env = os.environ.copy()
    env["FASE4_WAV"] = WAV_PATH
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", PS],
        check=True,
        env=env,
    )
    if not wav_is_demo(WAV_PATH):
        raise RuntimeError("WAV fora do formato 16 kHz mono")
    print(WAV_PATH)


if __name__ == "__main__":
    main()
