# Reproducibility Report (`scale=starter`)

**Result**: **PASS**

- **Run 1 Environment**: `PYTHONHASHSEED=1`
- **Run 2 Environment**: `PYTHONHASHSEED=2`

## 1. Per-Table Row Counts

| Table | Run 1 (`PYTHONHASHSEED=1`) | Run 2 (`PYTHONHASHSEED=2`) | Match |
| :--- | ---: | ---: | :---: |
| `billing_event` | 32381 | 32381 | `PASS` |
| `campaign_contact` | 253 | 253 | `PASS` |
| `churn_outcome` | 1803 | 1803 | `PASS` |
| `customer` | 1000 | 1000 | `PASS` |
| `eligibility_rule` | 7 | 7 | `PASS` |
| `feature_snapshot` | 1793 | 1793 | `PASS` |
| `offer` | 3 | 3 | `PASS` |
| `offer_eligibility_rule` | 21 | 21 | `PASS` |
| `retention_outcome` | 253 | 253 | `PASS` |
| `risk_score` | 917 | 917 | `PASS` |
| `rule_evaluation` | 8253 | 8253 | `PASS` |
| `state_event` | 3165 | 3165 | `PASS` |
| `subscription` | 1200 | 1200 | `PASS` |
| `support_case` | 1028 | 1028 | `PASS` |
| `usage_snapshot` | 16255 | 16255 | `PASS` |

## 2. Aggregate Metrics

| Metric | Run 1 (`PYTHONHASHSEED=1`) | Run 2 (`PYTHONHASHSEED=2`) | Match |
| :--- | ---: | ---: | :---: |
| `overall_churn_rate` | `0.119000` | `0.119000` | `PASS` |
| `voluntary_count` | `82` | `82` | `PASS` |
| `involuntary_count` | `37` | `37` | `PASS` |
| `plan_change_count` | `200` | `200` | `PASS` |
| `total_invoiced_cents` | `33585009` | `33585009` | `PASS` |
| `total_settled_cents` | `33516046` | `33516046` | `PASS` |

## 3. Latent Ground-Truth File SHA-256

| File | Run 1 SHA-256 | Run 2 SHA-256 | Match |
| :--- | :--- | :--- | :---: |
| `ground_truth/latent_customer_state.csv` | `925b484849b2948facee5fe60c5731bf6c3aadbbe3741e52c3997c0b6082ca1f` | `925b484849b2948facee5fe60c5731bf6c3aadbbe3741e52c3997c0b6082ca1f` | `PASS` |

## 4. Exported File SHA-256 Hashes

| File | Run 1 SHA-256 | Run 2 SHA-256 | Match |
| :--- | :--- | :--- | :---: |
| `anomaly_report.json` | `42b0f946cfa43a58e22edd6f5e153e8631a30f090c325a74375dbee86d6f2f20` | `42b0f946cfa43a58e22edd6f5e153e8631a30f090c325a74375dbee86d6f2f20` | `PASS` |
| `csv/billing_event.csv` | `9029232484674bed1be5c3e7123a556ccc08d1ea2701198700f87b40ee790e39` | `9029232484674bed1be5c3e7123a556ccc08d1ea2701198700f87b40ee790e39` | `PASS` |
| `csv/campaign_contact.csv` | `cbdb6f55533d58f9209aae36e2c6b31592aac83f381b9d6d392d4651ed8835d4` | `cbdb6f55533d58f9209aae36e2c6b31592aac83f381b9d6d392d4651ed8835d4` | `PASS` |
| `csv/churn_outcome.csv` | `860834071a2a50caae31e46137df15851518c53d378ae08d140fb34d79957cf0` | `860834071a2a50caae31e46137df15851518c53d378ae08d140fb34d79957cf0` | `PASS` |
| `csv/customer.csv` | `42fceda91e1115b8cb1ceab10d66b873c9e102d79fcc5604a056209c8c6aa951` | `42fceda91e1115b8cb1ceab10d66b873c9e102d79fcc5604a056209c8c6aa951` | `PASS` |
| `csv/eligibility_rule.csv` | `40b51ca0da8aa83fa00d4302640d519fd0a67c4d0d0a32586d271dbb6d70c150` | `40b51ca0da8aa83fa00d4302640d519fd0a67c4d0d0a32586d271dbb6d70c150` | `PASS` |
| `csv/feature_snapshot.csv` | `b9d01828cefb90061980e0b7ce6c9ceb5bf9adfdb27e5dd2845929f0e760b60e` | `b9d01828cefb90061980e0b7ce6c9ceb5bf9adfdb27e5dd2845929f0e760b60e` | `PASS` |
| `csv/offer.csv` | `587262ca603ffdb02d78ed5f3160dbc072f5a72d3ad4b560893fed081b26ca39` | `587262ca603ffdb02d78ed5f3160dbc072f5a72d3ad4b560893fed081b26ca39` | `PASS` |
| `csv/offer_eligibility_rule.csv` | `abaec520ecf93753458748d3dc48a56288672ce25ac2b539fe5709748b124d16` | `abaec520ecf93753458748d3dc48a56288672ce25ac2b539fe5709748b124d16` | `PASS` |
| `csv/retention_outcome.csv` | `491d5157b7aaaf533019055523737b697f9a600ef2cb9739c935716896a5a169` | `491d5157b7aaaf533019055523737b697f9a600ef2cb9739c935716896a5a169` | `PASS` |
| `csv/risk_score.csv` | `1e632894586b39137d89bbdc94b3dd78a439bc1fe15ed3a635a32abe9fbee7ed` | `1e632894586b39137d89bbdc94b3dd78a439bc1fe15ed3a635a32abe9fbee7ed` | `PASS` |
| `csv/rule_evaluation.csv` | `8f4b0cb4953f405234ed8cfcfb0d42653b001a1a80bf177a0891ecc48aabb1fe` | `8f4b0cb4953f405234ed8cfcfb0d42653b001a1a80bf177a0891ecc48aabb1fe` | `PASS` |
| `csv/state_event.csv` | `65d2c9f04088ac4fdacbe9492d3f8b9d1e95258ff2914054efc316904b02a72c` | `65d2c9f04088ac4fdacbe9492d3f8b9d1e95258ff2914054efc316904b02a72c` | `PASS` |
| `csv/subscription.csv` | `5827c53514f86b1530e24c46621a7f5d63d9c7c72bd9675d2684a38ef044b5f9` | `5827c53514f86b1530e24c46621a7f5d63d9c7c72bd9675d2684a38ef044b5f9` | `PASS` |
| `csv/support_case.csv` | `2950fef5fd10e2daf0fd0b75b5a24a3f1c8698086819456ebc5af1049dbb0499` | `2950fef5fd10e2daf0fd0b75b5a24a3f1c8698086819456ebc5af1049dbb0499` | `PASS` |
| `csv/usage_snapshot.csv` | `66cab0c26503e1a93e1b32b3cecf47838e4c355095adfac438cca9220c97f3c6` | `66cab0c26503e1a93e1b32b3cecf47838e4c355095adfac438cca9220c97f3c6` | `PASS` |
| `evaluation_results.json` | `f30f37c655bb48cef85b0d3df4c04e48f18cf6fb4da88a4cf57f8ec1c7e2dcc7` | `f30f37c655bb48cef85b0d3df4c04e48f18cf6fb4da88a4cf57f8ec1c7e2dcc7` | `PASS` |
| `ground_truth/anomalies.csv` | `e0af4805ea16bcafe3e37b28022abc148d48af0847abbbc49f3b183a0c7c573b` | `e0af4805ea16bcafe3e37b28022abc148d48af0847abbbc49f3b183a0c7c573b` | `PASS` |
| `ground_truth/expected_decisions.csv` | `caa7bd892dd9ae5a8ef70448d545873fdbfa5ea664a41274d2ae8c28d72c52c5` | `caa7bd892dd9ae5a8ef70448d545873fdbfa5ea664a41274d2ae8c28d72c52c5` | `PASS` |
| `ground_truth/latent_customer_state.csv` | `925b484849b2948facee5fe60c5731bf6c3aadbbe3741e52c3997c0b6082ca1f` | `925b484849b2948facee5fe60c5731bf6c3aadbbe3741e52c3997c0b6082ca1f` | `PASS` |
| `json/billing_event.json` | `bccb00f9454f48537e6766f693671552fe6d6640ecbb0f7eade7afd47f3838d2` | `bccb00f9454f48537e6766f693671552fe6d6640ecbb0f7eade7afd47f3838d2` | `PASS` |
| `json/campaign_contact.json` | `49851a601ade249940b6478b94142a58b01e1c9ee90ec072eaea7460da7ea2fc` | `49851a601ade249940b6478b94142a58b01e1c9ee90ec072eaea7460da7ea2fc` | `PASS` |
| `json/churn_outcome.json` | `c333c951d2fdc1aabf4d77d3b8ccc9dd9df5cfead100c5234fbda4b0801b442e` | `c333c951d2fdc1aabf4d77d3b8ccc9dd9df5cfead100c5234fbda4b0801b442e` | `PASS` |
| `json/customer.json` | `011ebcb58b611744534510df5fec1aca08d60f1ec9c7134e9de970eb3c811b10` | `011ebcb58b611744534510df5fec1aca08d60f1ec9c7134e9de970eb3c811b10` | `PASS` |
| `json/eligibility_rule.json` | `b0725519662a056c22e99e99e0803248af683a8b383eb5b9ef4ece19e1766311` | `b0725519662a056c22e99e99e0803248af683a8b383eb5b9ef4ece19e1766311` | `PASS` |
| `json/feature_snapshot.json` | `d889ad7f48850d4db2e6e1951ccfc0e3e6a5d0a29792254170cc5c8469fc9d20` | `d889ad7f48850d4db2e6e1951ccfc0e3e6a5d0a29792254170cc5c8469fc9d20` | `PASS` |
| `json/offer.json` | `2d765808ded42bd09d3d738c4697638c2d32fe0bd8d2bbc953c9b212a4e6e10f` | `2d765808ded42bd09d3d738c4697638c2d32fe0bd8d2bbc953c9b212a4e6e10f` | `PASS` |
| `json/offer_eligibility_rule.json` | `5dc1cbad98c6ab5118966eb07e649e75a7052a9cdbe11d2c3499424e006caa7b` | `5dc1cbad98c6ab5118966eb07e649e75a7052a9cdbe11d2c3499424e006caa7b` | `PASS` |
| `json/retention_outcome.json` | `7d851899343435a88e7494944a95c24c67c911c132b221ebb6bb186ae6244294` | `7d851899343435a88e7494944a95c24c67c911c132b221ebb6bb186ae6244294` | `PASS` |
| `json/risk_score.json` | `c1844535b86fa68c1402d78ed3fae79d01e15f0fb1441ab4067e4ffba30f4450` | `c1844535b86fa68c1402d78ed3fae79d01e15f0fb1441ab4067e4ffba30f4450` | `PASS` |
| `json/rule_evaluation.json` | `afbc687ed6dbf2096f7dd3f949d48de2e5bf0a7c91bbd115dff600ef145dd41e` | `afbc687ed6dbf2096f7dd3f949d48de2e5bf0a7c91bbd115dff600ef145dd41e` | `PASS` |
| `json/state_event.json` | `86452a883d46b4521a3e50f6a4d0cdd88fa6e182fc98c0df4cb83845b63011dd` | `86452a883d46b4521a3e50f6a4d0cdd88fa6e182fc98c0df4cb83845b63011dd` | `PASS` |
| `json/subscription.json` | `3e5a09b71e975d64d4286962e3373c471ff478c8c777a2d3ed5517c942209e6c` | `3e5a09b71e975d64d4286962e3373c471ff478c8c777a2d3ed5517c942209e6c` | `PASS` |
| `json/support_case.json` | `70a743b13514f5738d99e8269324e441f38fafe3a5d141e7eb961fbbf3b4d00b` | `70a743b13514f5738d99e8269324e441f38fafe3a5d141e7eb961fbbf3b4d00b` | `PASS` |
| `json/usage_snapshot.json` | `a8bb542a7c2c4516c1d235373409a6c5b97a83599d74cb6e098d590ecbc3a9ea` | `a8bb542a7c2c4516c1d235373409a6c5b97a83599d74cb6e098d590ecbc3a9ea` | `PASS` |
| `model_info.json` | `f75be5ab926c563c1e518c88c37bd1ac0cee0dd16b9f82005a0314a61c965eea` | `f75be5ab926c563c1e518c88c37bd1ac0cee0dd16b9f82005a0314a61c965eea` | `PASS` |
| `sql/schema.sql` | `1025bbb340ba5823ab32a29d5438094a73c2a1fbfad9b96249afb1964ea3ea11` | `1025bbb340ba5823ab32a29d5438094a73c2a1fbfad9b96249afb1964ea3ea11` | `PASS` |
| `sql/seed.sql` | `2807e748872c4161598aa0b005d6909938b5c436f404917fd48744920007c615` | `2807e748872c4161598aa0b005d6909938b5c436f404917fd48744920007c615` | `PASS` |

Reproducibility Result: PASS
