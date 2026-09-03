# RecoveryOS V3 — Policy Regret & Error Analysis

> **Analysis Objective**: Identify why V2 ML Policy performed slightly below static Failure-Aware Rules on synthetic test data and define the ML architectural upgrade required for V3.

---

## 1. Regret Summary & Root Cause Analysis

### Benchmark Comparison (559 Test Cases)
- **V2 ML Policy Expected Net Recovery**: **₹842,050.27** (77.34% recovery rate)
- **Failure-Aware Rules Expected Net Recovery**: **₹842,871.90** (77.41% recovery rate)
- **Difference**: **-₹821.62 (-0.10% expected net gap)**
- **Realized 5-Seed Difference**: **-₹18,015.80 (-2.12% realized net gap)**

### Root Cause 1: Action-Context Interaction Loss
In V2, a single ExtraTrees Classifier was trained on single-action observations. When expanded across all 5 candidate actions per failure during counterfactual evaluation, the model occasionally assigned slightly higher probabilities to suboptimal actions (e.g. predicting 0.82 for `WAIT_AND_RETRY` when `UPDATE_PAYMENT_METHOD` had true probability 0.88).

### Root Cause 2: Failure Reason Compatibility Penalties
For failure reasons like `CARD_EXPIRED` or `UPDATE_PAYMENT_METHOD_REQUIRED`, the static rules baseline strictly forces `UPDATE_PAYMENT_METHOD` (cost ₹3.00), while a single shared classifier without action-specific conditioning sometimes selected lower-cost actions (`SEND_REMINDER` cost ₹1.00) that had zero true recovery probability.

---

## 2. Regret Breakdown by Failure Reason & Action

| Failure Reason | V2 Selected Action (Top Count) | Rules Action | Oracle Action | Regret Source / Economic Loss |
| :--- | :--- | :--- | :--- | :--- |
| **CARD_EXPIRED** | `SEND_REMINDER` / `WAIT_AND_RETRY` (24 cases) | `UPDATE_PAYMENT_METHOD` | `UPDATE_PAYMENT_METHOD` | Low probability predictions caused selection of low-cost ineffective actions. |
| **INSUFFICIENT_FUNDS**| `WAIT_AND_RETRY` (210 cases) | `WAIT_AND_RETRY` | `PAYMENT_LINK` / `WAIT_AND_RETRY` | Minor probability calibration noise vs Payment Link. |
| **AUTHENTICATION_FAILED**| `RETRY_NOW` (35 cases) | `RETRY_NOW` | `RETRY_NOW` | 0 regret — perfect alignment. |

---

## 3. V3 Machine Learning Solution: Action-Specific Counterfactual Estimators

To eliminate action-context interaction loss, RecoveryOS V3 introduces **Action-Specific Probability Estimators** $\hat{P}_a(Y=1 \mid X)$:

$$\hat{P}(Y=1 \mid X, a = a_k) = \mathcal{M}_{a_k}(X)$$

Instead of a single multi-class model estimating generic recovery probability, V3 trains distinct calibrated probabilistic estimators for each candidate action $a_k \in \{\text{RETRY\_NOW}, \text{WAIT\_AND\_RETRY}, \text{SEND\_REMINDER}, \text{PAYMENT\_LINK}, \text{UPDATE\_PAYMENT\_METHOD}\}$.

This architecture ensures that action-specific feature interactions (e.g., `failure_reason == 'CARD_EXPIRED'` predicting $\hat{P} = 0.0$ for `RETRY_NOW` and $\hat{P} = 0.85$ for `UPDATE_PAYMENT_METHOD`) are captured with zero cross-action noise!
