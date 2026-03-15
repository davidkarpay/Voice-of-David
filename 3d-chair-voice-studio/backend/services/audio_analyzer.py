"""Audio quality analysis service for David's Voice.

Analyzes WAV recordings for signal-to-noise ratio (SNR), clipping,
silence ratio, duration, and overall quality scoring.
"""

import io
import struct
import numpy as np
from scipy import signal as scipy_signal
from typing import Optional
from pathlib import Path

from config import (
    AUDIO_SAMPLE_RATE, MIN_DURATION_SECONDS, MAX_DURATION_SECONDS,
    SNR_THRESHOLD_A, SNR_THRESHOLD_B, SNR_THRESHOLD_C,
    CLIPPING_THRESHOLD, MAX_SILENCE_RATIO
)


class AudioAnalysisResult:
    """Result of audio quality analysis."""

    def __init__(self):
        self.duration_seconds: float = 0.0
        self.sample_rate: int = 0
        self.channels: int = 0
        self.bit_depth: int = 0
        self.snr_db: float = 0.0
        self.rms_db: float = 0.0
        self.peak_amplitude: float = 0.0
        self.has_clipping: bool = False
        self.clipping_count: int = 0
        self.silence_ratio: float = 0.0
        self.quality_score: str = "D"  # A, B, C, D
        self.issues: list[str] = []
        self.suggestions: list[str] = []

    def to_dict(self) -> dict:
        return {
            "duration_seconds": round(self.duration_seconds, 2),
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "bit_depth": self.bit_depth,
            "snr_db": round(self.snr_db, 1),
            "rms_db": round(self.rms_db, 1),
            "peak_amplitude": round(self.peak_amplitude, 4),
            "has_clipping": self.has_clipping,
            "clipping_count": self.clipping_count,
            "silence_ratio": round(self.silence_ratio, 3),
            "quality_score": self.quality_score,
            "issues": self.issues,
            "suggestions": self.suggestions,
        }


def read_wav_bytes(wav_bytes: bytes) -> tuple[np.ndarray, int, int, int]:
    """Parse WAV file from bytes. Returns (samples, sample_rate, channels, bit_depth).

    Samples are normalized to float64 in range [-1.0, 1.0].
    """
    buf = io.BytesIO(wav_bytes)

    # RIFF header
    riff = buf.read(4)
    if riff != b"RIFF":
        raise ValueError("Not a valid WAV file (missing RIFF header)")
    buf.read(4)  # file size
    wave = buf.read(4)
    if wave != b"WAVE":
        raise ValueError("Not a valid WAV file (missing WAVE marker)")

    # Find fmt and data chunks
    fmt_data = None
    audio_data = None
    sample_rate = 0
    channels = 0
    bit_depth = 0

    while True:
        chunk_header = buf.read(8)
        if len(chunk_header) < 8:
            break
        chunk_id = chunk_header[:4]
        chunk_size = struct.unpack("<I", chunk_header[4:8])[0]

        if chunk_id == b"fmt ":
            fmt_data = buf.read(chunk_size)
            audio_format = struct.unpack("<H", fmt_data[0:2])[0]
            channels = struct.unpack("<H", fmt_data[2:4])[0]
            sample_rate = struct.unpack("<I", fmt_data[4:8])[0]
            bit_depth = struct.unpack("<H", fmt_data[14:16])[0]
            if audio_format != 1:  # PCM
                raise ValueError(f"Unsupported audio format: {audio_format} (only PCM supported)")
        elif chunk_id == b"data":
            audio_data = buf.read(chunk_size)
            break
        else:
            buf.read(chunk_size)
            # Pad byte for odd chunk sizes
            if chunk_size % 2 == 1:
                buf.read(1)

    if fmt_data is None or audio_data is None:
        raise ValueError("WAV file missing fmt or data chunk")

    # Convert to numpy array
    if bit_depth == 16:
        samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float64) / 32768.0
    elif bit_depth == 24:
        # 24-bit needs manual unpacking
        n_samples = len(audio_data) // 3
        samples = np.zeros(n_samples, dtype=np.float64)
        for i in range(n_samples):
            b = audio_data[i * 3: i * 3 + 3]
            val = int.from_bytes(b, byteorder="little", signed=True)
            samples[i] = val / 8388608.0
    elif bit_depth == 32:
        samples = np.frombuffer(audio_data, dtype=np.int32).astype(np.float64) / 2147483648.0
    else:
        raise ValueError(f"Unsupported bit depth: {bit_depth}")

    # Convert to mono if stereo
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
        channels = 1

    return samples, sample_rate, channels, bit_depth


def estimate_snr(samples: np.ndarray, sample_rate: int) -> float:
    """Estimate Signal-to-Noise Ratio (SNR) in decibels (dB).

    Uses voice activity detection (VAD) based on energy thresholding
    to separate speech frames from noise frames.
    """
    frame_length = int(0.025 * sample_rate)  # 25 millisecond frames
    hop_length = int(0.010 * sample_rate)    # 10 millisecond hop

    # Calculate frame energies
    n_frames = (len(samples) - frame_length) // hop_length + 1
    if n_frames < 2:
        return 0.0

    energies = np.zeros(n_frames)
    for i in range(n_frames):
        start = i * hop_length
        frame = samples[start:start + frame_length]
        energies[i] = np.mean(frame ** 2)

    # VAD: frames above 10% of mean energy are speech
    energy_threshold = np.mean(energies) * 0.1
    speech_mask = energies > energy_threshold
    noise_mask = ~speech_mask

    if not np.any(speech_mask) or not np.any(noise_mask):
        return 40.0  # Default to good if can't separate

    speech_energy = np.mean(energies[speech_mask])
    noise_energy = np.mean(energies[noise_mask])

    if noise_energy < 1e-10:
        return 60.0  # Very clean

    snr = 10 * np.log10(speech_energy / noise_energy)
    return max(0.0, min(60.0, snr))


def detect_clipping(samples: np.ndarray, threshold: float = CLIPPING_THRESHOLD) -> tuple[bool, int]:
    """Detect digital clipping in audio.

    Returns (has_clipping, count_of_clipped_samples).
    """
    clipped = np.abs(samples) >= threshold
    count = int(np.sum(clipped))
    # Only flag as clipping if there are consecutive clipped samples
    has_clipping = count > 10
    return has_clipping, count


def calculate_silence_ratio(samples: np.ndarray, sample_rate: int) -> float:
    """Calculate the ratio of silence to total duration.

    Silence is defined as frames below -40dB relative to peak.
    """
    frame_length = int(0.025 * sample_rate)
    hop_length = int(0.010 * sample_rate)

    n_frames = (len(samples) - frame_length) // hop_length + 1
    if n_frames < 1:
        return 0.0

    silent_frames = 0
    peak = np.max(np.abs(samples))
    if peak < 1e-6:
        return 1.0

    silence_threshold = peak * 0.01  # -40dB relative to peak

    for i in range(n_frames):
        start = i * hop_length
        frame = samples[start:start + frame_length]
        if np.max(np.abs(frame)) < silence_threshold:
            silent_frames += 1

    return silent_frames / n_frames


def analyze_audio(wav_bytes: bytes) -> AudioAnalysisResult:
    """Perform complete quality analysis on a WAV audio file.

    Args:
        wav_bytes: Raw bytes of a WAV file.

    Returns:
        AudioAnalysisResult with all quality metrics and scoring.
    """
    result = AudioAnalysisResult()

    try:
        samples, sample_rate, channels, bit_depth = read_wav_bytes(wav_bytes)
    except ValueError as e:
        result.issues.append(f"Invalid audio: {e}")
        return result

    result.sample_rate = sample_rate
    result.channels = channels
    result.bit_depth = bit_depth
    result.duration_seconds = len(samples) / sample_rate

    # Duration check
    if result.duration_seconds < MIN_DURATION_SECONDS:
        result.issues.append(f"Too short ({result.duration_seconds:.1f}s). Minimum is {MIN_DURATION_SECONDS}s.")
    if result.duration_seconds > MAX_DURATION_SECONDS:
        result.issues.append(f"Too long ({result.duration_seconds:.1f}s). Maximum is {MAX_DURATION_SECONDS}s.")

    # Sample rate check
    if sample_rate != AUDIO_SAMPLE_RATE:
        result.issues.append(f"Sample rate is {sample_rate}Hz, expected {AUDIO_SAMPLE_RATE}Hz.")
        result.suggestions.append(f"Set your recording device to {AUDIO_SAMPLE_RATE}Hz.")

    # RMS level
    rms = np.sqrt(np.mean(samples ** 2))
    result.rms_db = 20 * np.log10(rms) if rms > 0 else -100.0

    # Peak amplitude
    result.peak_amplitude = float(np.max(np.abs(samples)))

    # SNR
    result.snr_db = estimate_snr(samples, sample_rate)

    # Clipping
    result.has_clipping, result.clipping_count = detect_clipping(samples)
    if result.has_clipping:
        result.issues.append(f"Clipping detected ({result.clipping_count} samples). Reduce input volume.")

    # Silence ratio
    result.silence_ratio = calculate_silence_ratio(samples, sample_rate)
    if result.silence_ratio > MAX_SILENCE_RATIO:
        result.issues.append(f"Too much silence ({result.silence_ratio:.0%}). Trim dead air or speak sooner after pressing record.")

    # RMS level warnings
    if result.rms_db < -30:
        result.issues.append("Recording is very quiet. Move closer to the microphone or increase input gain.")
    elif result.rms_db > -6:
        result.issues.append("Recording is very loud. Reduce input gain to avoid distortion.")

    # Quality scoring
    score_points = 0

    # SNR scoring (0-40 points)
    if result.snr_db >= SNR_THRESHOLD_A:
        score_points += 40
    elif result.snr_db >= SNR_THRESHOLD_B:
        score_points += 30
    elif result.snr_db >= SNR_THRESHOLD_C:
        score_points += 20
    else:
        score_points += 10

    # Duration scoring (0-20 points)
    if MIN_DURATION_SECONDS <= result.duration_seconds <= MAX_DURATION_SECONDS:
        score_points += 20
    elif result.duration_seconds > 1.0:
        score_points += 10

    # No clipping (0-20 points)
    if not result.has_clipping:
        score_points += 20

    # Silence ratio (0-20 points)
    if result.silence_ratio < 0.2:
        score_points += 20
    elif result.silence_ratio < MAX_SILENCE_RATIO:
        score_points += 10

    # Map to letter grade
    if score_points >= 85:
        result.quality_score = "A"
    elif score_points >= 65:
        result.quality_score = "B"
    elif score_points >= 45:
        result.quality_score = "C"
    else:
        result.quality_score = "D"

    # Suggestions for improvement
    if result.snr_db < SNR_THRESHOLD_B:
        result.suggestions.append("Try recording in a quieter room or closer to the microphone.")
    if not result.suggestions and not result.issues:
        result.suggestions.append("Great recording! Keep it up.")

    return result


def analyze_audio_file(file_path: Path) -> AudioAnalysisResult:
    """Analyze a WAV file from disk."""
    with open(file_path, "rb") as f:
        return analyze_audio(f.read())
