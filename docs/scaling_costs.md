# Scaling Cost Projections (docs/scaling_costs.md)

*Scope: Cost estimation for 1,000 completed telephone calls (averaging 3 minutes / 6 conversation turns per call) transitioning from free tiers to commercial cloud providers.*

---

## 1. Workload Assumptions (Per 1,000 Calls)

| Metric | Per Turn | Per Call (6 turns) | Total (1,000 calls) |
|---|---|---|---|
| **Audio In (Caller)** | 5 seconds (speech) | 30 seconds | 500 minutes (8.33 hours) |
| **Audio Out (TTS)** | 40 words (~12s) | 72 seconds | 1,200 minutes (20 hours) |
| **Input Tokens (LLM)** | ~600 tokens (incl context) | ~3,600 tokens | 3,600,000 tokens |
| **Output Tokens (LLM)**| ~60 tokens | ~360 tokens | 360,000 tokens |
| **RAG Queries** | 1 query | 6 queries | 6,000 queries |

---

## 2. Cost Breakdown by Commercial Cloud Service

### 2.1 LLM Inference (Google Gemini Flash Pay-As-You-Go)
- Input: $0.075 per 1M tokens -> 3.6M * $0.075 = **$0.27**
- Output: $0.30 per 1M tokens -> 0.36M * $0.30 = **$0.11**
- **Subtotal LLM**: **$0.38**

### 2.2 Speech-to-Text (STT)
- *Option A: Self-hosted MMS 1B on GPU (e.g., T4 instance @ $0.35/hr)*:
  - 8.33 audio hours @ ~0.2x Real-Time Factor = 1.66 GPU hours = **$0.58**
- *Option B: Commercial Cloud STT (e.g., Google Cloud Speech-to-Text @ $0.024/min)*:
  - 500 minutes * $0.024 = **$12.00**

### 2.3 Text-to-Speech (TTS)
- *Option A: Self-hosted MMS-TTS (CPU/GPU)*: **$0.20** (Compute time)
- *Option B: Microsoft Azure Cognitive Neural TTS ($16.00 per 1M characters)*:
  - ~240,000 characters * $16.00 / 1M = **$3.84**

### 2.4 Telephony & Infrastructure (Host VM & SIP Trunk)
- Local SIP Trunk (Ethio Telecom / VoIP gateway): ~$0.02 / call = **$20.00**
- Cloud VM (2 vCPU, 8GB RAM, e.g., Hetzner / AWS Lightsail): ~$10/month prorated = **$0.50**

---

## 3. Total Estimated Cost Comparison (1,000 Calls)

| Architecture Strategy | LLM | STT | TTS | Infrastructure/SIP | Total for 1,000 Calls | Cost Per Call |
|---|---|---|---|---|---|---|
| **Hybrid (Self-hosted Speech + Gemini Flash)** | $0.38 | $0.58 | $0.20 | $20.50 | **$21.66** | **~$0.022** |
| **Fully Commercial Cloud (Google/Azure APIs)** | $0.38 | $12.00 | $3.84 | $20.50 | **$36.72** | **~$0.037** |
| **Hello Farmer Free-Tier Prototype** | **$0.00** | **$0.00** | **$0.00** | **$0.00** | **$0.00** | **$0.00** |

*Conclusion: A hybrid architecture keeping speech recognition and synthesis on self-hosted models while leveraging frontier flash LLMs enables serving 1,000 rural farming families for under $22.*
