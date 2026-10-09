# Hello Farmer (ሄሎ ፋርመር)

> **AI-Powered Conversational Agricultural Voice & Web Platform for Ethiopian Farmers**

Hello Farmer enables Ethiopian smallholder and commercial farmers to access grounded, actionable agronomic advice in **Amharic (አማርኛ)**, **Afaan Oromoo**, and **English**.

The platform provides dual access modes:
1. **National Telephone Voice Line (8028)**: Farmers with ordinary mobile phones can dial **8028** toll-free, speak naturally without keypad menus or DTMF presses, and hear spoken advice.
2. **Modern Web Application (`http://localhost:3000`)**: An agricultural AI platform featuring conversational chat, voice input, agro-meteorological risk forecasts, crop yield prediction, and call history.

---

## 1. Brand Identity & Visual Design System

The visual design is anchored in the official **Hello Farmer Emblem**:
* **Tech Circuit Board (Left Hemisphere)**: Deep agricultural emerald and forest green (`#164234`, `#1E5642`), symbolizing high-tech speech AI.
* **Farmer with Mobile Handset (Center)**: Ethiopian farmer wearing a traditional Netela/Gabi, speaking on a mobile handset receiving voice waves.
* **Teff & Wheat Wreath (Right Hemisphere)**: Warm harvest gold and ripe teff grain ears (`#C69214`, `#D4AF37`), connecting the technology directly to Ethiopian soil and harvests.

---

## 2. End-to-End System Architecture

```mermaid
flowchart TD
    Caller[Farmer Telephone / MicroSIP 1001] -->|SIP G.711 / UDP 5060| Asterisk[Asterisk 20 LTS Telephony]
    Asterisk -->|AudioSocket 8kHz Linear PCM / TCP 9092| Bridge[Python AudioSocket TCP Server]

    subgraph Core Pipeline [Conversational Agricultural Pipeline]
        Bridge --> VAD[Energy VAD / Speech Endpointing]
        VAD --> Resample[Audio Resampling 8kHz to 16kHz]
        Resample --> STT[STT: Groq Whisper-Large-V3 / Gemini]
        STT --> LangDet[Language & Dialect Identification]
        LangDet --> Retrieval[pgvector Agricultural Knowledge Base]
        LangDet --> Weather[Open-Meteo Agro-Weather API]
        Retrieval --> LLM[LLM Reasoning: Groq Qwen / Gemini 2.5]
        Weather --> LLM
        LLM --> Guardrails[Safety & Dosage Guardrails]
        Guardrails --> TTS[TTS: Edge-TTS MekdesNeural / AmehaNeural]
        TTS --> Downsample[Downsample 16kHz to 8kHz Linear PCM]
    end

    Downsample --> Bridge
    Bridge --> Asterisk
    Asterisk --> Caller

    subgraph Web & Background Services
        Guardrails --> DB[(PostgreSQL + pgvector)]
        Guardrails --> Worker[arq Redis Background Worker]
        Worker --> SMS[Farmer SMS Dispatcher]
        Web[Next.js 14 Web Portal] -->|FastAPI REST| DB
    end
```

---

## 3. Key Web Application Modules

* **Home Dashboard**: Welcoming seasonal greeting, instant "Ask Hello Farmer" query bar, 8028 telephone hotline status, and quick advisory pills.
* **AI Agricultural Advisor**: Grounded conversational chat with Amharic/Afaan Oromo Unicode font support, suggested farming questions, Knowledge Base verification tags, and source citations.
* **Voice Agent 8028 & Web Mic**: Browser speech recognition alongside MicroSIP softphone connection credentials (1001/1002 on 127.0.0.1:5060).
* **Weather & Agro-Risk Alerts**: Live Open-Meteo forecasts with chemical spraying risk evaluations, planting soil moisture indices, and rainfall warnings.
* **Crop Yield Predictor**: EIAR-grounded yield estimator for Teff, Maize, Wheat, Coffee, and Barley with soil type and fertilizer inputs.
* **Call & SMS History**: Anonymized farmer profile, recent telephony call logs, and simulated SMS dispatch summaries.
* **Platform Analytics**: Telephony metrics, grounded answer rates, active warnings, and average system latency.

---

## 4. Quickstart: Running the Application

### Option A: With Docker Compose (Recommended)

Start the entire containerized stack (Next.js Frontend, FastAPI Backend, Asterisk 20, PostgreSQL + pgvector, Redis, Arq Worker):

```bash
# 1. Ensure .env is populated with your API keys
cp .env.example .env

# 2. Build and launch all services
docker compose up -d

# 3. Check running status
docker compose ps
```

#### Services Exposed:
* **Web Application**: [`http://localhost:3000`](http://localhost:3000)
* **Backend API & Docs**: [`http://localhost:8000/docs`](http://localhost:8000/docs)
* **Asterisk SIP Signaling**: `localhost:5060` (UDP & TCP)
* **AudioSocket Internal TCP Server**: `localhost:9092` (TCP)

---

### Option B: Running the Frontend Separately for Development

```bash
cd frontend
npm install
npm run dev
```

The frontend will be live on `http://localhost:3000` with hot-reloading.

---

## 5. Environment Variables (`.env`)

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `GROQ_API_KEY` | Groq API Key for Whisper STT and Qwen/Llama LLM | `gsk_...` |
| `GEMINI_API_KEY` | Google Gemini API Key | `AIza...` |
| `LLM_PROVIDER` | Active LLM Provider (`groq` or `gemini`) | `groq` |
| `DATABASE_URL` | PostgreSQL with pgvector connection URL | `postgresql+asyncpg://farmer:farmerpass@postgres:5432/hello_farmer` |
| `REDIS_URL` | Redis URL for caching and task queues | `redis://redis:6379/0` |
| `VAD_ENERGY_THRESHOLD` | Microphone Voice Activity Detection Energy RMS | `700` |
| `SPEECH_SILENCE_TIMEOUT_MS`| Silence pause to trigger end of caller utterance | `800` |
| `AUDIOSOCKET_PORT` | Asterisk AudioSocket TCP listening port | `9092` |

---

## 6. Testing MicroSIP Softphone (Call 8028)

1. Download and open **MicroSIP** (or Linphone / Zoiper).
2. Configure account settings:
   * **SIP Server**: `127.0.0.1:5060`
   * **Username**: `1001`
   * **Domain**: `127.0.0.1`
   * **Password**: `FarmerPass1001!`
3. Dial **8028** and speak into your microphone in Amharic or Afaan Oromo.

---

## 7. Knowledge Base & Pipeline Evaluation CLI

The repository includes dedicated CLI utilities for ingestion, benchmarking, and telephony verification:

```bash
# 1. Ingest official agronomic manuals into pgvector database
python scripts/ingest_kb.py

# 2. Pre-render fixed Amharic & Afaan Oromo prompt WAV files
python scripts/render_prompts.py --lang all

# 3. Test speech-to-text recognition accuracy with Groq Whisper
python scripts/test_stt.py

# 4. Test LLM latency and structured JSON output
python scripts/test_groq_llm.py

# 5. Run end-to-end conversational audio pipeline
python scripts/test_pipeline.py

# 6. Simulate synthetic telephone call over AudioSocket
python scripts/simulate_call.py
```