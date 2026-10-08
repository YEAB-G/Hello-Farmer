# Hello Farmer - VAD Speech Endpointing Evaluation Report

Evaluates speech cutoffs, telephone noise rejection, and silence timeouts.

| Test Scenario | Measured Metric | Result |
|---------------|-----------------|--------|
| Conversational pause (300ms) & Trailing silence (1.0s) | Trailing Silence: 1020ms, False Cutoff: False | PASS |
| Narrowband phone line noise immunity (RMS 250) | False speech trigger: False | PASS |
| Initial silence timeout detection (5.0s) | Triggered timeout: True | PASS |
| Maximum utterance duration capping (10.0s limit) | Capped safely: True | PASS |

## Findings & Recommendations
- **Silence Threshold**: 1000ms silence timeout provides natural pacing for rural Ethiopian callers.
- **Pause Rejection**: 300ms mid-utterance conversational pauses do not trigger premature truncation.
- **Line Noise**: G.711 narrowband line hiss below RMS 350 is safely rejected without false speech triggers.
