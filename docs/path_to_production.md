# Path to Production (docs/path_to_production.md)

This document outlines the engineering, operational, and agronomic milestones required to transition Hello Farmer from an evaluation MVP to a reliable national pilot in Ethiopia.

---

## 1. Telecom & Infrastructure Integration
1. **Direct E1/PRI or SIP Trunking with Ethio Telecom / Safaricom Ethiopia**:
   - Transition from local softphone testing to carrier-grade SIP trunks.
   - High-availability Asterisk / FreeSWITCH clusters with Kamailio SIP proxy load balancers.
   - Support for short code `8028` integration or dedicated regional agricultural toll-free numbers.
2. **Hardware Sizing**:
   - On-premises or local cloud hosting (e.g. Ethiopian Data Center) for low network latency (<50ms).
   - Dedicated GPU nodes (NVIDIA L4 / A10G) for real-time speech-to-text inference with sub-second RTF.

---

## 2. Speech Models & Local Languages
1. **Acoustic Model Customization**:
   - Collect 500+ hours of rural telephone speech in Amharic, Afaan Oromo, Tigrigna, Somali, and Sidama.
   - Fine-tune Whisper / MMS specifically on 8 kHz narrowband GSM/AMR phone audio.
2. **High-Fidelity Local Neural TTS**:
   - Train custom neural TTS models (e.g. VITS / Matcha-TTS) with native rural Ethiopian speakers for warm, trustworthy agronomic delivery.

---

## 3. Agronomic Knowledge Base & Governance
1. **Direct Integration with Ministry of Agriculture (MoA) & EIAR**:
   - Establish an automated ingestion pipeline for vetted extension advisories.
   - Mandatory human agronomist sign-off on all Tier 1 documents and dosage limits.
2. **Continuous Agronomic Safety Audits**:
   - Automated regression test suite running daily against poison control guidelines and agrochemical regulations.
   - Direct integration with local Woreda Development Agents (DAs) for complex case referrals.

---

## 4. Privacy, Regulation, and Resilience
1. **Compliance with Ethiopian Data Protection Proclamations**:
   - Local data residency compliance.
   - Strict encryption keys management using Hardware Security Modules (HSM).
2. **Fallback & Emergency Resilience**:
   - Redundant fallback chains ensuring the telephony line never drops or goes silent during network partitions or cloud provider outages.
