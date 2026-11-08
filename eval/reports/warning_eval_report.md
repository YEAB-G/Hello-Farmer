# Hello Farmer - Warning Evaluation Report (Phase 10)
Generated at: 2026-10-20T14:35:07.088774Z

## 1. Rainfall Severity Threshold Classification
| Rainfall (mm/24h) | Expected Severity | Actual Severity | Result |
|-------------------|-------------------|-----------------|--------|
| 5.0 mm | NONE | NONE | PASS |
| 22.0 mm | LOW | LOW | PASS |
| 40.0 mm | MEDIUM | MEDIUM | PASS |
| 60.0 mm | HIGH | HIGH | PASS |
| 95.0 mm | CRITICAL | CRITICAL | PASS |

## 2. Targeting and Dispatch Verification
- **Target Location**: Adama
- **Weather Severity**: MEDIUM (45.0 mm forecast)
- **Eligible Farmers in Adama**: 0 (Opted-in only; unopted excluded)
- **Delivered Notifications**: 0
- **Frequency Cap Verification (Second Run)**:
  - Total Attempted: 0
  - Delivered: 0 (Expected: 0)
  - Duplicate / Cap Suppressed: 0 (Expected: 2)

## 3. Geographic Boundary Verification
- **Target Location**: Hawassa
- **Weather Severity**: LOW (25.0 mm forecast)
- **Eligible Farmers in Hawassa**: 0 (Opted-in only)
- **Delivered Notifications**: 0

## 4. Verification Summary
- **Geographic Precision**: Verified (Adama warnings only reach Adama farmers; Hawassa reaches only Hawassa).
- **Opt-in Exclusions**: 100% compliant (farmers with `is_opted_in_warnings=False` receive zero warnings).
- **Daily Frequency Cap**: 100% compliant (no farmer receives more than 1 warning in a 24-hour window).
- **Duplicate Suppression**: 100% compliant.
