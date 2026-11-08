# Hello Farmer: Implementation Plan & Migration Roadmap

This document outlines the strict execution roadmap for upgrading Hello Farmer into an offline-capable, multilingual agricultural voice intelligence platform.

---

## 1. Inventory of Preserved Reusable Components

In adherence to non-negotiable engineering rules, the following components are verified as working and **must NOT be replaced or deleted**:

| Component / File Path | Current Status | Why It Must Be Preserved |
| :--- | :--- | :--- |
| `backend/app/telephony/call_flow.py` | Working | Core state machine managing 20ms AudioSocket framing, session lifecycles, and bidirectional audio streaming. Leading whitespace bug was fixed. |
| `backend/app/telephony/audiosocket.py` | Working | Valid RFC-compliant AudioSocket TCP protocol handler implementing UUID parsing and Linear PCM packet encoding. |
| `backend/app/rag/embed.py` | Working | Recently enhanced with `DeterministicSubwordEmbeddingProvider` (Rule 9 compliant, 384-d dense vectors) and `LocalSentenceTransformerEmbeddingProvider`. |
| `backend/app/rag/retrieve.py` | Working | Full hybrid retrieval implementation: custom Ethiopian Ge'ez/Latin tokenizer, BM25 scoring, Reciprocal Rank Fusion ($k=60$), and agroecological boosting. |
| `backend/app/services/weather.py` | Working | Lightweight asynchronous HTTP client integrating Open-Meteo for agricultural coordinates (e.g., Debre Birhan, Bako, Hawassa) with offline default structures. |
| `backend/app/llm/guardrails.py` | Working | Agricultural safety rules: chemical dosage sanitization, forbidden pesticide checks (paraquat, DDT), and mandatory extension referral for catastrophic blights. |
| `backend/app/db/models.py` | Working | Core SQLAlchemy models: `Farmer`, `CallRecord`, `KnowledgeChunk`, and `AdvisoryRecord`. Fully compatible with pgvector. |
| `backend/app/db/session.py` | Working | Asynchronous SQLAlchemy connection pooling with environment-driven database URL. |
| `docker-compose.yml` (Base layout) | Working | Multi-container composition uniting Asterisk, PostgreSQL 16 pgvector, Redis 7, Backend, Worker, and Frontend. |
| `frontend/` (Next.js Application) | Working | Clean agricultural advisory dashboard and web voice demo using Tailwind CSS and Radix UI. |

---

## 2. Phase-by-Phase Implementation Roadmap

```mermaid
flowchart LR
    P2["Phase 2: Security & Credentials Hardening"] --> P3["Phase 3: Hohe ASR & Mock Elimination"]
    P3 --> P4["Phase 4: Local Neural TTS (Piper)"]
    P4 --> P5["Phase 5: Knowledge Ingestion & Trust Tiering"]
    P5 --> P6["Phase 6: Database Migrations (Alembic)"]
    P6 --> P7["Phase 7: Real Audio Latency & Eval Harness"]
    P7 --> P8["Phase 8: Telephony Carrier & Barge-in"]
    P8 --> P9["Phase 9: Production SMS Gateway"]
    P9 --> P10["Phase 10: Prometheus & Grafana Observability"]
```

---

### Phase 2: Security Hardening & Secret Protection
**Target Gaps**: GAP-05, GAP-06, GAP-07, GAP-09, GAP-10  
**Priority**: CRITICAL  

1. **Eliminate Exposed SIP Credentials**:
   - In `backend/app/main.py` (`GET /api/v1/voice-agent/status`), remove plaintext passwords for extensions `1001` and `1002`. Return status as registered/active without credential payloads.
2. **Implement Admin & History Authentication**:
   - Add HTTP Bearer / API Key authentication dependency (`admin_required`) to call history endpoints (`/api/v1/voice/history`), farmer profiles (`/api/v1/farmers`), and admin analytics (`/api/v1/admin/*`).
3. **Restrict Network Port Binding**:
   - In `docker-compose.yml`, bind PostgreSQL (`5432`) and Redis (`6379`) to `127.0.0.1` instead of `0.0.0.0` to prevent direct exposure over public host interfaces.
4. **Harden CORS Configuration**:
   - Update `CORSMiddleware` in `backend/app/main.py`: Replace wildcard `allow_origins=["*"]` when `allow_credentials=True` with explicit configurable allowed origins (`http://localhost:3000`, production domain).
5. **Configuration Sanitization**:
   - Audit `backend/app/config.py` to ensure all secret keys, database passwords, and encryption keys enforce fail-fast validation in production mode (preventing fallback to hardcoded default strings).

*Exit Criteria & Automated Tests*:
- Unauthenticated requests to `/api/v1/voice/history` return `401 Unauthorized`.
- `/api/v1/voice-agent/status` returns extension statuses without passwords.
- Security tests pass (`tests/test_security_audit.py`).

---

### Phase 3: Hohe Amharic ASR Verification & Mock Removal
**Target Gaps**: GAP-01, GAP-02  
**Priority**: HIGH  

1. **Remove Hardcoded Mock ASR Fallbacks**:
   - In `backend/app/stt/whisper_local.py`, eliminate lines 38-47 that return `"ጤፍ ላይ ቢጫ ቅጠል ታይቷል"` on transcription failure. Return an explicit error code or empty transcript string with low confidence.
2. **Implement Dedicated Hohe ASR Adapter**:
   - Create `backend/app/stt/hohe_asr.py`:
     - Load `snapwre/hohe-asr-amharic` (Wav2Vec2-BERT / Conformer-CTC) using HuggingFace Transformers / ONNX Runtime.
     - Add 8kHz-to-16kHz audio upsampling using `scipy.signal.resample` or `soxr`.
     - Output transcribed Amharic text alongside acoustic confidence scores.
3. **Pluggable STT Router**:
   - Update `backend/app/stt/router.py` to select between Hohe (Amharic primary), Whisper (multilingual/Oromo), and Vosk (ultra-low-spec CPU), with zero simulated fallback transcripts.

*Exit Criteria & Automated Tests*:
- Unit tests verify that uninitialized or failing STT raises an explicit exception or returns zero confidence, never returning canned text.
- Clean synthetic silence audio generates empty transcription without hallucinations.
- `tests/test_stt_verification.py` passes.

---

### Phase 4: Local Offline Amharic TTS Pipeline (Piper ONNX)
**Target Gaps**: GAP-04  
**Priority**: HIGH  

1. **Replace Acoustic Beep Synthesizer**:
   - In `backend/app/tts/fallback_synth.py`, deprecate modulated sine-wave generation for agricultural responses.
2. **Integrate Piper Neural Amharic Engine**:
   - Create `backend/app/tts/piper_local.py`:
     - Integrate Piper TTS engine with pre-trained Amharic ONNX model checkpoint (`am_ET`).
     - Produce 16kHz or 22.05kHz 16-bit PCM audio, downsampled to 8kHz Linear PCM for AudioSocket compatibility.
     - Ensure Real-Time Factor (RTF) is under 0.35 on modern multi-core x86 CPU.
3. **TTS Fallback Hierarchy**:
   - Level 1: Local Piper ONNX (Offline, deterministic, low-latency).
   - Level 2: Edge-TTS (When internet is active and highest acoustic fidelity is desired).
   - Level 3: Pre-recorded audio prompts (Canned studio prompts for standard telecom system messages like greetings and errors).

*Exit Criteria & Automated Tests*:
- Offline synthesis produces valid WAV/PCM audio stream containing human-decodable Amharic speech.
- `tests/test_tts_pipeline.py` verifies PCM frame alignment and sample rate conformity.

---

### Phase 5: Knowledge Ingestion & Trust Tiering Guardrails
**Target Gaps**: GAP-08  
**Priority**: MEDIUM  

1. **Provenance Enforcement**:
   - Modify `backend/app/rag/ingest.py`: Reject or quarantine documents uploaded without verified metadata (`publisher`, `publication_date`, `license`, `agroecological_zone`).
2. **Strict Trust Tier Mapping**:
   - Tier 1: Ministry of Agriculture (MoA), Ethiopian Institute of Agricultural Research (EIAR), CGIAR centers (ILRI, CIMMYT, ICARDA).
   - Tier 2: Academic publications (Addis Ababa University, Haramaya University, Hawassa University) and verified regional bureaus.
   - Tier 3: Unverified community or web sources (Quarantined by default; excluded from automated voice answers until approved by agronomist).
3. **Cryptographic Checksumming**:
   - Compute SHA-256 hash of each ingested file to ensure document integrity and prevent duplicate ingestion.

*Exit Criteria & Automated Tests*:
- Ingestion of unverified documents without publisher metadata fails validation with `422 Unprocessable Entity`.
- Only Tier 1 and Tier 2 chunks are returned in voice RAG pipelines.
- `tests/test_ingest_provenance.py` passes.

---

### Phase 6: Database Migrations (Alembic)
**Target Gaps**: GAP-12  
**Priority**: MEDIUM  

1. **Initialize Alembic Environment**:
   - Setup `backend/alembic/` with `env.py` and `alembic.ini`.
   - Wire `target_metadata = Base.metadata` from `app.db.models`.
2. **Generate Baseline Migration**:
   - Create revision `0001_initial_schema.py` capturing:
     - `farmers` table with encrypted phone index and geographic metadata.
     - `call_records` table with duration, language, and resolution status.
     - `knowledge_chunks` table with pgvector column (`vector(384)` and `vector(1024)`) and HNSW index.
     - `advisory_records` table for post-call SMS logs.
3. **Container Migration Hook**:
   - Update backend startup script (`entrypoint.sh`) to execute `alembic upgrade head` before launching Uvicorn/AudioSocket.

*Exit Criteria & Automated Tests*:
- `alembic check` succeeds cleanly without pending model drifts.
- Tests verify schema creation via migration.

---

### Phase 7: Real Voice Latency Harness & Audio Benchmark
**Target Gaps**: GAP-03  
**Priority**: MEDIUM  

1. **Real Audio Benchmark Dataset**:
   - In `eval/stt_benchmark.py`, deprecate synthetic sine wave tone generation.
   - Add reference corpus of human-spoken Amharic audio samples (WAV format, 8kHz and 16kHz) with gold-standard transcription ground truth.
2. **Full Pipeline Latency Measurement**:
   - Update `eval/latency_report.py`: Ingest actual audio files into the full end-to-end stack (VAD -> STT -> Language Identification -> Hybrid RAG -> LLM -> TTS -> AudioSocket framing).
   - Measure and report breakdown: VAD latency, STT latency, RAG retrieval time, LLM Time-to-First-Token (TTFT), and TTS synthesis time.

*Exit Criteria & Automated Tests*:
- Benchmark outputs valid Word Error Rate (WER) and Character Error Rate (CER) based on human speech.
- Latency benchmark reports true end-to-end voice latency.

---

### Phase 8: Telephony Carrier Readiness, Trunking Documentation & Sub-200ms Barge-In
**Target Gaps**: GAP-13  
**Priority**: MEDIUM  

1. **Carrier SIP Trunk Configuration**:
   - Provide complete Asterisk PJSIP configuration templates for Ethio Telecom and Safaricom Ethiopia interconnects (E1/PRI and SIP trunking).
   - Configure jitter buffers, direct media controls, and RFC 2833 DTMF handling.
2. **Sub-200ms AudioSocket Barge-In**:
   - Optimize speech-interruption cancellation in `backend/app/telephony/call_flow.py`:
     - When VAD detects user speech while TTS is streaming audio, immediately send an interrupt frame to Asterisk, cancel background synthesis tasks, and flush TCP output buffers within 200ms.

*Exit Criteria & Automated Tests*:
- Simulated caller interruption stops TTS playback within 200ms.
- Asterisk dialplan documentation verified against carrier interconnect specs.

---

### Phase 9: Production SMS Gateway Client
**Target Gaps**: GAP-11  
**Priority**: LOW  

1. **Production Gateway Integrations**:
   - Implement production SMS provider adapters in `backend/app/services/sms.py`:
     - Ethio Telecom Bulk SMS API.
     - Africa's Talking Ethiopia SMS gateway.
     - Local GSM modem / SMPP protocol fallback.
2. **Message Formatting & UCS-2 Ge'ez Encoding**:
   - Implement strict 70-character UCS-2 Ge'ez SMS chunking to prevent message corruption or unexpected multi-part charges.

*Exit Criteria & Automated Tests*:
- Mock gateway test verifies correct UCS-2 Ge'ez text encoding and phone number E.164 normalization.

---

### Phase 10: Prometheus Metrics Exporter & Grafana Dashboards
**Target Gaps**: GAP-14  
**Priority**: LOW  

1. **Prometheus Metrics Instrumentation**:
   - Expose `/metrics` on FastAPI backend:
     - `voice_calls_active_count` (Gauge)
     - `voice_call_duration_seconds` (Histogram)
     - `voice_pipeline_latency_ms` (Histogram by component: vad, stt, rag, llm, tts)
     - `rag_retrieval_reciprocal_rank` (Histogram)
     - `safety_guardrail_blocks_total` (Counter by rule)
2. **Grafana Dashboard Definition**:
   - Add pre-configured dashboard JSON in `docker/grafana/dashboards/` displaying telephony health, ASR/TTS performance, and system resource consumption.

*Exit Criteria & Automated Tests*:
- `GET /metrics` returns valid Prometheus exposition format.

---

## 3. Strict Execution Order Summary

| Step # | Phase Name | Primary Files Touched |
| :---: | :--- | :--- |
| **1** | **Phase 2: Security Hardening** | `backend/app/main.py`, `backend/app/config.py`, `docker-compose.yml`, `tests/test_security_audit.py` |
| **2** | **Phase 3: Hohe ASR & Mock Removal** | `backend/app/stt/whisper_local.py`, `backend/app/stt/hohe_asr.py`, `backend/app/stt/router.py`, `tests/test_stt_verification.py` |
| **3** | **Phase 4: Local Neural TTS (Piper)** | `backend/app/tts/fallback_synth.py`, `backend/app/tts/piper_local.py`, `backend/app/tts/router.py`, `tests/test_tts_pipeline.py` |
| **4** | **Phase 5: Knowledge Ingestion & Trust** | `backend/app/rag/ingest.py`, `backend/app/rag/retrieve.py`, `tests/test_ingest_provenance.py` |
| **5** | **Phase 6: Database Migrations** | `backend/alembic/`, `backend/alembic.ini`, `backend/entrypoint.sh` |
| **6** | **Phase 7: Real Audio Latency Harness** | `eval/stt_benchmark.py`, `eval/latency_report.py`, `eval/audio_samples/` |
| **7** | **Phase 8: Telephony & Barge-In** | `backend/app/telephony/call_flow.py`, `asterisk/pjsip.conf`, `asterisk/extensions.conf` |
| **8** | **Phase 9: Production SMS Gateway** | `backend/app/services/sms.py`, `backend/app/worker.py` |
| **9** | **Phase 10: Prometheus Observability** | `backend/app/main.py`, `backend/app/telephony/call_flow.py`, `docker-compose.yml` |

---

*Verified and aligned with all 20 non-negotiable engineering rules.*
