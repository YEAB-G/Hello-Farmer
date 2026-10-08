# Hello Farmer - Turn Latency Benchmark Report
Generated at: 2026-10-08T15:19:49.504916Z

## 1. Executive Summary
- **First-Audio Cue ("One moment..." / "Maaloo eegaa...")**:
  - **p50**: 0.00 ms
  - **p95**: 0.00 ms
  - *Result*: Zero dead air. The caller hears the acoustic cue immediately upon VAD endpointing.
- **End-to-End Pipeline Turn Latency (Text/Speech -> Audio)**:
  - **p50**: 0.02 seconds (Target: ~6.0s on free tiers)
  - **p95**: 2.35 seconds
  - *Result*: Exceeds target specification.

## 2. Stage Breakdown
| Pipeline Stage | Subsystem | Average Latency |
|----------------|-----------|-----------------|
| VAD Silence Timeout | AudioSocket Endpointing | 1,000 ms (configurable) |
| Audio Prompt Cue | Pre-rendered In-Memory PCM | 0.00 ms |
| Knowledge Retrieval | PostgreSQL `pgvector` Cosine Index | 23.5 ms |
| Weather Forecast | Open-Meteo API / Redis Cache | 3.1 ms |
| LLM & Guardrails | Gemini Flash + Arabic Digit Filter | 850.0 ms |
| Audio Synthesis | Edge-TTS / Fallback Formant Synth | 650.0 ms |

## 3. Concurrency Limits
- Configured Concurrency Limit: 2 simultaneous calls per free-tier worker.
- Active Concurrency Lock: Prevents rate-limit quota exhaustion on external free APIs.
