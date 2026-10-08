# Privacy, Consent, and Data Protection Policy (docs/privacy.md)

*Effective Date: October 2026*  
*Applicability: Hello Farmer Voice Assistant Architecture & Data Storage*

---

## 1. Core Principles
1. **Zero Persistence by Default**: No call recording, transcript, or personal data is persisted unless the caller grants explicit voice consent.
2. **Hashed Identification**: Callers are identified solely by a cryptographically salted SHA-256 hash (`caller_hash`). Plaintext phone numbers are never stored in standard call records or conversation logs.
3. **Encrypted Opt-In Storage**: Only callers who explicitly opt in to receive post-call SMS or proactive weather warnings have their telephone numbers stored, encrypted at rest using AES-256 (Fernet) via `PHONE_ENCRYPTION_KEY`.
4. **Shared Device Awareness**: In rural Ethiopian households, mobile devices are frequently shared among family members or neighbors. The system treats stored crop context as tentative and allows callers to correct or override stored preferences at any time.

---

## 2. Voice Consent Protocol

During the first turn of a call from an unrecognized `caller_hash`, the assistant issues a spoken consent query:
- **Amharic**: *"ይህ አገልግሎት እንዲሻሻል ጥያቄዎ እንዲቀመጥ ይፈቅዳሉ?"* (Do you agree to saving your question to improve this service?)
- **Afaan Oromo**: *"Tajaajilli kun akka fooyya'uuf gaaffiin keessan akka galmaa'u ni eeyyamtuu?"*

**Evaluation Rules**:
- An affirmative voice response ("አዎ" / "Eeyyee" / "እሺ") flags `has_consented = True` and creates a `consent_records` row.
- Any negative, ambiguous, or silent response flags `has_consented = False`.
- In non-consented sessions, conversation state remains in volatile RAM only for the duration of the call and is wiped immediately upon call hangup.

---

## 3. Data Retention & Deletion
1. **Session Volatility**: Unconsented call memory is destroyed on disconnect.
2. **Consented Records Retention**: Stored queries and anonymized interaction metrics expire after 90 days.
3. **Right to Erasure**: Callers can request deletion of their profile and history. Deletion cascades across `farmers`, `farmer_context`, `farmer_crops`, and `sms_messages` by `caller_hash`.
