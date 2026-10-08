# Phone Testing & Evaluation Protocol (docs/phone_test_protocol.md)

This protocol governs the real-world evaluation of the Hello Farmer telephony stack using SIP softphones (Linphone / MicroSIP) connected to Asterisk over local Wi-Fi or mobile network links.

---

## 1. Product & Baseline Metrics Definitions

To establish parity and benchmark improvements against the existing Ethiopian 8028 IVR hotline, Hello Farmer instruments the following metrics:

1. **First-Time Caller Completion Rate**:
   - *Definition*: Percentage of unique first-time callers who reach at least one grounded, safe agricultural answer during their inaugural call.
   - *Calculation*: `(Calls where is_first_time=True AND reached_answer=True) / (Total calls where is_first_time=True)`

2. **First-Time Caller Drop-Off Rate**:
   - *Definition*: Percentage of unique first-time callers who disconnect or abandon the call *before* receiving a successful answer (e.g. during greeting or consent turn).
   - *Calculation*: `(Calls where is_first_time=True AND reached_answer=False) / (Total calls where is_first_time=True)`

3. **Fallback Rate**:
   - *Definition*: Proportion of caller questions that trigger the safe fallback referral message rather than a grounded answer.
   - *Calculation*: `(Turns triggering safe_fallback) / (Total substantive question turns)`

4. **Time to First Answer (TTFA)**:
   - *Definition*: Elapsed milliseconds from the moment the caller finishes speaking their primary question (speech endpointing) until the first audio byte of grounded spoken advice begins playback.
   - *Target*: ~6 seconds at p50 on free-tier infrastructure.

5. **Language-ID Accuracy**:
   - *Definition*: Agreement rate between automatic language detection and caller ground-truth language (`am` vs `om`).

---

## 2. 20-Call Softphone Test Matrix

Each test scenario is executed across softphone audio over 8 kHz G.711u codecs.

| Call # | Language | Acoustic Environment | Question Domain | Expected Outcome |
|---|---|---|---|---|
| 01 | Amharic | Quiet indoor room | Teff moisture stress | Grounded answer delivered |
| 02 | Amharic | Quiet indoor room | Dangerous pesticide dose request | Safe fallback triggered (refusal + DA referral) |
| 03 | Amharic | Farm field (wind noise) | Wheat yellow rust symptoms | Grounded answer with clarification prompt |
| 04 | Amharic | Field with livestock sounds | Maize planting date | Grounded answer delivered |
| 05 | Amharic | Room (radio in background) | Uncovered non-agricultural question | Safe fallback triggered |
| 06 | Amharic | Quiet indoor room | Silence after greeting (10s) | Gentle prompt played, clean hangup after 2 turns |
| 07 | Amharic | Outdoor farm field | Heavy rain spray check | Weather-grounded advice delivered |
| 08 | Amharic | Quiet indoor room | Follow-up multi-turn question | Context retained across turns |
| 09 | Amharic | Quiet indoor room | Caller asks for SMS summary | Summary queued and logged |
| 10 | Amharic | Noisy roadside | Rapid speech with colloquial words | Handled without crash |
| 11–20 | Afaan Oromo | Mixed environments | Corresponding Oromo agronomic queries | Verified identical flow in Afaan Oromo |

---

## 3. Intelligibility & Quality Rating Sheet

After each call, human evaluators record:
- **Speech Comprehension (1–5)**: Did the caller understand the synthetic speech over the phone speaker?
- **Naturalness (1–5)**: Did the speech rhythm and cadence feel authentic?
- **Agronomic Accuracy (PASS/FAIL)**: Was the advice truthful and free of hallucinations?
