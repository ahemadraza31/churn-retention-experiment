# Reproducibility Report (`scale=starter`)

**Result**: **PASS**

- **Run 1 Environment**: `PYTHONHASHSEED=1`
- **Run 2 Environment**: `PYTHONHASHSEED=2`

## 1. Per-Table Row Counts

| Table | Run 1 (`PYTHONHASHSEED=1`) | Run 2 (`PYTHONHASHSEED=2`) | Match |
| :--- | ---: | ---: | :---: |
| `billing_event` | 32379 | 32379 | `PASS` |
| `campaign_contact` | 0 | 0 | `PASS` |
| `churn_outcome` | 876 | 876 | `PASS` |
| `customer` | 1000 | 1000 | `PASS` |
| `eligibility_rule` | 0 | 0 | `PASS` |
| `feature_snapshot` | 0 | 0 | `PASS` |
| `offer` | 0 | 0 | `PASS` |
| `offer_eligibility_rule` | 0 | 0 | `PASS` |
| `retention_outcome` | 0 | 0 | `PASS` |
| `risk_score` | 0 | 0 | `PASS` |
| `rule_evaluation` | 0 | 0 | `PASS` |
| `state_event` | 2640 | 2640 | `PASS` |
| `subscription` | 1200 | 1200 | `PASS` |
| `support_case` | 1028 | 1028 | `PASS` |
| `usage_snapshot` | 16255 | 16255 | `PASS` |

## 2. Aggregate Metrics

| Metric | Run 1 (`PYTHONHASHSEED=1`) | Run 2 (`PYTHONHASHSEED=2`) | Match |
| :--- | ---: | ---: | :---: |
| `overall_churn_rate` | `0.120000` | `0.120000` | `PASS` |
| `voluntary_count` | `83` | `83` | `PASS` |
| `involuntary_count` | `37` | `37` | `PASS` |
| `plan_change_count` | `200` | `200` | `PASS` |
| `total_invoiced_cents` | `33583010` | `33583010` | `PASS` |
| `total_settled_cents` | `33514047` | `33514047` | `PASS` |

## 3. Latent Ground-Truth File SHA-256

| File | Run 1 SHA-256 | Run 2 SHA-256 | Match |
| :--- | :--- | :--- | :---: |
| `ground_truth/latent_customer_state.csv` | `cdd2bbbfe4d8eca6a32c3a5cb215c99302692f97e8bff897e49dedc87a34885f` | `cdd2bbbfe4d8eca6a32c3a5cb215c99302692f97e8bff897e49dedc87a34885f` | `PASS` |

## 4. Exported File SHA-256 Hashes

| File | Run 1 SHA-256 | Run 2 SHA-256 | Match |
| :--- | :--- | :--- | :---: |
| `csv/billing_event.csv` | `bb9ae7b893e5efcbfef028bc02797e00cbdbe21267193e357baf26464bcdbdee` | `bb9ae7b893e5efcbfef028bc02797e00cbdbe21267193e357baf26464bcdbdee` | `PASS` |
| `csv/campaign_contact.csv` | `cf439e67b36b0e3daa384236fbd6b7f0ebbd65717d3b935b490098d30c7b63ed` | `cf439e67b36b0e3daa384236fbd6b7f0ebbd65717d3b935b490098d30c7b63ed` | `PASS` |
| `csv/churn_outcome.csv` | `3af349e014bff249833c03293a0fddabcce524b5872d05bb0c5616af9d506d7c` | `3af349e014bff249833c03293a0fddabcce524b5872d05bb0c5616af9d506d7c` | `PASS` |
| `csv/customer.csv` | `42fceda91e1115b8cb1ceab10d66b873c9e102d79fcc5604a056209c8c6aa951` | `42fceda91e1115b8cb1ceab10d66b873c9e102d79fcc5604a056209c8c6aa951` | `PASS` |
| `csv/eligibility_rule.csv` | `e594adaef097a2c649eaa2eae96bc7e4c85b88294954a8f82c5871b30ee8afd5` | `e594adaef097a2c649eaa2eae96bc7e4c85b88294954a8f82c5871b30ee8afd5` | `PASS` |
| `csv/feature_snapshot.csv` | `59eabf113b7ab8122e0a8d548c17e2a4e71ade0b98dfe677c40dadbd3dc38d85` | `59eabf113b7ab8122e0a8d548c17e2a4e71ade0b98dfe677c40dadbd3dc38d85` | `PASS` |
| `csv/offer.csv` | `420fe145fde8aa33e5475dd33ee2581a01d584447b002e158180fb042c847d6f` | `420fe145fde8aa33e5475dd33ee2581a01d584447b002e158180fb042c847d6f` | `PASS` |
| `csv/offer_eligibility_rule.csv` | `92e454e172f539cf7e331a6d0d86a68a5545045522ffdfc448fcc65c0a22788e` | `92e454e172f539cf7e331a6d0d86a68a5545045522ffdfc448fcc65c0a22788e` | `PASS` |
| `csv/retention_outcome.csv` | `5dc5918ae9ba7c51efbfe4195d16a24383558b426c17da3f3f9e31ca8f52433d` | `5dc5918ae9ba7c51efbfe4195d16a24383558b426c17da3f3f9e31ca8f52433d` | `PASS` |
| `csv/risk_score.csv` | `231ef78da1b6668a049f3abc711a49de73d38539918a3b440d79d7e2b6711d74` | `231ef78da1b6668a049f3abc711a49de73d38539918a3b440d79d7e2b6711d74` | `PASS` |
| `csv/rule_evaluation.csv` | `56be9252129563e9410a3e30cb109f1f7b12a037178081fe43d97dce99d60066` | `56be9252129563e9410a3e30cb109f1f7b12a037178081fe43d97dce99d60066` | `PASS` |
| `csv/state_event.csv` | `bab1f7626566fe46e3290ef37838180dbab04fd3ae2901844067d75b045cadc0` | `bab1f7626566fe46e3290ef37838180dbab04fd3ae2901844067d75b045cadc0` | `PASS` |
| `csv/subscription.csv` | `ff0da53478779b8396aa286e86e85becac5ef6339cb720f532caf046bf2d7ea6` | `ff0da53478779b8396aa286e86e85becac5ef6339cb720f532caf046bf2d7ea6` | `PASS` |
| `csv/support_case.csv` | `2950fef5fd10e2daf0fd0b75b5a24a3f1c8698086819456ebc5af1049dbb0499` | `2950fef5fd10e2daf0fd0b75b5a24a3f1c8698086819456ebc5af1049dbb0499` | `PASS` |
| `csv/usage_snapshot.csv` | `66cab0c26503e1a93e1b32b3cecf47838e4c355095adfac438cca9220c97f3c6` | `66cab0c26503e1a93e1b32b3cecf47838e4c355095adfac438cca9220c97f3c6` | `PASS` |
| `json/billing_event.json` | `b924bb5cbbdaf2c9caae8cb7d79acc95f8ff266d909c72318e8b79cbd2950698` | `b924bb5cbbdaf2c9caae8cb7d79acc95f8ff266d909c72318e8b79cbd2950698` | `PASS` |
| `json/campaign_contact.json` | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` | `PASS` |
| `json/churn_outcome.json` | `3bc4c88fe0ac4b658150c2806f52df78e6390f6b672982e4c3446dc1c98eef8d` | `3bc4c88fe0ac4b658150c2806f52df78e6390f6b672982e4c3446dc1c98eef8d` | `PASS` |
| `json/customer.json` | `011ebcb58b611744534510df5fec1aca08d60f1ec9c7134e9de970eb3c811b10` | `011ebcb58b611744534510df5fec1aca08d60f1ec9c7134e9de970eb3c811b10` | `PASS` |
| `json/eligibility_rule.json` | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` | `PASS` |
| `json/feature_snapshot.json` | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` | `PASS` |
| `json/offer.json` | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` | `PASS` |
| `json/offer_eligibility_rule.json` | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` | `PASS` |
| `json/retention_outcome.json` | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` | `PASS` |
| `json/risk_score.json` | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` | `PASS` |
| `json/rule_evaluation.json` | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` | `PASS` |
| `json/state_event.json` | `30298a0bf44af5e9eb322c4cd7e6d3bb043cdaeb1d7a5c49ed1634febc66c45d` | `30298a0bf44af5e9eb322c4cd7e6d3bb043cdaeb1d7a5c49ed1634febc66c45d` | `PASS` |
| `json/subscription.json` | `97987f4b84a2b33c54712770b2c6378931235b8da8d81ba912b9d4f9fc423681` | `97987f4b84a2b33c54712770b2c6378931235b8da8d81ba912b9d4f9fc423681` | `PASS` |
| `json/support_case.json` | `70a743b13514f5738d99e8269324e441f38fafe3a5d141e7eb961fbbf3b4d00b` | `70a743b13514f5738d99e8269324e441f38fafe3a5d141e7eb961fbbf3b4d00b` | `PASS` |
| `json/usage_snapshot.json` | `a8bb542a7c2c4516c1d235373409a6c5b97a83599d74cb6e098d590ecbc3a9ea` | `a8bb542a7c2c4516c1d235373409a6c5b97a83599d74cb6e098d590ecbc3a9ea` | `PASS` |
| `sql/schema.sql` | `1025bbb340ba5823ab32a29d5438094a73c2a1fbfad9b96249afb1964ea3ea11` | `1025bbb340ba5823ab32a29d5438094a73c2a1fbfad9b96249afb1964ea3ea11` | `PASS` |
| `sql/seed.sql` | `ad1a332458fa4ecbf686f29f2e4b4ec338dab08b6a49a4aef36c3316b71a9a87` | `ad1a332458fa4ecbf686f29f2e4b4ec338dab08b6a49a4aef36c3316b71a9a87` | `PASS` |

Reproducibility Result: PASS
