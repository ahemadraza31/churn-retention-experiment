# Ground Truth Audit Report (starter)

**Audit Status**: **PASS**
**Detector Target**: 100% Precision and 100% Recall on all anomalies (A, B, C, D)

## 1. Detector Performance vs Ground Truth

| Detector Rule | Type | Severity | Ground Truth | Detected | TP | FP | FN | Precision | Recall | Status |
| :--- | :---: | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| `DET-A-LABEL-BEFORE-PREDICTION` | A | CRITICAL | 10 | 10 | 10 | 0 | 0 | 1.0000 | 1.0000 | **PASS** |
| `DET-B-INELIGIBLE-OFFER` | B | CRITICAL | 10 | 10 | 10 | 0 | 0 | 1.0000 | 1.0000 | **PASS** |
| `DET-C-GROUP-LEAKAGE` | C | CRITICAL | 10 | 10 | 10 | 0 | 0 | 1.0000 | 1.0000 | **PASS** |
| `DET-D-MULTI-ATTRIBUTION` | D | HIGH | 10 | 10 | 10 | 0 | 0 | 1.0000 | 1.0000 | **PASS** |

## 2. Causal Lift Estimator Audit (180-day ITT)

- **Unflagged W01 Treatment Population**: 92
- **Ground Truth Saved Customers (`true_effect_flag == 1`)**: 1
- **True 180-day ITT Treatment Effect**: `0.0109` (1.09%)
- **Estimated 180-day ITT Lift**: `+0.0323` (+3.23 pp)
- **Estimated 95% Confidence Interval**: `[-0.0192, +0.0839]` ([-1.92 pp, +8.39 pp])
- **CI Contains True Effect**: **YES (VALID)**

## 3. Overall Audit Verdict

**AUDIT STATUS: PASS**
