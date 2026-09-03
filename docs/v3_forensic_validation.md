# RecoveryOS V3 — Forensic Research & Evaluation Validation Report

> **Document Purpose**: Authoritative forensic validation of RecoveryOS V3 research results, metric semantics, experimental model benchmarks, and structural baseline findings.

---

## 1. Discrepancy Resolution: Ground-Truth vs Model-Estimated Expected Net

### The Discrepancy
- **V2 Benchmark Expected Net**: **₹842,050.27**
- **V2 Model-Predicted Expected Net**: **₹823,787.59**

### Root Cause & Mathematical Distinction
1. **Ground-Truth Expected NET Recovery (₹842,050.27)**:
   $$\text{Expected Net}_{\text{GT}} = \sum_{i=1}^{N} \left( \text{Amount}_i \times P_{\text{true}}(Y=1 \mid X_i, a_i^*) - \text{Cost}(a_i^*) \right)$$
   This measures the actual economic recovery achieved when the model's chosen policy $a_i^*$ is evaluated against the counterfactual environment probabilities $P_{\text{true}}$.

2. **Model-Estimated Expected NET Recovery (₹823,787.59)**:
   $$\text{Expected Net}_{\text{Model}} = \sum_{i=1}^{N} \left( \text{Amount}_i \times \hat{P}_{\text{model}}(Y=1 \mid X_i, a_i^*) - \text{Cost}(a_i^*) \right)$$
   This measures what the machine learning model *believes* it will recover based on its internal probability predictions $\hat{P}_{\text{model}}$.

Both metrics are mathematically valid and now explicitly separated in all V3 evaluation scripts and documentation.

---

## 2. Experimental Model Benchmark Findings

| Model Variant | Expected Net (₹) | Oracle Action Match % | Result / Verdict |
| :--- | :---: | :---: | :--- |
| **V2 Control (ExtraTrees Baseline)** | **₹842,050.27** | **53.85%** | **PROMOTED AS PRODUCTION ML MODEL** |
| **V3 Action-Specific Model Bundle** | ₹828,857.04 | 35.06% | **REJECTED** (Sample splitting reduced training size per action from 13,975 to 2,795 rows, increasing variance). |
| **V3 Sigmoid Calibrated ExtraTrees** | ₹825,982.29 | 33.81% | **REJECTED** (Probability calibration smoothed tail predictions, degrading net value ranking). |

---

## 3. Structural Rules Baseline Bias Finding

- **Failure-Aware Rules Expected Net**: **₹842,871.90** (+₹821.62 over ML policy).
- **Finding**: The synthetic counterfactual generator (`m03_generate_counterfactual_dataset.py`) was constructed using heuristic rules (e.g. `CARD_EXPIRED` $\rightarrow$ update method probability 0.85). Consequently, the static Rules baseline possesses a structural advantage on this synthetic dataset.

---

## 4. Final Recommendation Decision

**CONCLUSION B**: **V3 engineering upgrades (SQLite persistence, execution adapters, safety guardrails, and ablation tools) are fully validated and promoted. The V2 ExtraTrees Classifier is retained as the production ML model.**

- **V3 Engineering Release Status**: **FREEZE & STABILIZE**.
- **Further Synthetic ML Tuning**: **HALT**. Further tuning against this synthetic generator adds risk of overfitting without real-world utility.
