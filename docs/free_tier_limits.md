# Free-Tier Limits and Constraints (docs/free_tier_limits.md)

*Last verified date: October 2026*  
*Scope: Providers evaluated for Hello Farmer MVP free-tier operation.*

---

## 1. LLM Providers

### 1.1 Google Gemini API (Google AI Studio)
- **Primary Model**: `gemini-2.5-flash` / `gemini-1.5-flash`
- **Cost**: Free tier available via Google AI Studio API key (`GEMINI_API_KEY`).
- **Free Quotas**:
  - Request Limit: 15 Requests Per Minute (RPM).
  - Daily Limit: 1,500 Requests Per Day (RPD).
  - Token Limit: 1,000,000 Tokens Per Minute (TPM).
- **Languages Verified**:
  - Amharic (`am`): Supported with high fluency in Ge'ez script.
  - Afaan Oromo (`om`): Supported in Latin Qubee script.
- **Data Policy**: Google AI Studio free tier terms allow Google to use prompt and response data for product improvement. Therefore, **personal identifiable data (farmer names, phone numbers) must NEVER be transmitted**. Only anonymized query text and retrieved knowledge chunks are sent.

### 1.2 Groq (Fallback Tier 1)
- **Primary Model**: `llama-3.1-8b-instant` / `llama-3.3-70b-versatile`
- **Cost**: Free tier via Groq Cloud API key (`GROQ_API_KEY`).
- **Free Quotas**:
  - Request Limit: 30 RPM, 14,400 RPD.
  - Token Limit: 6,000 to 20,000 TPM depending on model tier.
- **Languages**:
  - Amharic: Basic to moderate (requires careful prompting in Amharic script).
  - Afaan Oromo: Moderate Latin script capability.
- **Data Policy**: Groq does not train on customer inputs submitted via standard API endpoints.

### 1.3 OpenRouter `:free` (Fallback Tier 2)
- **Models**: Free routing endpoints (e.g. `meta-llama/llama-3.2-3b-instruct:free`, `google/gemini-2.0-flash-exp:free`).
- **Quotas**: Rate-limited dynamically based on community availability.
- **Usage**: Used strictly when primary Gemini and Groq quotas are exhausted.

### 1.4 Ollama (Local Fallback Tier 3)
- **Model**: `qwen2.5:7b` or `llama3.2:3b` running locally on NVIDIA GPU.
- **Cost**: $0 (100% offline).
- **Languages**: Lower accuracy for Ethiopian languages compared to cloud frontier models, but ensures zero-crash fallback.
- **Data Policy**: 100% private and on-premises.

---

## 2. Speech-to-Text (STT) Providers

### 2.1 Meta MMS (`facebook/mms-1b-all`)
- **Type**: Local PyTorch / Transformers model.
- **Adapters**:
  - `amh` (Amharic)
  - `orm` (Oromo)
- **Cost**: $0 (runs locally on GPU/CPU).
- **Hardware Footprint**: ~3.8 GB VRAM / RAM. Fast inference on NVIDIA GPU (RTX series).

### 2.2 Faster-Whisper / Fine-Tuned Whisper
- **Type**: Local CT2-based Whisper models.
- **Cost**: $0.
- **Amharic / Oromo Performance**: Native Whisper small/medium has moderate Amharic representation; specialized Hugging Face fine-tunes (`amharic-whisper`) improve performance.

### 2.3 Gemini Multimodal STT (Audio Input)
- **Type**: Audio bytes passed to Gemini Flash with transcription prompt.
- **Cost**: Shared within Gemini free tier quota.
- **Latency**: ~1.5s - 3s over network.

---

## 3. Text-to-Speech (TTS) Providers

### 3.1 Meta MMS-TTS
- **Models**: `facebook/mms-tts-amh` (Amharic), `facebook/mms-tts-gaz` / `orm` (Oromo).
- **Type**: Local VITS-based acoustic model.
- **Cost**: $0.
- **Characteristics**: Fast, lightweight, authentic phonetic pronunciation, raw 16 kHz output easily downsampled to 8 kHz for telephony.

### 3.2 Microsoft Edge TTS (`edge-tts`)
- **Status**: Free community endpoint wrapper (PROTOTYPE ONLY).
- **Voices**: `am-ET-AmehaNeural` (Male), `am-ET-MekdesNeural` (Female).
- **Cost**: $0 (no API key required).
- **Characteristics**: High naturalness, neural synthesis, network-dependent.

---

## 4. Weather API

### 4.1 Open-Meteo
- **Endpoint**: `https://api.open-meteo.com/v1/forecast`
- **Cost**: Free for non-commercial use up to 10,000 daily API calls.
- **API Key**: Not required for standard free tier.
- **Parameters**: Precipitation sum, precipitation probability, wind speed, temperature, 7-day forecast.
- **Terms & Data Policy**: Open database, no personal data sent (only latitude and longitude coordinates).
