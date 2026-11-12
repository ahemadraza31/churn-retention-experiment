"""Planned offer selection and stratified randomized assignment (ADR-007)."""

import math
from typing import Mapping
import pandas as pd

from churnexp import ids
from churnexp.config import Config
from churnexp.rng import RngFactory

CAMPAIGN_CONTACT_COLUMNS: list[str] = [
    "contact_id",
    "customer_id",
    "offer_id",
    "experiment_group",
    "contact_status",
    "assigned_at",
    "sent_at",
    "stratum",
    "responded",
    "redeemed",
]


def assign_campaign(
    eligible_offers_by_cid: Mapping[str, list[str]],
    risk_scores: pd.DataFrame,
    cfg: Config,
    rng_factory: RngFactory | None = None,
) -> pd.DataFrame:
    """Assign planned offer and 50/50 stratified TREATMENT/CONTROL arm to eligible customers.

    - Planned offer: uniform random choice from passing ER-007 offers via
      `entity_stream("planned_offer", customer_index)`.
    - Stratum: `risk_band` (`HIGH` or `MEDIUM`).
    - Stratified randomization: within each stratum, shuffle sorted eligible customers using
      `stream("assignment")`, assign first `ceil(n / 2)` to `TREATMENT` and the rest to `CONTROL`.
    - Delivery: for `TREATMENT`, draw from `entity_stream("delivery", customer_index)`;
      if `< delivery_failure_prob`, `contact_status = 'DELIVERY_FAILED'`, else `'SENT'`,
      both with `sent_at = f"{assignment_date}T{contact_hour:02d}:00:00"`.
    - For `CONTROL`, `contact_status = 'WITHHELD'`, `sent_at = None`, retaining `offer_id`.
    """
    if not eligible_offers_by_cid:
        return pd.DataFrame(columns=CAMPAIGN_CONTACT_COLUMNS)

    if rng_factory is None:
        rng_factory = RngFactory(cfg.seed)

    camp_cfg = cfg.campaign
    assign_dt_str = camp_cfg.assignment_date.isoformat()
    cycle_year = camp_cfg.assignment_date.year
    assigned_at_str = f"{assign_dt_str}T08:00:00"
    sent_at_treatment = f"{assign_dt_str}T{int(camp_cfg.contact_hour):02d}:00:00"
    fail_prob = float(camp_cfg.delivery_failure_prob)

    band_by_cid = {
        str(row.customer_id): str(row.band)
        for row in risk_scores.itertuples(index=False)
    }

    planned_offer_by_cid: dict[str, str] = {}
    cids_by_stratum: dict[str, list[str]] = {}

    for cid in sorted(eligible_offers_by_cid.keys()):
        passing = sorted(eligible_offers_by_cid[cid])
        if not passing:
            continue
        c_idx = ids.parse_customer_id(cid)
        rng_offer = rng_factory.entity_stream("planned_offer", c_idx)
        choice_idx = int(rng_offer.integers(0, len(passing)))
        planned_offer_by_cid[cid] = str(passing[choice_idx])

        stratum = band_by_cid[cid]
        cids_by_stratum.setdefault(stratum, []).append(cid)

    # Seeded shuffle per stratum using stream("assignment")
    rng_assign = rng_factory.stream("assignment")
    group_by_cid: dict[str, str] = {}

    # Process strata in fixed deterministic order: HIGH, MEDIUM, then any others alphabetically
    ordered_strata = [s for s in ("HIGH", "MEDIUM") if s in cids_by_stratum] + [
        s for s in sorted(cids_by_stratum.keys()) if s not in ("HIGH", "MEDIUM")
    ]

    for stratum in ordered_strata:
        s_cids = sorted(cids_by_stratum[stratum])
        n_s = len(s_cids)
        perm = rng_assign.permutation(n_s)
        shuffled = [s_cids[int(i)] for i in perm]
        n_treat = math.ceil(n_s / 2.0)
        for pos, cid in enumerate(shuffled):
            group_by_cid[cid] = "TREATMENT" if pos < n_treat else "CONTROL"

    rows = []
    for cid in sorted(planned_offer_by_cid.keys()):
        c_idx = ids.parse_customer_id(cid)
        contact_id = ids.campaign_contact_id(cid, cycle_year, 1)
        planned_oid = planned_offer_by_cid[cid]
        exp_group = group_by_cid[cid]
        stratum = band_by_cid[cid]

        if exp_group == "TREATMENT":
            rng_deliv = rng_factory.entity_stream("delivery", c_idx)
            u_deliv = float(rng_deliv.random())
            status = "DELIVERY_FAILED" if u_deliv < fail_prob else "SENT"
            sent_at: str | None = sent_at_treatment
        else:
            status = "WITHHELD"
            sent_at = None

        rows.append(
            {
                "contact_id": contact_id,
                "customer_id": cid,
                "offer_id": planned_oid,
                "experiment_group": exp_group,
                "contact_status": status,
                "assigned_at": assigned_at_str,
                "sent_at": sent_at,
                "stratum": stratum,
                "responded": 0,
                "redeemed": 0,
            }
        )

    df = pd.DataFrame(rows, columns=CAMPAIGN_CONTACT_COLUMNS)
    return df.sort_values("contact_id", kind="mergesort").reset_index(drop=True)

