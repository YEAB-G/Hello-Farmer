# Provider Integration Notes (docs/provider_notes.md)

This document details integration specifications, data privacy practices, audio parameters, and language capabilities for external and local AI services used in Hello Farmer.

---

## 1. Provider Comparison & Selection Matrix

| Component | Selected Primary | Fallback 1 | Fallback 2 | Offline Fallback |
|---|---|---|---|---|
| **STT** | Meta MMS 1B (`amh`/`orm`) | Faster-Whisper | Gemini Audio STT | Error prompt |
| **TTS** | Edge TTS (`am-ET-AmehaNeural`) | Meta MMS-TTS | Cached pre-rendered WAV | Static audio |
| **LLM** | Google Gemini Flash | Groq Cloud | OpenRouter Free | Ollama (Local) |
| **Embeddings** | BAAI/bge-m3 | intfloat/multilingual-e5-large | - | Local PyTorch |
| **Weather** | Open-Meteo | Mock Weather Service | - | Cached records |
| **SMS** | Mock SMS Provider | - | - | SQLite / DB log |

---

## 2. Privacy & Data Handling Per Provider

### 2.1 Audio & Telephony Isolation
- **Rule**: AudioSocket streams are processed strictly inside the local network.
- **Audio Files**: Raw audio is NEVER forwarded to third-party APIs except when Gemini STT is explicitly chosen as STT provider in config.
- **Transcripts**: Cleaned transcripts sent to LLMs must be stripped of any caller identifiers (caller phone numbers are replaced by anonymous session hashes).

### 2.2 Google Gemini API
- **Endpoint**: Google AI SDK via `google-genai` / `google-generativeai`.
- **System Instructions**: Strict system prompt enforcing 3-sentence limit, non-invented agronomic advice, and Ge'ez/Latin script formatting.
- **Data Policy Notice**: Free-tier prompts may be logged by Google; sensitive identification information is strictly withheld.

### 2.3 Edge-TTS
- **Protocol**: WebSocket connection to Microsoft Edge read-aloud service.
- **Voices**:
  - `am-ET-AmehaNeural`
  - `am-ET-MekdesNeural`
- **Output**: 24 kHz MP3 or 16 kHz PCM, converted locally via `audio/convert.py` to 8 kHz mono linear PCM for Asterisk streaming.

---

## 3. Audio Specifications
- **Asterisk Telephony Audio**: 8,000 Hz sample rate, 16-bit signed linear PCM (slin), mono.
- **STT Processing**: Resampled to 16,000 Hz mono 16-bit PCM (standard input for Whisper and MMS).
- **TTS Synthesis**: Generated at native rate (16 kHz / 24 kHz) and resampled to 8 kHz mono PCM before streaming into AudioSocket.
- **Silero VAD**: 16 kHz mono float32/int16 frames with 30ms-50ms chunk sizes.
