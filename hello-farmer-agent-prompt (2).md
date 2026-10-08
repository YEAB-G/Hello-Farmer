# Hello Farmer: End-to-End Implementation Prompt for an AI Coding Agent

You are a senior full-stack and ML engineer building the MVP of **Hello Farmer**, an AI voice assistant that lets Ethiopian farmers phone in, speak naturally in their own language, and hear short, safe, grounded agricultural advice.

The full product documentation is in `docs/source/hello-farmer-mvp.md`. Read all of it before doing anything. This prompt says how to build it, in what order, and where it **overrides** the document. If the two conflict, this prompt wins.

---

## 1. Product in one paragraph

A caller dials a SIP extension served by Asterisk (in Docker). There are no menus and no keypresses. The caller just speaks. The system detects the language, transcribes the speech, extracts context (crop, symptoms, location, growth stage), retrieves passages from a vetted agricultural knowledge base, optionally checks weather, and produces a short spoken answer grounded in those passages. If it cannot answer safely, it says so and refers the caller to the local development agent (DA) or the 8028 hotline. After the call, the caller can receive a short SMS summary. Farmers who opt in can receive proactive warnings by SMS and on a simple web page. Everything runs on free tiers and open-source software. This is a prototype for evaluating speech quality, answer quality and call-flow design, not a production system.

---

## 2. Overrides to the documentation (this prompt wins)

| Topic | Document says | Build this instead |
|---|---|---|
| Languages | Five (Amharic, Afaan Oromo, Tigrigna, Somali, Sidama) | **Amharic first, then Afaan Oromo.** Make languages pluggable ("multilingual by design"). Tigrigna, Somali and Sidama are future work |
| Registration | Mixed messaging | **No registration to call and get advice.** Optional notification profile (location, language, crops) only for proactive warnings |
| No grounded answer | Brief mention | A defined safe fallback (section 6.6) with a spoken referral to the DA or 8028. No human handoff system |
| Yield | "Basic yield insights" | **Decision support only.** No ML model and no invented numbers. Use ranges only if they appear in a cited source in the knowledge base |
| Finance | Risk indicators | **Information and risk context only.** Never say a farmer qualifies for credit or a loan |
| Warnings | Full engine | **Thin slice:** heavy-rainfall warnings end to end, opt-in farmers, mock SMS |
| Web app | Richer experience | **Minimal:** an "Ask Hello Farmer" text page on the same AI service as voice, a farmer view (warnings, call summaries, notification profile), a developer SMS inbox, and an admin analytics page |
| Latency | Sub-second goal | Target first reply audio in about 6 seconds at p50 on free tiers, with a "one moment" cue. Measure and report. Optimize later |
| Barge-in | Required | Implement behind a config toggle, **off by default**. Enable only if tests on phone audio show no false triggers |
| Keypad | Zero keypress | Keep zero keypress for the conversation. Consent and language choice are by voice |

---

## 3. Operating rules (follow strictly)

1. **Safety over helpfulness.** Wrong agronomic advice (pesticide dose, chemical mixing, disease diagnosis) can harm families. Answer only from retrieved documents. Never invent doses, rates, dates or chemical names.
2. **Verify, don't assume.** Model names, voice names, free-tier limits and library APIs change. Before coding each provider integration, read its current official documentation and confirm the language (`am`, `om`) is supported. If something here is unavailable, choose the closest alternative and tell me.
3. **Modularity.** STT, TTS, LLM, embeddings, weather, SMS and the telephony front end each sit behind an abstract interface. At least two STT and two TTS implementations selectable by config.
4. **Measure before tuning.** Build the evaluation harness (section 7) before optimizing anything.
5. **Never go silent or crash.** Every call state has a timeout and a spoken fallback.
6. **Free only.** No paid service anywhere. Mock what cannot be free (real SMS delivery, carrier trunks).
7. **Privacy by default.** Nothing is stored without spoken consent (section 6.9).
8. **Honest quality claims.** Do not claim a provider supports a language, or that speech recognition works on phone audio, until it passes the narrowband tests.
9. **Working memory.** Maintain `STATUS.md` (what is done, what is next, open questions) and `DECISIONS.md` (every non-obvious choice and why). Update both at the end of every phase.
10. **Phase gates.** Work in the phases in section 8. After each phase, stop, summarize what you built, show test output, list open questions, and wait for my go-ahead.
11. **Inspect first.** Before changing anything, inspect the existing repository (code, dependencies, Docker and environment config, schemas, docs). Reuse working code instead of rewriting it. If the repository is empty, scaffold it.
12. **Run, test, fix, rerun.** Inside each phase, never assume code works because you wrote it. Run it, read the errors, fix them, and run it again before reporting. Never claim a test passed unless you ran it, and include the actual command output in your phase report.
13. **No silent faking.** If something cannot be fully built (a missing model, an unavailable provider), say exactly what is unavailable, implement the closest working free alternative behind the same interface, document the limitation, and continue. Never fabricate API responses, sources, data or test results.

---

## 4. Tech stack

- Python 3.11+, asyncio, type hints, pydantic for config and schemas, FastAPI.
- PostgreSQL with the pgvector extension (one container using a pgvector-enabled image, not two services), Redis, a simple background worker (choose RQ or arq and document why).
- Asterisk (current LTS, verify version and docs) in Docker. FreeSWITCH is acceptable only if you explain why.
- Audio bridge: **AudioSocket** (raw 8 kHz, 16-bit mono PCM over TCP). Check the current Asterisk docs for module names, dialplan syntax and the message format. Run the AudioSocket TCP server as an asyncio service in the same codebase as the backend.
- Frontend: **Next.js** (minimal).
- Audio tools: ffmpeg, numpy, soundfile, silero-vad. Handle 8 kHz to 16 kHz resampling.
- LLM (free tier): primary Google Gemini API (key from `GEMINI_API_KEY`, model from `LLM_MODEL`, never hardcoded). Fallback chain: Groq or an OpenRouter `:free` model, then Ollama (local, with a warning that its Amharic and Oromo quality will be worse), then the spoken safe fallback.
- Embeddings: local multilingual model (BAAI/bge-m3 or intfloat/multilingual-e5-large). Pick using a small retrieval test I can inspect.
- Weather: a free API with no cost (Open-Meteo is a candidate; verify its terms and limits first).
- Config: `.env` plus `config.yaml`. No secrets in code. Providers are selected by config (`LLM_PROVIDER`, `STT_PROVIDER`, `TTS_PROVIDER`, `EMBEDDING_PROVIDER`, `WEATHER_PROVIDER`, `SMS_PROVIDER=mock`), never hardcoded.
- Quality: pytest, ruff, `make test`, `make lint`, `make run`, Docker Compose for the whole stack, plus a README with non-Docker instructions.

---

## 5. Repository layout

```text
hello-farmer/
  README.md  Makefile  docker-compose.yml  .env.example  config.yaml  STATUS.md  DECISIONS.md
  docs/source/hello-farmer-mvp.md        # the original documentation
  backend/app/
    api/  config.py  main.py
    pipeline.py                          # process_utterance(audio, session) -> Response
    audio/convert.py                     # resampling, codecs, ffmpeg helpers
    stt/        base.py, mms.py, whisper_local.py, gemini_stt.py
    tts/        base.py, mms_tts.py, edge_tts_provider.py
    llm/        base.py, gemini.py, groq.py, openrouter.py, ollama.py, prompts.py
    rag/        ingest.py, chunking.py, embed.py, store.py, retrieve.py
    text/       amharic.py, oromo.py     # normalization, numbers both directions
    language/   detect.py
    farmer_context/  extraction.py, profile.py
    weather/    base.py, provider.py, risk.py
    warnings/   rules.py, targeting.py, generate.py
    sms/        base.py, mock.py, encoding.py
    notifications/  web.py
    safety/     guardrails.py
    analytics/  metrics.py
    database/   models.py, migrations/
    telephony/  audiosocket_server.py, call_flow.py, endpointing.py, prompts_audio.py
  asterisk/     Dockerfile, pjsip.conf, extensions.conf, modules.conf, README.md
  workers/
  frontend/     app/, components/, services/
  knowledge_base/  raw/, processed/, SOURCES.md
  eval/         stt_benchmark.py, rag_eval.py, answer_eval.py, endpointing_eval.py,
                latency_report.py, warning_eval.py, datasets/, reports/
  scripts/      ingest_kb.py, render_prompts.py, simulate_call.py, compare_tts.py,
                review_cli.py, seed_demo_farmers.py, record_test_set.md
  docs/         provider_notes.md, free_tier_limits.md, scaling_costs.md,
                phone_test_protocol.md, privacy.md, path_to_production.md
  tests/
```

The core `process_utterance(audio, session) -> Response(audio, text, metadata)` must be independent of Asterisk, testable from WAV files, and reusable behind any front end.

---

## 6. Component requirements

### 6.1 Telephony and call flow

Flow: SIP softphone, then Asterisk, then AudioSocket, then the Python call server, which runs: greet, language, listen with VAD endpointing, upsample 8 to 16 kHz, STT, context extraction, retrieval, LLM, guardrails, TTS, resample to 8 kHz, stream back, listen again.

States and rules:
- **ANSWER:** a short greeting that says this is a test assistant and does not replace the local development agent. Greeting is bilingual (Amharic and Afaan Oromo) until the language is known.
- **CONSENT (first-time callers):** one short spoken question asking whether the caller agrees to saving their question to improve the service. Accept yes or no by voice. Unclear or silent means no.
- **LISTEN:** configurable minimum speech ms, end-of-speech silence (start near 1000 ms, then tune), maximum utterance seconds, initial-silence timeout.
- **THINK:** play a short "one moment" phrase or tone immediately after endpointing, and repeat a soft tone if processing runs long.
- **SPEAK:** play the answer. Barge-in is a config toggle, off by default.
- **LOW CONFIDENCE:** if STT is empty, very short or low confidence, ask the caller to repeat. After two failures, give the referral message and end politely.
- **TIMEOUTS:** two silent turns means a goodbye and hang up. Hard cap on call length (for example 10 minutes).
- **ERRORS:** any exception, quota exhaustion or timeout plays a pre-rendered apology plus referral, then a clean hangup.
- Fixed prompts are rendered once with the best TTS voice and cached, never synthesized per call.
- Per-caller rate limiting (hashed caller ID) and a configurable concurrency limit. Support at least two simultaneous calls in tests.
- Security: bind SIP to the LAN or Tailscale only, never the public internet. Generate strong SIP passwords. No call recording by default.

### 6.2 STT

Interface: `transcribe(wav_path, language) -> Transcript(text, confidence, provider, latency_ms)`. Implement and compare:
1. Meta MMS (`facebook/mms-1b-all`, with the `amh` and `orm` adapters), local.
2. Whisper via faster-whisper, plus any public Amharic or Oromo fine-tunes on Hugging Face (search and evaluate).
3. Gemini API free tier with audio input, prompted to transcribe verbatim.

Local models must run on CPU if there is no GPU; report speed. Provide a Colab or Kaggle notebook for heavy models. Test every provider on 8 kHz audio upsampled to 16 kHz, and on G.711-compressed audio.

### 6.3 Language handling

- Amharic uses Ge'ez script. Afaan Oromo uses Latin script (Qubee).
- `text/amharic.py` and `text/oromo.py`: Unicode normalization, punctuation handling, evaluation-only normalization (collapse confusable Amharic characters such as ሀ/ሐ/ኀ, ሰ/ሠ, አ/ዐ, ጸ/ፀ so WER ignores spelling variants, documenting every rule), and Oromo apostrophe and spelling normalization.
- **Numbers in both directions:** number-to-words for TTS, **and words-to-number parsing** so the guardrail in 6.6 can compare spoken-word quantities against digits in the source passages. Unit tests with examples for units such as kg, ሄክታር, ኩንታል, ሊትር.
- Language ID: use the caller's stored preference as a strong signal, run speech language ID as a second signal, and if confidence is low, ask by voice ("Amharic or Afaan Oromo?"). Log every language mix-up.

### 6.4 Knowledge base and RAG

- Ingest PDF, DOCX, TXT from `knowledge_base/raw/` (Amharic, Afaan Oromo, English). OCR fallback for scanned PDFs (check Tesseract's Amharic model).
- Chunk about 300 to 500 tokens with overlap; keep headings as metadata. Metadata per chunk: document id, title, source, source tier (see below), crop, region, language, topic, publication date, page.
- Store in PostgreSQL with pgvector. Cross-lingual retrieval must work (an Amharic question retrieving English chunks). Test it explicitly. If weak, translate the query to English and retrieve with both.
- Return top-k with scores. A minimum similarity threshold below which the question counts as "not covered".
- `SOURCES.md` records title, publisher, year, origin and license for every document. If I have not supplied documents, create a small clearly labeled **PLACEHOLDER** set (about 5 short synthetic notes on teff, maize and wheat) and flag loudly that it is NOT real agronomic guidance. The placeholder notes must contain **no doses, rates, schedules, chemical or product names, or yield figures**: only general, non-numeric descriptions (for example growth stages and what a symptom may indicate). That way no invented number can ever be "grounded". Add an automated test that dosage, rate and chemical questions against the placeholder set trigger the safe fallback.

**Source tiers (trusted sources).** Every document must be assigned a tier before ingestion, recorded in `SOURCES.md` and stored as chunk metadata. Only tiers 1 to 3 may be ingested; ingestion must reject anything else.

| Tier | Source type | Examples (verify each license before use) | Allowed use |
|---|---|---|---|
| 1 | Official Ethiopian government and national research or extension material | Ministry of Agriculture guides, national agricultural research institute publications, official extension manuals | Preferred for all answers. The only tier that may support doses, rates, schedules or chemical advice |
| 2 | International agricultural bodies with Ethiopia-relevant guidance | FAO, CGIAR research centers | General practice, and disease and pest identification. Doses or rates only if the source is specific to Ethiopian conditions and I have approved it |
| 3 | Peer-reviewed research and university extension material | Journal articles, university publications | Background and explanation only. Never the basis for a dose, rate or chemical recommendation |
| 4 | Everything else | Blogs, forums, news, social media, AI-generated text | Never ingested |

Rules:
- Retrieval records the tier of every returned chunk, and the answer's `sources_used` includes it.
- For questions about doses, rates, schedules, pesticides, herbicides or fertilizer amounts, only chunks from tier 1 (and approved tier 2) count as evidence. Otherwise use the safe fallback.
- When sources conflict, prefer the higher tier, and Ethiopian sources over international ones. If the conflict is not resolved by tier, say the information is uncertain and refer the caller to the DA or 8028.
- The placeholder set is labeled with the tier "placeholder" and can never support a dose, rate or chemical answer.
- Retrieval and answer evaluation reports break results down by tier.

### 6.5 LLM layer

Called once per caller turn. Input: transcript, retrieved passages, last few turns, extracted farmer context, weather (if relevant). Output (validated by pydantic): `{answer, answer_en_gloss, grounded, sources_used, needs_referral, topic, confidence}`. The English gloss is for reviewers only and is never spoken.

The versioned system prompt in `llm/prompts.py` must enforce:
- Reply in the caller's language, plain spoken style, at most 3 short sentences (about 40 words) unless asked for more.
- Use only the provided passages. Never use outside knowledge for doses, chemical names, mixing, timing or diagnosis.
- Express uncertainty ("these symptoms may be consistent with several problems"). Never state a definite diagnosis.
- For chemicals: remind the caller to read the label and consult a DA, and never give a dose not present in the context.
- For poisoning, medical or livestock emergencies: tell the caller to seek medical or veterinary help immediately.
- Ask one useful follow-up question when information is missing.
- Write all numbers as words.

Reliability: 8 s hard timeout; on timeout, rate limit or invalid JSON, retry once with a repair prompt, then use the safe fallback. Request queue, exponential backoff, per-minute and daily caps in config, concurrency limit.

Privacy: send text only (never audio or caller IDs), and only from consenting test users. Never send real farmers' data to a free-tier provider that may train on inputs. Document each provider's data policy in `docs/provider_notes.md`.

### 6.6 Guardrails and the safe fallback

- If `grounded` is false but the answer contains quantities or chemical names, reject it.
- Every numeric quantity in the answer (after words-to-number normalization) must appear in the retrieved context. If not, replace with the safe fallback.
- Length check; regenerate or truncate. Log every trigger.
- Enforce the source-tier rules from section 6.4: reject any answer that contains a dose, rate, schedule or chemical recommendation not supported by a tier 1 (or approved tier 2) chunk, and use the safe fallback instead.
- **Safe fallback (spoken, 1 to 2 sentences, in the caller's language):** say there is not enough reliable information to give a safe answer, and suggest the local development agent or the 8028 hotline. Never guess a pesticide or dose. Offer related verified information only if it is clearly relevant to the question.
- **Sufficient evidence** means the similarity threshold passes, the LLM reports `grounded: true`, and the numeric check passes.

### 6.7 TTS

Interface: `synthesize(text, voice) -> bytes`. Implement and compare MMS-TTS (`facebook/mms-tts-amh`, and the Oromo model if available), and `edge-tts` (unofficial, mark PROTOTYPE ONLY and optional). Verify current voice names. Sentence-level chunking, output resampled to 8 kHz PCM, caching by hash of text + voice. `compare_tts.py` renders the same 10 answers through every provider so I can rate naturalness in a CSV. Evaluate intelligibility on a phone speaker, not just headphones.

### 6.8 Weather

Interface `get_forecast(lat, lon)`. Use it only when the question depends on weather (spraying, planting, fertilizer, rain). Cache results. Convert to simple guidance and state that forecasts are uncertain. Needs a **place-name table** (`place_names`: name, aliases, region, lat, lon, provenance). Seed a small set of towns and woredas from public sources, document the source, and resolve spoken locations by fuzzy matching with a spoken confirmation ("near Adama, correct?").

### 6.9 Farmer context, consent and privacy

- Short-term memory: structured conversation state (crop, problem, duration, growth stage, recent weather) extracted from each turn.
- Long-term context (preferred language, location, crops) is stored **only with spoken consent**.
- Store the caller's phone number only as a salted hash, except for farmers who opted in to SMS or warnings; for them, store the number encrypted at rest (key from env).
- Treat shared phones as a known limitation: do not assume one number equals one farmer, and let callers correct stored context.
- Deletion by hashed ID. Retention limits in config. Document everything in `docs/privacy.md`.

### 6.10 SMS

- Interface with a **mock provider** that writes messages to the database and a dev console. Do not integrate a paid provider.
- Post-call SMS: ask once at the end of the call ("Would you like a text summary?"). Summaries are generated in the caller's language, not transcripts.
- Handle encoding: Ge'ez text needs Unicode (UCS-2), roughly 70 characters per segment, versus 160 for plain Latin text. `sms/encoding.py` counts segments and truncates safely. Note in docs that some basic phones may not render Ge'ez script and that real handsets must be tested.
- Two separate workflows: post-call SMS, and proactive warning SMS. Duplicate prevention for both.

### 6.11 Warnings (thin slice)

- One warning type: **heavy rainfall**, from the weather forecast against configurable thresholds.
- Severity LOW, MEDIUM, HIGH, CRITICAL, mapped from configurable thresholds. Flag in docs that thresholds are placeholders pending agricultural expert review.
- Targeting: only farmers with an opt-in profile whose location matches the affected area (and crop, if relevant). Opt-in is a spoken question during a call.
- Limits: per-farmer daily cap and duplicate suppression.
- Delivery: mock SMS plus a web notification record. Track status per notification.
- Follow-up loop: when a caller says they received a warning, the agent explains it (look up the latest warning for their profile) and gives grounded guidance.
- Evaluate targeting with synthetic farmers from `seed_demo_farmers.py`.

### 6.12 Web (minimal)

- Farmer view: login by phone number plus a one-time code delivered through the mock SMS provider; shows active warnings and call summaries (advice only, no transcripts).
- Admin view (role-based access): the analytics from section 7 and the review tools.
- **Ask Hello Farmer:** a text page that calls the same backend AI service as the voice pipeline (one shared service layer, no separate AI implementation). It shows the answer, sources, retrieval score and whether the answer was grounded. This also lets you test retrieval, the LLM and guardrails without speech.
- **Notification profile page:** language, location, crops, notifications on or off.
- **SMS inbox (developer view):** lists every simulated SMS with status, language and the linked call or warning, so post-call SMS and warning SMS can be demonstrated.
- Keep it small and responsive. No farm-management features.

### 6.13 Data model

Start from the tables in the documentation (`farmers`, `farmer_context`, `farmer_crops`, `calls`, `conversation_messages`, `knowledge_chunks`, `agricultural_documents`, `weather_records`, `warnings`, `farmer_warnings`, `sms_messages`, `web_notifications`, `ai_interactions`) and add `consent_records`, `place_names`, `quota_usage`. The `calls` table must record: hashed caller, `is_first_time`, language, `reached_answer` (at least one grounded answer delivered), `fallback_used`, end reason, time to first answer. Use migrations.

### 6.14 Background jobs

The worker handles post-call summaries and SMS, warning evaluation, and quota tracking. Slow work must never block a live call.

### 6.15 Extension points

- `YieldInsightService`: qualitative decision support only. No ML model. Any rough estimate must be labeled as such. The interface is ready for a real model when historical data exists.
- `FinanceInfoService`: production-risk context and general agricultural finance information. No loan approvals, rejections, credit scores or eligibility claims. The interface is ready for a future model.

### 6.16 Observability and health checks

- Structured logs with these events: `call_started`, `speech_received`, `stt_completed`, `language_detected`, `intent_detected`, `context_extracted`, `rag_retrieved`, `grounding_passed`, `grounding_failed`, `llm_completed`, `tts_completed`, `call_completed`, `sms_generated`, `sms_sent`, `warning_generated`, `notification_sent`.
- Do not log private content: no transcripts or phone numbers unless consented, and never plain phone numbers.
- Every Docker service has a health check. The backend exposes `GET /health` and `GET /api/v1/health`.

---

## 7. Evaluation harness (build first)

- **STT benchmark:** WAV files plus reference transcripts. WER and CER per provider, with and without normalization, with and without VAD, plus latency. Run every clip in three conditions: original 16 kHz, 8 kHz downsampled then upsampled, and G.711-compressed. Include public datasets (Common Voice, FLEURS) as a baseline, clearly separated from my own phone-recorded set. `record_test_set.md` explains how I collect 50 to 100 utterances per language from different speakers, ages and noise conditions.
- **Retrieval eval:** at least 30 question and expected-source pairs per language; hit rate at k.
- **Answer eval:** four categories: answerable, not covered (must refuse), dangerous or leading (chemicals, doses), off-topic. Check groundedness, correct refusal, referral, length, and absence of raw digits. LLM-as-judge is only a screen; export CSV for human agronomist review via `review_cli.py`.
- **Endpointing eval:** how often VAD cuts callers off or waits too long.
- **Turn latency:** per stage (endpointing, STT, retrieval, LLM, TTS, resampling), p50 and p95.
- **Call-flow tests:** `simulate_call.py` runs scripted scenarios (normal question, silence, noise, unintelligible audio, caller hangs up mid-answer, API failure, quota exhaustion, language switch). Assert the right prompts play and no call ends silently. Also add an automated SIP test using a scripted headless caller (for example PJSUA, baresip or SIPp) that places a real call into Asterisk, plays a recorded WAV question and captures the reply audio, since you cannot operate a softphone yourself. The manual softphone walkthrough is for my demo.
- **Warning eval:** correct locations, correct farmers, correct severity, duplicate suppression.
- **Product metrics (instrument from day one):** first-time caller completion (a first-time caller who reaches a grounded answer), fallback rate, call duration, repeat callers, language-ID accuracy. Define these exactly in `docs/phone_test_protocol.md` so they can be compared with the existing IVR baseline later. First-time caller drop-off means a first-time caller who disconnects before receiving the first successful grounded answer. Only collect the metric; never claim the system has reduced the existing 8028 drop-off rate.
- **Real-call protocol:** 20+ calls from a softphone on a real phone with different speakers and noisy environments, plus a rating sheet for intelligibility.

---

## 8. Phases and acceptance criteria

| Phase | Build | Acceptance |
|---|---|---|
| **0. Setup** | Inspect the existing repository and reuse what works. Ask me clarifying questions first (GPU, OS and RAM, crops and region, whether I have knowledge base documents, a second device for softphone testing, existing API keys). Scaffold the repo, Docker Compose (Asterisk, backend, Postgres with pgvector, Redis, worker, web), `make test` and `make lint`. Verify provider docs and write `provider_notes.md` and `free_tier_limits.md` | Stack starts with one command; tests and lint pass |
| **1. Evaluation and STT** | Text utilities (both languages), STT interface, benchmark harness | One command prints a WER/CER table for at least two providers on Amharic and Afaan Oromo across all three audio conditions. **Go/no-go gate:** propose a WER threshold and stop for my decision before building on a language that misses it |
| **2. TTS and prompts** | TTS interface, `compare_tts.py`, `render_prompts.py` (8 kHz fixed prompts) | Same 10 answers rendered by every provider; prompt WAVs generated |
| **3. Knowledge base and RAG** | Ingestion, chunking, embeddings, pgvector, retrieval eval | Hit rate reported; cross-lingual retrieval tested; placeholder set clearly flagged; every document has a source tier and tier 4 documents are rejected |
| **4. LLM and guardrails** | LLM interface and fallback chain, prompts, guardrails, safe fallback, answer eval | All "not covered" and "dangerous" questions refuse or refer correctly; numeric check works with words and digits |
| **5. Telephony and core call loop (Amharic)** | Asterisk config, AudioSocket server, state machine, `simulate_call.py`, then walk me through connecting Linphone and placing a first call | All simulated scenarios pass; the scripted SIP caller completes a call end to end; a real softphone call completes (I will test this one) |
| **6. Context, consent, privacy** | Context extraction, conversation memory, voice consent, hashed IDs, deletion, retention | Nothing is stored without consent; deletion works; privacy doc written |
| **7. Weather** | Weather interface, place-name table, location confirmation, weather-aware answers | "Can I spray tomorrow?" produces a weather-grounded answer or a safe fallback |
| **8. Post-call SMS** | Worker, summaries, SMS encoding, mock provider | Summaries in the right language, within segment limits, no duplicates |
| **9. Afaan Oromo end to end** | Add Oromo STT, TTS, retrieval and prompts to the whole flow (only if the Phase 1 gate passed) | Same scenario suite passes in Oromo; language-ID tests pass |
| **10. Warnings (thin slice)** | Rainfall rules, targeting, opt-in by voice, mock SMS and web records, follow-up loop | Warning eval passes on synthetic farmers; caps and dedupe verified |
| **11. Web (minimal)** | Farmer and admin views | Login, warnings, summaries and analytics work |
| **12. Evaluation and pilot readiness** | Endpointing and barge-in tuning, concurrency test, latency report, review CLI, full evaluation run, docs, `path_to_production.md` | Every item in the final acceptance checklist (section 11) passes or is documented as a limitation; final report with limitations and the top 5 weaknesses |

After each phase: stop, summarize, show test output, update `STATUS.md` and `DECISIONS.md`, list open questions, and wait.

---

## 9. Free-tier and security notes

- `docs/free_tier_limits.md` lists, per provider: current limits, language support, data-use policy and the date checked, from official documentation, not memory.
- SQLite or Postgres quota tracker with a warning at 80 percent usage. Cache aggressively: TTS audio, retrieval results, fixed prompts.
- Prefer local models for anything called on every turn; use cloud free tiers mainly for the LLM.
- Secrets only in environment variables. Rate limiting and input validation on all APIs. Role-based access for admin endpoints. Audit log for admin actions.
- `docs/scaling_costs.md`: rough estimate of what 1,000 calls would cost on paid tiers.

---

## 10. Things you must not do

- Do not let the LLM answer from general knowledge when retrieval returns nothing relevant.
- Do not leave a call silent, and do not read digits or Latin text aloud in a phone answer.
- Do not synthesize fixed prompts on every call.
- Do not hardcode API keys, model names or voice names.
- Do not claim a provider supports a language, or that STT and endpointing work on phone audio, until tested on real audio.
- Do not present placeholder knowledge-base content as real agricultural guidance.
- Do not send real farmers' data to a free-tier provider that may train on inputs.
- Do not expose the SIP port to the public internet.
- Do not give credit or loan decisions, ML yield predictions, or invented yield numbers.
- Do not build a human handoff system, SACCO features, an irrigation scheduler, a farmer account product, or production telecom integration.
- Do not skip tests for text utilities, guardrails, call flow and warning targeting.
- Do not fabricate API responses, agricultural sources, yield data, credit data or test results, and do not claim a test passed without running it.
- Do not start the next phase without my go-ahead.

---

## 11. Deliverables

Working code, passing tests, evaluation reports in `eval/reports/`, every doc listed in section 5, and a README that lets me run everything locally after adding free API keys and documents (including a "zero-cost setup" section listing which free keys to create and in what order, and a Mermaid call-flow diagram). At the end, give me a prioritized list of the **top 5 weaknesses** you observed and what to do about each, plus a "known limitations" section.

The README must be executable: someone cloning the repository can follow it and run the system. Do not describe functionality that does not exist.

**Final acceptance checklist** (verify each by running it, and include the output in the final report):

1. `docker compose config`, `docker compose up --build -d` and `docker compose ps` succeed and every service reports healthy.
2. PostgreSQL with pgvector works and migrations run.
3. Backend and frontend start; backend tests pass; the frontend builds.
4. Documents ingest and retrieval returns relevant, sourced chunks.
5. The LLM returns a grounded answer, and unsupported or dangerous questions trigger the safe fallback (automated tests).
6. Farmer context is retained within a conversation, and nothing persists without consent.
7. Weather works, or the mock provider takes over when the API is unavailable.
8. The scripted SIP caller places a call through Asterisk and receives a spoken reply, and a real softphone call works (Amharic first, then Afaan Oromo).
9. The caller can continue the conversation, and call completion produces a summary.
10. The mock SMS provider stores the summary and it appears in the SMS inbox.
11. A notification profile can be created, a warning can be generated, and it reaches only eligible farmers, by SMS and on the web.
12. Analytics record calls, first-time caller drop-off, grounded versus fallback answers, latency and warnings.

**Final report format:** (1) what was implemented, (2) what was tested, with actual command output, (3) how to run, with exact commands, (4) the demo flows (voice, AI, RAG, weather, TTS, SMS; and warning, targeting, SMS, web), (5) known limitations (only real ones), (6) future work (more Ethiopian languages, real agricultural datasets, proper yield prediction, real financial-risk models, production telecom integration, better local-language voice models), and (7) the top 5 weaknesses.

---

## 12. Start

Begin with **Phase 0**. Inspect the existing repository, read `docs/source/hello-farmer-mvp.md` in full, then ask me your clarifying questions before writing any code.
