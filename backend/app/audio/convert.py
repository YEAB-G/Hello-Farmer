"""Audio conversion, resampling, and format utilities.

Handles conversions between:
- 8 kHz 16-bit mono PCM (Asterisk AudioSocket / Telephony)
- 16 kHz 16-bit mono PCM / float32 (Silero VAD / MMS STT / Whisper STT)
- G.711 mulaw / alaw simulation for telephony evaluation
- Conversion from container formats (MP3/WAV/OGG) to 8 kHz mono linear PCM via ffmpeg
"""
import io
import subprocess

import numpy as np
import scipy.signal
import soundfile as sf


def pcm8k_to_pcm16k(pcm_data: bytes) -> bytes:
    """Resample raw 8 kHz 16-bit mono linear PCM to 16 kHz 16-bit mono PCM."""
    if not pcm_data:
        return b""
    samples = np.frombuffer(pcm_data, dtype=np.int16)
    resampled = scipy.signal.resample_poly(samples, 2, 1).astype(np.int16)
    return resampled.tobytes()


def pcm16k_to_pcm8k(pcm_data: bytes) -> bytes:
    """Downsample raw 16 kHz 16-bit mono linear PCM to 8 kHz 16-bit mono PCM."""
    if not pcm_data:
        return b""
    samples = np.frombuffer(pcm_data, dtype=np.int16)
    resampled = scipy.signal.resample_poly(samples, 1, 2).astype(np.int16)
    return resampled.tobytes()


def pcm_to_float32(pcm_data: bytes) -> np.ndarray:
    """Convert int16 PCM bytes to float32 numpy array normalized to [-1.0, 1.0]."""
    samples = np.frombuffer(pcm_data, dtype=np.int16)
    return samples.astype(np.float32) / 32768.0


def float32_to_pcm(audio_float: np.ndarray) -> bytes:
    """Convert float32 numpy array to int16 PCM bytes."""
    clipped = np.clip(audio_float, -1.0, 1.0)
    samples = (clipped * 32767.0).astype(np.int16)
    return samples.tobytes()


def simulate_g711_ulaw(pcm_data: bytes) -> bytes:
    """Simulate G.711 u-law compression and decompression on 8 kHz PCM audio."""
    if not pcm_data:
        return b""
    import audioop
    ulaw_bytes = audioop.lin2ulaw(pcm_data, 2)
    return audioop.ulaw2lin(ulaw_bytes, 2)


def audio_stream_to_pcm8k(audio_bytes: bytes) -> bytes:
    """Transcode any audio format (MP3, WAV, AAC, etc.) to 8 kHz 16-bit mono linear PCM."""
    if not audio_bytes:
        return b""
    try:
        proc = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel", "error",
                "-i", "pipe:0",
                "-af", "volume=1.5,lowpass=f=3800",
                "-f", "s16le",
                "-acodec", "pcm_s16le",
                "-ac", "1",
                "-ar", "8000",
                "pipe:1"
            ],
            input=audio_bytes,
            capture_output=True,
            check=True
        )
        return proc.stdout
    except Exception:
        # Fallback using soundfile if ffmpeg pipe fails
        try:
            data, sr = sf.read(io.BytesIO(audio_bytes), dtype="int16")
            if len(data.shape) > 1:
                data = data.mean(axis=1).astype(np.int16)
            if sr == 8000:
                return data.tobytes()
            elif sr == 16000:
                return pcm16k_to_pcm8k(data.tobytes())
            else:
                num_target_samples = int(len(data) * 8000 / sr)
                resampled = scipy.signal.resample(data, num_target_samples).astype(np.int16)
                return resampled.tobytes()
        except Exception:
            return b""


def pcm8k_to_wav(pcm_data: bytes) -> bytes:
    """Wrap raw 8 kHz 16-bit mono linear PCM bytes into standard WAV container."""
    samples = np.frombuffer(pcm_data, dtype=np.int16)
    buf = io.BytesIO()
    sf.write(buf, samples, 8000, format="WAV", subtype="PCM_16")
    return buf.getvalue()
