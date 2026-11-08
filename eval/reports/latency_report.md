# Hello Farmer - Real Voice & Turn Latency Benchmark Report
Generated at: 2026-11-08T19:37:23.213887Z
Phase: Phase 7 (GAP-03 Verification - Real Voice Latency Harness)

## 1. Executive Summary
- **First-Audio Prompt Cue ("One moment..." / "Maaloo eegaa...")**:
  - **p50**: 0.00 ms
  - **p95**: 0.00 ms
  - *Result*: Zero dead air. The caller hears the acoustic cue immediately upon VAD endpointing.
- **Acoustic Voice Pipeline Turn Latency (Real Audio In -> Audio Out)**:
  - **p50**: 11.14 seconds
  - **p95**: 14.29 seconds
  - *Result*: End-to-end voice turnaround tested with real telephony spoken inputs.
- **Text-to-Speech Turn Latency (Text In -> Audio Out)**:
  - **p50**: 4.82 seconds
  - **p95**: 10.44 seconds

## 2. Stage-by-Stage Latency Breakdown
| Pipeline Stage | Subsystem | Average Latency |
|----------------|-----------|-----------------|
| VAD Silence Timeout | AudioSocket Endpointing | 1,000 ms (configurable) |
| Audio Prompt Cue | Pre-rendered In-Memory PCM (`prompts_audio.py`) | 0.00 ms |
| Speech-to-Text (STT) | Gemini STT / Local Whisper / HuggingFace | 3915.7 ms |
| Knowledge Retrieval | PostgreSQL `pgvector` Cosine Index (HNSW) | 1646.2 ms |
| Weather Forecast | Open-Meteo API / Redis Cache | 1.8 ms |
| LLM & Guardrails | Local / Cloud LLM + Numeric Word Transliteration | 1780.3 ms |
| Audio Synthesis (TTS) | Piper ONNX / Edge-TTS / Pre-rendered Prompts | 4179.9 ms |

## 3. Concurrency Limits & Architecture
- **Configured Concurrency Limit**: 2 simultaneous calls per free-tier worker.
- **Active Concurrency Lock**: Prevents rate-limit quota exhaustion on external APIs.
- **Zero-Dead-Air Acoustic Bridge**: Fixed prompts stream instantly from RAM cache while dynamic reasoning completes.
