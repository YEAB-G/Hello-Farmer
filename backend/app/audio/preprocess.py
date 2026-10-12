"""Acoustic pre-processing module for Speech-to-Text (STT).

Enhances telephony and web audio prior to STT inference:
1. Automatic Gain Control (AGC) / RMS Normalization: Normalizes soft/loud callers to -20 dBFS.
2. Pre-emphasis Filtering: Boosts high-frequency consonant formants (ጠ, ጨ, ቀ, ተ, ከ) attenuated by telephone channels.
3. Clean 16 kHz Resampling: Generates pristine 16 kHz 16-bit linear mono WAV for STT models.
"""
import io
import wave
import numpy as np
import scipy.signal

try:
    from app.audio.convert import pcm8k_to_pcm16k
except ImportError:
    from backend.app.audio.convert import pcm8k_to_pcm16k


def apply_preemphasis(signal: np.ndarray, alpha: float = 0.97) -> np.ndarray:
    """Apply first-order high-frequency pre-emphasis filter: y[n] = x[n] - alpha * x[n-1].

    Args:
        signal: 1D float32 audio samples in range [-1.0, 1.0].
        alpha: Pre-emphasis coefficient (typically 0.95 - 0.97).

    Returns:
        Filtered audio signal with sharpened high-frequency consonant transients.
    """
    if len(signal) < 2:
        return signal
    # Fast vectorized FIR filter [1, -alpha]
    return np.append(signal[0], signal[1:] - alpha * signal[:-1]).astype(np.float32)


def apply_automatic_gain_control(
    signal: np.ndarray,
    target_rms: float = 0.08,
    max_gain: float = 8.0,
    min_gain: float = 0.2,
) -> np.ndarray:
    """Normalize speech loudness to standard target RMS energy level without clipping.

    Args:
        signal: 1D float32 audio samples in range [-1.0, 1.0].
        target_rms: Desired root-mean-square energy (approx -22 dBFS).
        max_gain: Maximum amplification factor for soft-spoken callers.
        min_gain: Minimum attenuation factor for loud callers.

    Returns:
        Gain-normalized audio signal clipped to [-1.0, 1.0].
    """
    if len(signal) == 0:
        return signal

    current_rms = float(np.sqrt(np.mean(signal**2)))
    # If silence or near-zero, do not amplify background noise
    if current_rms < 0.002:
        return signal

    gain = target_rms / current_rms
    gain = np.clip(gain, min_gain, max_gain)
    normalized = signal * gain
    return np.clip(normalized, -1.0, 1.0).astype(np.float32)


def preprocess_speech_for_stt(
    audio_bytes: bytes,
    is_8k_pcm: bool = True,
    apply_filter: bool = True,
) -> bytes:
    """Convert input telephony or web audio into optimized 16 kHz WAV for STT models.

    Args:
        audio_bytes: Raw 8 kHz 16-bit linear PCM bytes or standard WAV bytes.
        is_8k_pcm: True if input is raw 8 kHz telephony PCM; False if standard WAV.
        apply_filter: Whether to apply pre-emphasis and gain normalization.

    Returns:
        16 kHz 16-bit mono linear WAV bytes.
    """
    if not audio_bytes:
        return b""

    # 1. Decode bytes into float32 array and sample rate
    if audio_bytes.startswith(b"RIFF"):
        try:
            with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
                sr = wf.getframerate()
                n_frames = wf.getnframes()
                raw_frames = wf.readframes(n_frames)
                samples = np.frombuffer(raw_frames, dtype=np.int16).astype(np.float32) / 32768.0
        except Exception:
            return audio_bytes
    else:
        sr = 8000 if is_8k_pcm else 16000
        samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

    if len(samples) == 0:
        return b""

    # 2. Resample to 16 kHz if necessary
    if sr != 16000:
        target_len = int(len(samples) * 16000 / sr)
        samples = scipy.signal.resample(samples, target_len).astype(np.float32)
        sr = 16000

    # 3. Apply Acoustic Enhancements: AGC & Pre-emphasis
    if apply_filter:
        samples = apply_automatic_gain_control(samples, target_rms=0.08)
        samples = apply_preemphasis(samples, alpha=0.96)
        samples = np.clip(samples, -1.0, 1.0)

    # 4. Pack into 16 kHz 16-bit mono WAV container
    int16_samples = (samples * 32767.0).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(int16_samples.tobytes())

    return buf.getvalue()
