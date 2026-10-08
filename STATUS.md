# Project Status (STATUS.md)

Current Date: October 2026  
Current Status: **Phase 4 (LLM and Guardrails) - COMPLETED ✅ | Ready for Phase 5 Gate**

---

## 1. What is Done
- [x] **Phase 0 (Setup)**:
  - Scaffolding, configuration, Docker Compose (all 6 services healthy).
  - PostgreSQL with pgvector 0.8.7, Redis, Asterisk 20 LTS with AudioSocket, FastAPI, arq worker, Next.js web portal.
- [x] **Phase 1 (Evaluation & STT)**:
  - Ethiopian text utilities (Amharic Ge'ez normalization, confusable character folding, Afaan Oromo Qubee normalization, bidirectional numbers & quantity extractors).
  - STT providers: Gemini Multimodal Audio STT (primary) and Faster-Whisper local (MIT license).
  - STT benchmark evaluation across 3 audio conditions (16 kHz, 8 kHz, G.711 telephony).
- [x] **Phase 2 (TTS and Prompts)**:
  - `BaseTTSProvider` with sentence-level chunking and SHA-256 disk caching.
  - `EdgeTTSProvider` (PROTOTYPE ONLY) with neural voices `am-ET-AmehaNeural` and `am-ET-MekdesNeural` and ffmpeg transcoding to 8 kHz 16-bit mono linear PCM.
  - `FallbackSynthProvider`: Deterministic offline acoustic synthesizer ensuring the system never goes silent or crashes.
  - `scripts/render_prompts.py`: Rendered all 15 fixed telephony prompt WAVs in 8 kHz mono linear PCM in `backend/cache/prompts/` (greetings, consent, "one moment" cue, repeat prompts, safe fallback, goodbyes, error handling).
  - `backend/app/telephony/prompts_audio.py`: Zero-latency in-memory prompt audio loader for Asterisk call states.
  - `scripts/compare_tts.py`: Rendered 10 standardized agricultural evaluation answers across 3 provider/voice configurations into `eval/reports/tts_samples/` and generated human evaluation CSV `eval/reports/tts_comparison.csv`.
- [x] **Phase 3 (Knowledge Base & RAG)**:
  - `backend/app/rag/embed.py`: Gemini `text-embedding-004` (768 dimensions) & local dense embedding fallback.
  - `backend/app/rag/chunking.py`: 300-500 token sliding chunker with 50-token overlap and section heading hierarchy retention.
  - `backend/app/rag/ingest.py`: Multi-format document parser with strict provenance and source tier gating (Tiers 1-3 allowed; Tier 4 strictly blocked).
  - `backend/app/rag/store.py`: PostgreSQL `pgvector` store with cosine distance index.
  - `backend/app/rag/retrieve.py`: Semantic vector search, cross-lingual querying, similarity thresholding, and source tier tagging.
  - `scripts/ingest_kb.py`: CLI ingestion script populated 5 placeholder agronomic guides (teff, maize, wheat, pesticide safety) into PostgreSQL.
  - `eval/rag_eval.py`: RAG evaluation harness across 30 questions per language with cross-lingual validation and Tier 4 rejection gate.
- [x] **Phase 4 (LLM and Guardrails)**:
  - `backend/app/llm/prompts.py`: Versioned prompt enforcing 3-sentence limit, spoken style, words-for-numbers, no invented chemicals/doses, express uncertainty, immediate medical/veterinary referral, and JSON schema.
  - `backend/app/llm/gemini.py`: Primary Google Gemini Flash LLM provider with structured JSON schema output, 8s timeout, and repair retry.
  - Fallback chain (`backend/app/llm/chain.py`): Gemini -> Groq -> OpenRouter (:free) -> Ollama (local) -> pre-rendered safe fallback referral.
  - Guardrails engine (`backend/app/safety/guardrails.py`):
    - Words-to-number quantity validator against retrieved passages.
    - Strict source tier enforcement: chemical/dosage recommendations rejected on placeholder/unvetted documents.
    - Arabic-to-words digit transliteration for natural phone speech.
    - Sentence length capping (<= 3 sentences).
    - Emergency detection routing acute poisoning or livestock distress to medical/veterinary facilities.
  - `eval/answer_eval.py`: 100% pass across 4 categories (Answerable, Not Covered, Dangerous/Chemicals, Off-Topic) with zero digit violations.
  - `scripts/review_cli.py`: Interactive CLI tool for human agronomist review of answer outputs.
  - 26 automated unit tests passing (`26 passed in 4.15s`).
  - Zero ruff lint errors across the codebase.

---

- [x] **Phase 5 (Telephony & Core Call Loop - Amharic)**:
  - `backend/app/telephony/endpointing.py`: VADEndpointer online RMS frame accumulator with silence timeout (1000ms), min speech (250ms), and initial silence detection.
  - `backend/app/telephony/call_flow.py`: Full asynchronous CallStateMachine (ANSWER -> CONSENT -> LISTEN -> THINK -> SPEAK -> LOW CONFIDENCE -> TIMEOUT -> HANGUP).
  - Concurrency limiter and salted SHA-256 caller hashing.
  - `backend/app/telephony/audiosocket_server.py`: Wired to CallStateMachine on port 9092.
  - `scripts/simulate_call.py`: 100% pass on all 3 scenarios (normal question with 195k audio bytes delta, silence timeout, caller hangup).
  - Asterisk 20 LTS configured and healthy (`pjsip.conf`, `extensions.conf` with AudioSocket dialplan on 8028).
  - 30 automated unit tests passing (`30 passed in 4.82s`).
  - Zero ruff lint errors across the codebase.

---

- [x] **Phase 6 (Context, Consent, Privacy)**:
  - Structured extraction of crop, symptoms, location, and growth stage in `backend/app/farmer_context/extraction.py`.
  - Cryptographic farmer profile management with salted SHA-256 caller hashing and AES-256 Fernet encryption at rest in `backend/app/farmer_context/profile.py`.
  - Voice consent recording (`consent_records`), complete data purge by caller hash (`delete_all_caller_data`).
  - Unit tests in `tests/test_privacy_context.py` (5 passing tests).
  - Comprehensive documentation in `docs/privacy.md`.

---

- [x] **Phase 7 (Weather Integration)**:
  - Open-Meteo free API provider with Redis / in-memory 60-minute TTL caching and `MockWeatherProvider` offline fallback in `backend/app/weather/provider.py`.
  - Place-name directory and fuzzy location matching across Amharic, Oromo, and English in `backend/app/weather/location.py`.
  - 18 Ethiopian agricultural hubs seeded into PostgreSQL (`place_names`).
  - Spoken location confirmation ("በአዳማ አካባቢ...", "Naannoo Adaamaatti...").
  - Agricultural weather risk analyzer in `backend/app/weather/risk.py`: evaluates pesticide spraying risks (rain wash-off and wind drift) and heavy rainfall hazards (>20mm).
  - Integrated weather flow into `backend/app/pipeline.py` handling spraying and rain inquiries.
  - Unit tests in `tests/test_weather.py` (8 passing tests).
  - Total test suite: 43 automated unit tests passing (`43 passed in 4.79s`).
  - Code quality: 0 ruff errors across `app/`, `tests/`, `scripts/`.

- [x] **Phase 8 (Post-Call SMS & Background Worker)**:
  - `workers/worker.py` running `arq` background queue on Redis with healthy container status.
  - Post-call advice summarization in caller's language (`am` / `om`) in `backend/app/sms/summary.py`.
  - SMS encoding & segmentation engine in `backend/app/sms/encoding.py` (UCS-2 70 chars for Ge'ez, GSM-7 160 chars for Latin, safe truncation, duplicate suppression).
  - `MockSMSProvider` in `backend/app/sms/mock.py` saving to `sms_messages` table and printing developer console banners.
  - Background dispatcher in `backend/app/sms/dispatcher.py`.
  - Unit tests in `tests/test_sms.py` (8 passing tests).
  - Total test suite: 51 automated unit tests passing (`51 passed in 5.06s`).
  - Code quality: 0 ruff errors across `app/`, `tests/`, `scripts/`, `workers/`.

- [x] **Phase 9 (Afaan Oromo End-to-End)**:
  - Language identification engine in `backend/app/language/detect.py` with script classification and inflected vocabulary matching.
  - Dynamic language switching in `backend/app/pipeline.py`.
  - Spoken Qubee number transliteration into words ("lama", "sadii", "shan").
  - Afaan Oromo pre-rendered prompts in `backend/cache/prompts/` (greeting, consent, one_moment, safe_fallback, goodbye, error).
  - Weather, spraying safety, safe referral, and post-call SMS verified in Afaan Oromo.
  - Unit tests in `tests/test_oromo_e2e.py` (7 passing tests).
  - Total test suite: 58 automated unit tests passing (`58 passed in 6.25s`).
  - Code quality: 0 ruff errors across `app/`, `tests/`, `scripts/`, `workers/`.

- [x] **Phase 10 (Warnings - Thin Slice)**:
  - Heavy-rainfall warning rules in `backend/app/warnings/rules.py` with 4 severity levels (LOW, MEDIUM, HIGH, CRITICAL).
  - Targeting engine in `backend/app/warnings/targeting.py` enforcing opt-in verification, geographic woreda matching, daily frequency cap (1/24h), and duplicate suppression.
  - Localized warning generator in `backend/app/warnings/generate.py`.
  - Follow-up loop in `backend/app/warnings/followup.py` for returning callers.
  - Seeder script `scripts/seed_demo_farmers.py` populated 10 synthetic farmers across Ethiopian woredas into PostgreSQL.
  - Evaluation harness in `eval/warning_eval.py` generated `eval/reports/warning_eval_report.md`.
  - Unit tests in `tests/test_warnings.py` (4 passing tests).
  - Total test suite: 62 automated unit tests passing (`62 passed in 5.36s`).
  - Code quality: 0 ruff errors across `app/`, `tests/`, `scripts/`, `workers/`, `eval/`.

---

- [x] **Phase 11 (Web Frontend - Minimal Next.js)**:
  - Backend API endpoints in `backend/app/main.py`:
    - `POST /api/v1/ask`: Unified AI pipeline query endpoint with source citations, tier ratings, grounding flags, and bilingual gloss.
    - `GET /api/v1/warnings/active`: Recent heavy-rainfall warnings for web display.
    - `GET /api/v1/developer/sms`: Dev SMS inbox listing simulated SMS dispatches.
    - `GET /api/v1/farmer/profile`: Profile, registered crops, and opt-in status.
    - `GET /api/v1/admin/analytics`: Aggregated platform metrics from PostgreSQL.
  - Next.js 14 Web Portal live on port 3000:
    - "Ask Hello Farmer" text page.
    - Farmer Profile view.
    - Rainfall Warnings view.
    - Developer Mock SMS Inbox view.
    - Admin Analytics dashboard.
    - Rewrite proxy `/api/backend/*` to backend service.
  - All 6 Docker containers running and healthy.
  - Total test suite: 62 automated unit tests passing (`62 passed in 5.84s`).
  - Code quality: 0 ruff errors across `app/`, `tests/`, `scripts/`, `workers/`, `eval/`.

---

## 2. What is Next (Phase 12: Evaluation & Pilot Readiness)
- [ ] VAD Endpointing evaluation (`eval/endpointing_eval.py`).
- [ ] Concurrency & turn latency benchmarking (`eval/latency_report.py`).
- [ ] Automated headless SIP softphone test into Asterisk.
- [ ] Comprehensive path to production documentation (`docs/path_to_production.md`, `docs/scaling_costs.md`).
- [ ] Final acceptance verification against the 12-item acceptance checklist.





