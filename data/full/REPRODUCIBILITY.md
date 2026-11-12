# Reproducibility Report (`scale=full`)

**Result**: **PASS**

- **Run 1 Environment**: `PYTHONHASHSEED=1`
- **Run 2 Environment**: `PYTHONHASHSEED=2`

## 1. Per-Table Row Counts

| Table | Run 1 (`PYTHONHASHSEED=1`) | Run 2 (`PYTHONHASHSEED=2`) | Match |
| :--- | ---: | ---: | :---: |
| `billing_event` | 652796 | 652796 | `PASS` |
| `campaign_contact` | 0 | 0 | `PASS` |
| `churn_outcome` | 17738 | 17738 | `PASS` |
| `customer` | 20000 | 20000 | `PASS` |
| `eligibility_rule` | 0 | 0 | `PASS` |
| `feature_snapshot` | 0 | 0 | `PASS` |
| `offer` | 0 | 0 | `PASS` |
| `offer_eligibility_rule` | 0 | 0 | `PASS` |
| `retention_outcome` | 0 | 0 | `PASS` |
| `risk_score` | 0 | 0 | `PASS` |
| `rule_evaluation` | 0 | 0 | `PASS` |
| `state_event` | 52550 | 52550 | `PASS` |
| `subscription` | 23875 | 23875 | `PASS` |
| `support_case` | 20849 | 20849 | `PASS` |
| `usage_snapshot` | 327290 | 327290 | `PASS` |

## 2. Aggregate Metrics

| Metric | Run 1 (`PYTHONHASHSEED=1`) | Run 2 (`PYTHONHASHSEED=2`) | Match |
| :--- | ---: | ---: | :---: |
| `overall_churn_rate` | `0.120000` | `0.120000` | `PASS` |
| `voluntary_count` | `1709` | `1709` | `PASS` |
| `involuntary_count` | `691` | `691` | `PASS` |
| `plan_change_count` | `3875` | `3875` | `PASS` |
| `total_invoiced_cents` | `651841698` | `651841698` | `PASS` |
| `total_settled_cents` | `650621389` | `650621389` | `PASS` |

## 3. Latent Ground-Truth File SHA-256

| File | Run 1 SHA-256 | Run 2 SHA-256 | Match |
| :--- | :--- | :--- | :---: |
| `ground_truth/latent_customer_state.csv` | `22d00a6a7e527dff92cf4fd0a246e0af9489069f080a9130e015561d9e022b31` | `22d00a6a7e527dff92cf4fd0a246e0af9489069f080a9130e015561d9e022b31` | `PASS` |

## 4. Exported File SHA-256 Hashes

| File | Run 1 SHA-256 | Run 2 SHA-256 | Match |
| :--- | :--- | :--- | :---: |
| `csv/billing_event.csv` | `f6c200390d29d2940d345b50ce2016767b63a994b6d168d0ad071aae76e8fdf0` | `f6c200390d29d2940d345b50ce2016767b63a994b6d168d0ad071aae76e8fdf0` | `PASS` |
| `csv/campaign_contact.csv` | `cf439e67b36b0e3daa384236fbd6b7f0ebbd65717d3b935b490098d30c7b63ed` | `cf439e67b36b0e3daa384236fbd6b7f0ebbd65717d3b935b490098d30c7b63ed` | `PASS` |
| `csv/churn_outcome.csv` | `0bf416fff78930e52f642af2f23cc1e643e7c8af8967e14e95c6c6f536743c87` | `0bf416fff78930e52f642af2f23cc1e643e7c8af8967e14e95c6c6f536743c87` | `PASS` |
| `csv/customer.csv` | `24f3e5c13f7d6ef22d53cac855ae0635303c9f740c8c7d2c10fa04e26af7edc3` | `24f3e5c13f7d6ef22d53cac855ae0635303c9f740c8c7d2c10fa04e26af7edc3` | `PASS` |
| `csv/eligibility_rule.csv` | `e594adaef097a2c649eaa2eae96bc7e4c85b88294954a8f82c5871b30ee8afd5` | `e594adaef097a2c649eaa2eae96bc7e4c85b88294954a8f82c5871b30ee8afd5` | `PASS` |
| `csv/feature_snapshot.csv` | `59eabf113b7ab8122e0a8d548c17e2a4e71ade0b98dfe677c40dadbd3dc38d85` | `59eabf113b7ab8122e0a8d548c17e2a4e71ade0b98dfe677c40dadbd3dc38d85` | `PASS` |
| `csv/offer.csv` | `420fe145fde8aa33e5475dd33ee2581a01d584447b002e158180fb042c847d6f` | `420fe145fde8aa33e5475dd33ee2581a01d584447b002e158180fb042c847d6f` | `PASS` |
| `csv/offer_eligibility_rule.csv` | `92e454e172f539cf7e331a6d0d86a68a5545045522ffdfc448fcc65c0a22788e` | `92e454e172f539cf7e331a6d0d86a68a5545045522ffdfc448fcc65c0a22788e` | `PASS` |
| `csv/retention_outcome.csv` | `5dc5918ae9ba7c51efbfe4195d16a24383558b426c17da3f3f9e31ca8f52433d` | `5dc5918ae9ba7c51efbfe4195d16a24383558b426c17da3f3f9e31ca8f52433d` | `PASS` |
| `csv/risk_score.csv` | `231ef78da1b6668a049f3abc711a49de73d38539918a3b440d79d7e2b6711d74` | `231ef78da1b6668a049f3abc711a49de73d38539918a3b440d79d7e2b6711d74` | `PASS` |
| `csv/rule_evaluation.csv` | `56be9252129563e9410a3e30cb109f1f7b12a037178081fe43d97dce99d60066` | `56be9252129563e9410a3e30cb109f1f7b12a037178081fe43d97dce99d60066` | `PASS` |
| `csv/state_event.csv` | `40aca4d3f215db9a8856690bcc411d06141d6269ad1f60b52f18cd8a0869baf9` | `40aca4d3f215db9a8856690bcc411d06141d6269ad1f60b52f18cd8a0869baf9` | `PASS` |
| `csv/subscription.csv` | `2697b875e5c938f3d8389078b5c381e3621b4585d99351436935bbc2f7505f90` | `2697b875e5c938f3d8389078b5c381e3621b4585d99351436935bbc2f7505f90` | `PASS` |
| `csv/support_case.csv` | `14c98c90594c4971872f75eac334d10c70d8c87e035751d2c5013403a9fc8765` | `14c98c90594c4971872f75eac334d10c70d8c87e035751d2c5013403a9fc8765` | `PASS` |
| `csv/usage_snapshot.csv` | `caec4d91db4525cc4f53ba31d4d301509b89146f41af650f22de9135ed702f4a` | `caec4d91db4525cc4f53ba31d4d301509b89146f41af650f22de9135ed702f4a` | `PASS` |

Reproducibility Result: PASS
