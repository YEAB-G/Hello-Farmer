# Hello Farmer - Real Voice & Turn Latency Benchmark Report
Generated at: 2026-11-08T18:10:23.899333Z
Phase: Phase 7 (GAP-03 Verification - Real Voice Latency Harness)

## 1. Executive Summary
- **First-Audio Prompt Cue ("One moment..." / "Maaloo eegaa...")**:
  - **p50**: 0.00 ms
  - **p95**: 0.00 ms
  - *Result*: Zero dead air. The caller hears the acoustic cue immediately upon VAD endpointing.
- **Acoustic Voice Pipeline Turn Latency (Real Audio In -> Audio Out)**:
  - **p50**: 14.35 seconds
  - **p95**: 21.04 seconds
  - *Result*: End-to-end voice turnaround tested with real telephony spoken inputs.
- **Text-to-Speech Turn Latency (Text In -> Audio Out)**:
  - **p50**: 12.24 seconds
  - **p95**: 21.64 seconds

## 2. Stage-by-Stage Latency Breakdown
| Pipeline Stage | Subsystem | Average Latency |
|----------------|-----------|-----------------|
| VAD Silence Timeout | AudioSocket Endpointing | 1,000 ms (configurable) |
| Audio Prompt Cue | Pre-rendered In-Memory PCM (`prompts_audio.py`) | 0.00 ms |
| Speech-to-Text (STT) | Gemini STT / Local Whisper / HuggingFace | 3341.8 ms |
| Knowledge Retrieval | PostgreSQL `pgvector` Cosine Index (HNSW) | 5748.5 ms |
| Weather Forecast | Open-Meteo API / Redis Cache | 2.8 ms |
| LLM & Guardrails | Local / Cloud LLM + Numeric Word Transliteration | 1665.5 ms |
| Audio Synthesis (TTS) | Piper ONNX / Edge-TTS / Pre-rendered Prompts | 6641.6 ms |

## 3. Concurrency Limits & Architecture
- **Configured Concurrency Limit**: 2 simultaneous calls per free-tier worker.
- **Active Concurrency Lock**: Prevents rate-limit quota exhaustion on external APIs.
- **Zero-Dead-Air Acoustic Bridge**: Fixed prompts stream instantly from RAM cache while dynamic reasoning completes.
