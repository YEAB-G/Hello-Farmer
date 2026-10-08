"""Abstract interface for Speech-to-Text (STT) providers."""
from abc import ABC, abstractmethod

from pydantic import BaseModel


class Transcript(BaseModel):
    text: str
    confidence: float
    provider: str
    latency_ms: float
    language: str


class BaseSTTProvider(ABC):
    @abstractmethod
    async def transcribe(self, wav_path_or_bytes: str | bytes, language: str = "am") -> Transcript:
        """Transcribe speech audio into text.

        Args:
            wav_path_or_bytes: Filepath or raw WAV/PCM audio bytes.
            language: Target ISO language code ('am' or 'om').

        Returns:
            Transcript containing text, confidence score, provider name, and latency.
        """
