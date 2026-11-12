# Reproducibility Report (`scale=full`)

**Result**: **PASS**

- **Run 1 Environment**: `PYTHONHASHSEED=1`
- **Run 2 Environment**: `PYTHONHASHSEED=2`

## 1. Per-Table Row Counts

| Table | Run 1 (`PYTHONHASHSEED=1`) | Run 2 (`PYTHONHASHSEED=2`) | Match |
| :--- | ---: | ---: | :---: |
| `billing_event` | 653119 | 653119 | `PASS` |
| `campaign_contact` | 4867 | 4867 | `PASS` |
| `churn_outcome` | 36101 | 36101 | `PASS` |
| `customer` | 20000 | 20000 | `PASS` |
| `eligibility_rule` | 7 | 7 | `PASS` |
| `feature_snapshot` | 36089 | 36089 | `PASS` |
| `offer` | 3 | 3 | `PASS` |
| `offer_eligibility_rule` | 21 | 21 | `PASS` |
| `retention_outcome` | 4867 | 4867 | `PASS` |
| `risk_score` | 18363 | 18363 | `PASS` |
| `rule_evaluation` | 165267 | 165267 | `PASS` |
| `state_event` | 64021 | 64021 | `PASS` |
| `subscription` | 23875 | 23875 | `PASS` |
| `support_case` | 20859 | 20859 | `PASS` |
| `usage_snapshot` | 327426 | 327426 | `PASS` |

## 2. Aggregate Metrics

| Metric | Run 1 (`PYTHONHASHSEED=1`) | Run 2 (`PYTHONHASHSEED=2`) | Match |
| :--- | ---: | ---: | :---: |
| `overall_churn_rate` | `0.117450` | `0.117450` | `PASS` |
| `voluntary_count` | `1658` | `1658` | `PASS` |
| `involuntary_count` | `691` | `691` | `PASS` |
| `plan_change_count` | `3875` | `3875` | `PASS` |
| `total_invoiced_cents` | `652125538` | `652125538` | `PASS` |
| `total_settled_cents` | `650905229` | `650905229` | `PASS` |

## 3. Latent Ground-Truth File SHA-256

| File | Run 1 SHA-256 | Run 2 SHA-256 | Match |
| :--- | :--- | :--- | :---: |
| `ground_truth/latent_customer_state.csv` | `8a4f907c8770997f5cf262813ceff158182d59be6d396fe3ee6b7545486b5eda` | `8a4f907c8770997f5cf262813ceff158182d59be6d396fe3ee6b7545486b5eda` | `PASS` |

## 4. Exported File SHA-256 Hashes

| File | Run 1 SHA-256 | Run 2 SHA-256 | Match |
| :--- | :--- | :--- | :---: |
| `csv/billing_event.csv` | `50d54159852b4f42b709105662ee4dd4bad66def240f8c65e6e39503f7fcf735` | `50d54159852b4f42b709105662ee4dd4bad66def240f8c65e6e39503f7fcf735` | `PASS` |
| `csv/campaign_contact.csv` | `6a16eaec56976d8ed8dc36860d8c9aafec491e96f28fe3d9d12f0655566f1812` | `6a16eaec56976d8ed8dc36860d8c9aafec491e96f28fe3d9d12f0655566f1812` | `PASS` |
| `csv/churn_outcome.csv` | `027dad2676d4a81cf7caa2b683f5a0b3a8e35a344d0854c8fd9fa8591aa17c2a` | `027dad2676d4a81cf7caa2b683f5a0b3a8e35a344d0854c8fd9fa8591aa17c2a` | `PASS` |
| `csv/customer.csv` | `24f3e5c13f7d6ef22d53cac855ae0635303c9f740c8c7d2c10fa04e26af7edc3` | `24f3e5c13f7d6ef22d53cac855ae0635303c9f740c8c7d2c10fa04e26af7edc3` | `PASS` |
| `csv/eligibility_rule.csv` | `40b51ca0da8aa83fa00d4302640d519fd0a67c4d0d0a32586d271dbb6d70c150` | `40b51ca0da8aa83fa00d4302640d519fd0a67c4d0d0a32586d271dbb6d70c150` | `PASS` |
| `csv/feature_snapshot.csv` | `53fe255b89bec1688e8cbf65e002ded249dba96def3f905887d81a75abd00609` | `53fe255b89bec1688e8cbf65e002ded249dba96def3f905887d81a75abd00609` | `PASS` |
| `csv/offer.csv` | `587262ca603ffdb02d78ed5f3160dbc072f5a72d3ad4b560893fed081b26ca39` | `587262ca603ffdb02d78ed5f3160dbc072f5a72d3ad4b560893fed081b26ca39` | `PASS` |
| `csv/offer_eligibility_rule.csv` | `abaec520ecf93753458748d3dc48a56288672ce25ac2b539fe5709748b124d16` | `abaec520ecf93753458748d3dc48a56288672ce25ac2b539fe5709748b124d16` | `PASS` |
| `csv/retention_outcome.csv` | `9e2510c44d508c803f4c4946815d0859c382363ebab84e58cb68b1c1e50011e9` | `9e2510c44d508c803f4c4946815d0859c382363ebab84e58cb68b1c1e50011e9` | `PASS` |
| `csv/risk_score.csv` | `aba0005aa58744e7f5b51bfb177e1758ba355db8ae5d0a9f2616c5f72fb9a01c` | `aba0005aa58744e7f5b51bfb177e1758ba355db8ae5d0a9f2616c5f72fb9a01c` | `PASS` |
| `csv/rule_evaluation.csv` | `7b0d53cf59d8027cf776a7dc41e7b7a229ef183eea85bc00b3186af3b755d9bf` | `7b0d53cf59d8027cf776a7dc41e7b7a229ef183eea85bc00b3186af3b755d9bf` | `PASS` |
| `csv/state_event.csv` | `5442a706c500bb8fadab48b8f14cb2cc5592378a9a9be62ea851b566eccc0cc1` | `5442a706c500bb8fadab48b8f14cb2cc5592378a9a9be62ea851b566eccc0cc1` | `PASS` |
| `csv/subscription.csv` | `0c7a4d21d27c68d2ce49b417706917d62ec26d82f45f048b5201566a701fca62` | `0c7a4d21d27c68d2ce49b417706917d62ec26d82f45f048b5201566a701fca62` | `PASS` |
| `csv/support_case.csv` | `b81e32e196b1217978f3be7731cbb312a46a0b788b5b7c39698bb29e6df24fa3` | `b81e32e196b1217978f3be7731cbb312a46a0b788b5b7c39698bb29e6df24fa3` | `PASS` |
| `csv/usage_snapshot.csv` | `048363f46bfa6923d6cfc10c719b5887221f1244f3fa3013f1229cfc8bfab7ed` | `048363f46bfa6923d6cfc10c719b5887221f1244f3fa3013f1229cfc8bfab7ed` | `PASS` |

Reproducibility Result: PASS
