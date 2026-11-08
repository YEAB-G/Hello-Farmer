# Hello Farmer: Existing System Audit & Baseline Verification

**Audit Date:** November 2026  
**Auditor:** Senior AI/ML, Backend, Speech, Telephony Engineer & Software Architect  
**Target Repository:** `Hello-Farmer` (`feature/implementation-enhancements`)  
**Scope:** Complete architectural inspection across all 17 subsystems and investigation of known engineering anomalies.

---

## 1. Subsystem Classification Matrix

| # | Subsystem | Current Status | Key Files / Entrypoints | Verification Details |
|---|---|---|---|---|
| 1 | **FastAPI Core & Routes** | **NEEDS SECURITY REVIEW** | `backend/app/main.py` | 19 HTTP endpoints implemented. CORS allows `*` with credentials. Unprotected administrative endpoints. Cleartext SIP credentials exposed. |
| 2 | **Telephony & AudioSocket** | **IMPLEMENTED AND VERIFIED** | `backend/app/telephony/audiosocket_server.py`, `call_flow.py`, `endpointing.py` | AudioSocket TCP server on port 9092. Full-duplex buffer drainer, silence keepalive streamer (`start_keepalive`), and state machine turn-taking functional and verified with live MicroSIP calls. |
| 3 | **Asterisk PBX & Dialplan** | **IMPLEMENTED AND VERIFIED** | `asterisk/pjsip.conf`, `extensions.conf`, `modules.conf` | Asterisk 20 LTS running in Docker. Extension `8028` connects to AudioSocket. PJSIP endpoints 1001 and 1002 registered. Local dynamic IP script handles Wi-Fi/Tailscale NAT. |
| 4 | **Speech Recognition (STT)** | **PARTIALLY IMPLEMENTED** | `backend/app/stt/gemini_stt.py`, `hf_stt.py`, `groq_stt.py`, `whisper_local.py`, `router_stt.py` | Gemini Flash Lite and Groq Whisper work via cloud. `hf_stt.py` has local pipeline loader for `snapwre/hohe-asr-amharic` but needs offline model caching. `whisper_local.py` contained hardcoded canned fallback string. |
| 5 | **Speech Synthesis (TTS)** | **PARTIALLY IMPLEMENTED** | `backend/app/tts/edge_tts_provider.py`, `gemini_tts_provider.py`, `fallback_synth.py` | Edge-TTS works cleanly for Amharic (`am-ET-AmehaNeural`) and Oromo (`om-ET`). However, offline fallback (`fallback_synth.py`) generates a dual-sine acoustic tone (450Hz/1450Hz) rather than synthesized speech. |
| 6 | **Agricultural RAG & Embeddings** | **IMPLEMENTED AND VERIFIED** | `backend/app/rag/embed.py`, `retrieve.py`, `store.py`, `faq_cache.py` | Hybrid RAG (Dense Vector + BM25 Lexical + Reciprocal Rank Fusion) implemented. Pseudo-random hash embedding removed. HNSW index active on 8,335 PostgreSQL chunks. Semantic FAQ cache functional. |
| 7 | **LLM Reasoning & Prompts** | **IMPLEMENTED AND VERIFIED** | `backend/app/llm/prompts.py`, `gemini.py`, `groq.py`, `ollama.py`, `chain.py` | Versioned prompt `v3.0-gemini` enforces 3-step agronomic prescription, polite Ethiopian honorifics, numbers-to-words, and Pydantic JSON schema. Ollama local provider exists. |
| 8 | **Agricultural Safety Guardrails** | **IMPLEMENTED AND VERIFIED** | `backend/app/safety/guardrails.py` | Enforces Zero Chemical Hallucination rule, verified quantity matching, Arabic digits-to-words conversion, poison ingestion emergency routing, and mandatory Kebele DA referral. |
| 9 | **Farmer Context & Geocoding** | **IMPLEMENTED AND VERIFIED** | `backend/app/weather/location.py`, `backend/app/farmer_context/extraction.py` | Ethiopian locality extraction strips conversational prepositions. Resolves ~50 woredas/zones into geographic coordinates and agroecological zones (Dega, Woina Dega, Kolla, Bereha). |
| 10 | **Weather Integration** | **IMPLEMENTED AND VERIFIED** | `backend/app/weather/provider.py`, `risk.py` | Live Open-Meteo integration with 1-hour Redis and memory caching. Evaluates 7-day precipitation, soil moisture, and spray hazard windows. Offline mock provider exists. |
| 11 | **PostgreSQL & Database Models** | **IMPLEMENTED BUT NEEDS TESTING** | `backend/app/database/models.py`, `session.py` | SQLAlchemy async models for `Farmer`, `FarmerContext`, `Call`, `ConversationMessage`, `KnowledgeChunk`. Missing Alembic migration version control directory. |
| 12 | **Redis & Background Workers** | **PARTIALLY IMPLEMENTED** | `workers/worker.py`, `backend/app/sms/` | Redis 7 container healthy. `arq` worker handles post-call summary generation and weather evaluations. SMS provider is currently mock-only (`backend/app/sms/mock.py`). |
| 13 | **Next.js Web Portal** | **IMPLEMENTED AND VERIFIED** | `frontend/app/page.tsx`, `components/`, `utils/audioRecorder.ts` | Complete Next.js 14 dashboard with live Web Voice Chat, audio recorder, waveform visualizer, call log inspector, and bilingual Amharic/English UI. |
| 14 | **Docker Infrastructure** | **IMPLEMENTED AND VERIFIED** | `docker-compose.yml`, `backend/Dockerfile`, `asterisk/Dockerfile`, `frontend/Dockerfile` | 6-service stack (`backend`, `asterisk`, `frontend`, `postgres`, `redis`, `worker`) with healthchecks and volume mounts. |
| 15 | **Environment Configuration** | **NEEDS SECURITY REVIEW** | `.env`, `config.yaml`, `backend/app/config.py` | Typed settings via Pydantic. However, default `.env` contains insecure development secrets (`SECRET_KEY`, `PHONE_ENCRYPTION_KEY`). |
| 16 | **Evaluation Harness & Benchmarks**| **PARTIALLY IMPLEMENTED** | `eval/stt_benchmark.py`, `latency_report.py`, `rag_eval.py`, `answer_eval.py` | Extensive benchmark suites exist, but several harness scripts bypass real audio pipelines (using text overrides or synthetic sine waves). |
| 17 | **Agricultural Knowledge Sources** | **IMPLEMENTED AND VERIFIED** | `knowledge_base/raw/MoA Guidelines/`, `scripts/sync_moa_kb.py` | 80+ official MoA, EIAR, and FAO guidelines and crop production packages ingested. Over 8,335 vectorized chunks in pgvector. |

---

## 2. Forensic Investigation of Known Concerns

### 2.1 Random or Hash-Based Embedding Fallback
* **Audit Finding:** **CONFIRMED & REMEDIED IN PHASE 1**.
* **Prior Code:** In `backend/app/rag/embed.py` (lines 100-130), `_offline_hash_embedding` utilized `rng = np.random.RandomState(abs(hash(text)) % (2**31))` to generate pseudo-random Gaussian noise. Under Gemini 429 quota exhaustion, chunks and queries received arbitrary vectors.
* **Current State:** Completely eradicated in Phase 1. Replaced with `DeterministicSubwordEmbeddingProvider` (deterministic character n-gram/token FNV-1a projection maintaining semantic root alignment) and `LocalSentenceTransformerEmbeddingProvider`.

### 2.2 Fixed Example Transcript Returned After ASR Failure
* **Audit Finding:** **CONFIRMED IN REPOSITORY**.
* **Evidence:** In `backend/app/stt/whisper_local.py` (lines 38-47):
  ```python
  if self.model is None:
      # Fallback for testing / container without faster-whisper compiled
      latency_ms = (time.perf_counter() - start_time) * 1000.0
      return Transcript(
          text="ጤፍ ላይ ቢጫ ቅጠል ታይቷል" if language == "am" else "Baalli xaafii keelloo tahe",
          confidence=0.88,
          provider="whisper_mock",
          latency_ms=max(20.0, latency_ms),
          language=language,
      )
  ```
* **Impact:** If `faster-whisper` fails to load (due to missing CUDA/C++ runtimes), every spoken utterance is falsely transcribed as *"ጤፍ ላይ ቢጫ ቅጠል ታይቷል"* (*Yellow leaves seen on teff*). This directly violates Rule 8 ("Never return fake ASR transcripts"). Must be replaced with real local model inference or explicit failure propagation.

### 2.3 Synthetic Speech Used in ASR Evaluation
* **Audit Finding:** **CONFIRMED IN REPOSITORY**.
* **Evidence:** In `eval/stt_benchmark.py` (lines 80-89 & line 178):
  ```python
  def generate_synthetic_tone_wav(duration_s: float = 2.0, sample_rate: int = 16000) -> bytes:
      t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
      audio = 0.4 * np.sin(2 * np.pi * 200 * t) + 0.3 * np.sin(2 * np.pi * 800 * t)
      ...
  ```
  The benchmark harness feeds a 200Hz + 800Hz sine-wave tone into the speech recognizer instead of human speech. Because `whisper_local` returned the canned string above, the benchmark reported a false Word Error Rate (WER). Must be replaced with real pre-recorded Amharic/Oromo acoustic test vectors.

### 2.4 Latency Tests That Bypass the Actual Voice Pipeline
* **Audit Finding:** **CONFIRMED IN REPOSITORY**.
* **Evidence:** In `eval/latency_report.py` (lines 81-86):
  ```python
  res = await process_utterance(
      audio_bytes=None,
      session=session,
      text_override=item["q"],
      synthesize_audio=True,
  )
  ```
  The benchmark measures LLM and TTS latency, but passes `audio_bytes=None`, skipping AudioSocket streaming, VAD silence accumulation, audio format resampling, and speech recognition transcription.

### 2.5 Automatic Trust Assignment to Unknown Document Sources
* **Audit Finding:** **CONFIRMED IN REPOSITORY**.
* **Evidence:** In `backend/app/rag/ingest.py` (lines 46-55):
  ```python
  publisher = "Ministry of Agriculture, Ethiopia (MoA)"
  tier = 1
  if "ess data" in str(file_path).lower():
      publisher = "Ethiopian Statistical Service (ESS)"
  elif "fao" in stem.lower():
      publisher = "FAO / UN"
      tier = 2
  ```
  Any arbitrary document placed in the ingestion path lacking metadata automatically defaults to `source_tier = 1` and `publisher = "Ministry of Agriculture, Ethiopia (MoA)"`. Unverified agricultural forum posts or third-party PDFs could inherit top-tier authority. Ingestion must require explicit provenance or default unverified files to Tier 4 / Tier 0.

### 2.6 Exposed Credentials and Insecure Endpoints
* **Audit Finding:** **CONFIRMED IN REPOSITORY**.
* **Evidence:**
  1. `backend/app/main.py` lines 442-445: `GET /api/v1/voice-agent/status` publicly outputs cleartext SIP passwords:
     `{"ext": "1001", "password": "FarmerPass1001!", "status": "Available"}`.
  2. `backend/app/main.py` lines 398-421: `GET /api/v1/farmer/profile` returns private farmer phone hashes and locations without authentication.
  3. `backend/app/main.py` lines 478-615: `GET /api/v1/calls` returns unauthenticated full transcripts of caller conversations.
  4. `docker-compose.yml`: PostgreSQL port `5432:5432` and Redis port `6379:6379` are bound directly to `0.0.0.0` on the host without network firewall segregation or Redis password requirements.
  5. `backend/app/config.py`: Hardcoded `SECRET_KEY = "hello_farmer_insecure_dev_secret_change_me_32chars!"`.

### 2.7 External AI API Dependencies & Offline Fallback Gaps
* **Audit Finding:** **PARTIALLY MITIGATED, FURTHER WORK REQUIRED**.
* The core conversational pipeline currently relies on external cloud APIs:
  - Speech Recognition: Google Gemini API or Groq Cloud API.
  - LLM: Google Gemini API or Groq LLaMA Cloud.
  - Speech Synthesis: Microsoft Edge-TTS Cloud.
* When running offline:
  - STT: `whisper_local` fails if C++ binary is missing and outputs canned strings.
  - LLM: `OllamaLLMProvider` is implemented but requires an active local Ollama daemon.
  - TTS: `FallbackSynthProvider` produces a sine tone rather than speech.

---

## 3. Summary of Reusable Assets (Do Not Replace)

The following components represent high-value engineering that must be preserved:
1. **AudioSocket Protocol Engine (`backend/app/telephony/audiosocket_server.py`)**: Robust framing, buffer draining, and silence keepalive generators.
2. **Call State Machine (`backend/app/telephony/call_flow.py`)**: Turn-taking, caller context tracking, and DB metric finalization.
3. **Asterisk Configuration & Network Auto-Configurator (`scripts/update_network_ip.ps1`)**: Resolves complex Docker NAT loopback on Windows.
4. **Agricultural Safety Engine (`backend/app/safety/guardrails.py`)**: Comprehensive regex rules, dosage sanity validation, and emergency keyword detectors.
5. **Geocoding & Agroecological Engine (`backend/app/weather/location.py`)**: 50+ Ethiopian woredas and zones mapped to elevation profiles.
6. **Pre-rendered Telephony Audio Cues (`backend/cache/prompts/`)**: High-quality 8kHz SLIN audio prompts for call state transitions.
7. **Curated Agricultural Knowledge Base (`knowledge_base/raw/MoA Guidelines/`)**: 80+ official MoA technical packages.
