# Real Voice STT Benchmark Evaluation Report

**Generated**: 2026-11-08 18:05:10 UTC
**Source Audio**: Real studio and telephony spoken audio from `C:\Users\user\OneDrive\Desktop\New folder\Hello-Farmer\backend\cache\prompts`
**Total Utterances**: 13 items across Amharic, Afaan Oromo, and English

| Provider | Condition | Amharic WER (Raw/Norm) | Amharic CER | Oromo WER (Raw/Norm) | Oromo CER | English WER (Raw/Norm) | p50 Latency (ms) |
|---|---|---|---|---|---|---|---|
| Gemini STT | 16k_clean | 43.6% / 34.0% | 19.7% | 100.0% / 100.0% | 100.0% | 100.0% / 100.0% | 1880.3 ms |
| Gemini STT | 8k_narrowband | 49.0% / 41.1% | 23.9% | 100.0% / 100.0% | 100.0% | 100.0% / 100.0% | 1616.4 ms |
| Gemini STT | g711_telephony | 46.6% / 41.9% | 21.7% | 100.0% / 100.0% | 100.0% | 100.0% / 100.0% | 1887.1 ms |
| Whisper Local | 16k_clean | 100.0% / 100.0% | 100.0% | 100.0% / 100.0% | 100.0% | 100.0% / 100.0% | 1.4 ms |
| Whisper Local | 8k_narrowband | 100.0% / 100.0% | 100.0% | 100.0% / 100.0% | 100.0% | 100.0% / 100.0% | 1.3 ms |
| Whisper Local | g711_telephony | 100.0% / 100.0% | 100.0% | 100.0% / 100.0% | 100.0% | 100.0% / 100.0% | 1.2 ms |
| HuggingFace STT | 16k_clean | 38.6% / 34.0% | 21.6% | 100.0% / 100.0% | 100.0% | 100.0% / 100.0% | 1836.2 ms |
| HuggingFace STT | 8k_narrowband | 50.7% / 46.1% | 25.6% | 100.0% / 100.0% | 100.0% | 100.0% / 100.0% | 2853.5 ms |
| HuggingFace STT | g711_telephony | 46.8% / 42.2% | 25.1% | 100.0% / 100.0% | 100.0% | 100.0% / 100.0% | 1770.4 ms |
