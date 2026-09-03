# RecoveryOS V3 — Day 1 Policy Regret Deep Dive Report

> **Objective**: Conduct an exhaustive offline forensic research analysis into why the RecoveryOS ML policy achieves ₹842,050.27 expected net recovery compared to Failure-Aware Rules (₹842,871.90) and Oracle Ceiling (₹855,329.57).

---

## 1. Executive Summary & Core Metrics

Across 559 held-out test cases, the economic breakdown is:

- **Total Oracle Expected NET Recovery**: **₹855,329.57** (100.0% ceiling)
- **Total Rules Expected NET Recovery**: **₹842,871.90** (-₹12,457.67 gap vs Oracle)
- **Total RecoveryOS ML Expected NET Recovery**: **₹842,050.27** (-₹13,279.29 gap vs Oracle)
- **RecoveryOS vs Rules Gap**: **-₹821.62** (-0.10% difference)
- **Oracle Action Match Rate**: **53.85%** (301 / 559 cases)
- **Rules Action Match Rate**: **79.07%** (442 / 559 cases)

---

## 2. Action Disagreement Matrix (RecoveryOS vs Oracle)

```
Oracle Action          RETRY_NOW  WAIT_AND_RETRY  SEND_REMINDER  PAYMENT_LINK  UPDATE_PAYMENT_METHOD  STOP
RecoveryOS ML Action                                                                                                 
RETRY_NOW                     31              12              2             1                      1     0
WAIT_AND_RETRY                20             114             23            74                     23     0
SEND_REMINDER                  1               2              1             6                      1     0
PAYMENT_LINK                   4              31             11            53                     24     0
UPDATE_PAYMENT_METHOD          0               0              3            19                    102     0
STOP                           0               0              0             0                      0     0
```

---

## 3. Concentration & Regret Distribution

- **Top 10 Regret Cases**: Account for **₹2,725.21** (**20.5%** of total Oracle gap).
- **Top 25 Regret Cases**: Account for **₹5,182.28** (**39.0%** of total Oracle gap).
- **Top 50 Regret Cases**: Account for **₹7,855.32** (**59.2%** of total Oracle gap).
- **Top 100 Regret Cases**: Account for **₹10,958.32** (**82.5%** of total Oracle gap).

---

## 4. Regret Breakdown by Failure Reason & Amount

### Regret by Failure Reason
1. **`BANK_DECLINED`**: **₹5,539.01 total regret** (**41.7% of total gap**, 145 cases). Primary mistake: selecting `WAIT_AND_RETRY` instead of `PAYMENT_LINK`.
2. **`INSUFFICIENT_FUNDS`**: **₹5,494.58 total regret** (**41.4% of total gap**, 183 cases). Primary mistake: selecting `WAIT_AND_RETRY` when `PAYMENT_LINK` had higher recovery probability.
3. **`NETWORK_ERROR`**: ₹1,046.75 total regret (7.9% of gap, 62 cases).
4. **`LIMIT_EXCEEDED`**: ₹621.41 total regret (4.7% of gap, 50 cases).
5. **`AUTHENTICATION_FAILED`**: ₹350.86 total regret (2.6% of gap, 54 cases).
6. **`CARD_EXPIRED`**: ₹226.69 total regret (1.7% of gap, 65 cases).

### Regret by Amount Bucket
- **₹1,000–₹5,000 Bucket**: **₹7,868.38 total regret** (**59.3% of gap**, 172 cases).
- **< ₹1,000 Bucket**: **₹4,059.67 total regret** (**30.6% of gap**, 330 cases).
- **₹5,000–₹10,000 Bucket**: ₹485.86 total regret (3.7% of gap, 23 cases).
- **₹10,000+ Bucket**: ₹865.39 total regret (6.5% of gap, 34 cases).

---

## 5. ML vs Rules Disagreement Analysis

- Total Disagreement Cases: **117 cases** (20.9% of population).
- Cases where ML beats Rules: **45 cases** (gained **+₹3,043.70** expected net).
- Cases where Rules beats ML: **65 cases** (lost **-₹3,865.32** expected net).
- Net difference: **-₹821.62**.

---

## 6. Model Margin & Uncertainty Analysis

- **Q1 Low Margin (Uncertain, margin < ₹35.00)**: 140 cases, total regret = **₹4,142.26**, Oracle match = **42.1%**.
- **Q4 High Margin (Confident, margin > ₹300.00)**: 139 cases, total regret = **₹3,306.95**, Oracle match = **59.0%**.

---

## 7. Ranked Candidate Improvements (Day 2 / Day 3 Roadmap)

### Rank #1: Failure-Reason Interaction Feature Engineering
- **Expected Benefit**: Reclaims ~₹5,000–₹7,000 of the Oracle gap by eliminating `BANK_DECLINED` / `INSUFFICIENT_FUNDS` cross-action confusion between `WAIT_AND_RETRY` and `PAYMENT_LINK`.
- **Implementation Complexity**: Low (Add explicit interaction terms `failure_reason * amount`, `failure_reason * candidate_action`).
- **Risk**: Very Low.
- **Data Requirements**: Uses existing observable features.
- **Leakage Risk**: ZERO (No ground-truth fields used).
- **Expected Impact on Net**: +₹3,000 to +₹6,000.

### Rank #2: Uncertainty-Aware Rules Fallback Policy (Hybrid Policy)
- **Expected Benefit**: For low-margin cases ($Q1$, margin < ₹35.00) where ML is uncertain, default to `failure_aware_rules`.
- **Implementation Complexity**: Low (Simple threshold check in `v2_counterfactual_policy.py`).
- **Risk**: Low.
- **Data Requirements**: Uses model predicted probability margins.
- **Leakage Risk**: ZERO.
- **Expected Impact on Net**: +₹821.62 to +₹1,500.

### Rank #3: Class-Balanced Sample Weighting
- **Expected Benefit**: Improves probability estimation accuracy on underrepresented failure reasons.
- **Implementation Complexity**: Medium.
- **Risk**: Low.
- **Data Requirements**: Training dataset sample weights.
- **Leakage Risk**: ZERO.
- **Expected Impact on Net**: +₹500 to +₹1,200.
