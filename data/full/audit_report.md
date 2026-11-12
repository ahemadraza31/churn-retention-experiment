# Ground Truth Audit Report (full)

**Audit Status**: **PASS**
**Detector Target**: 100% Precision and 100% Recall on all anomalies (A, B, C, D)

## 1. Detector Performance vs Ground Truth

| Detector Rule | Type | Severity | Ground Truth | Detected | TP | FP | FN | Precision | Recall | Status |
| :--- | :---: | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| `DET-A-LABEL-BEFORE-PREDICTION` | A | CRITICAL | 40 | 40 | 40 | 0 | 0 | 1.0000 | 1.0000 | **PASS** |
| `DET-B-INELIGIBLE-OFFER` | B | CRITICAL | 40 | 40 | 40 | 0 | 0 | 1.0000 | 1.0000 | **PASS** |
| `DET-C-GROUP-LEAKAGE` | C | CRITICAL | 40 | 40 | 40 | 0 | 0 | 1.0000 | 1.0000 | **PASS** |
| `DET-D-MULTI-ATTRIBUTION` | D | HIGH | 40 | 40 | 40 | 0 | 0 | 1.0000 | 1.0000 | **PASS** |

## 2. Causal Lift Estimator Audit (180-day ITT)

- **Unflagged W01 Treatment Population**: 2354
- **Ground Truth Saved Customers (`true_effect_flag == 1`)**: 50
- **True 180-day ITT Treatment Effect**: `0.0212` (2.12%)
- **Estimated 180-day ITT Lift**: `+0.0130` (+1.30 pp)
- **Estimated 95% Confidence Interval**: `[+0.0010, +0.0251]` ([+0.10 pp, +2.51 pp])
- **CI Contains True Effect**: **YES (VALID)**

## 3. Overall Audit Verdict

**AUDIT STATUS: PASS**
