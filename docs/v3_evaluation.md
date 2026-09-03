# RecoveryOS V3 — Evaluation & Experimental Benchmark Report

> **Objective**: Present empirical evaluation results comparing V1 Baseline, V2 Engine, V3 ML Experiments, Failure-Aware Rules, and Oracle Ceiling across 559 held-out test cases.

---

## 1. Summary Benchmark Matrix (559 Test Cases)

| Model Architecture | Cases Evaluated | Revenue at Risk (₹) | Expected Gross (₹) | Cost (₹) | Expected NET (₹) | Recovery Rate % | Oracle Match % |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **V1 Baseline** | 559 | ₹1,090,563.78 | ₹843,404.27 | ₹1,354.00 | **₹842,050.27** | 77.34% | 53.85% |
| **V2 Engine (ExtraTrees Control)** | 559 | ₹1,090,563.78 | ₹843,404.27 | ₹1,354.00 | **₹842,050.27** | **77.34%** | **53.85%** |
| **V3 Action-Specific Estimators** | 559 | ₹1,090,563.78 | ₹830,204.04 | ₹1,347.00 | **₹828,857.04** | 76.13% | 35.06% |
| **V3 Calibrated ExtraTrees** | 559 | ₹1,090,563.78 | ₹827,318.29 | ₹1,336.00 | **₹825,982.29** | 75.86% | 33.81% |
| **Failure-Aware Rules** | 559 | ₹1,090,563.78 | ₹844,158.90 | ₹1,287.00 | **₹842,871.90** | 77.41% | N/A |
| **Oracle Ceiling** | 559 | ₹1,090,563.78 | ₹856,711.57 | ₹1,382.00 | **₹855,329.57** | 78.56% | 100.00% |

---

## 2. Scientific Evaluation Findings

1. **V2 Control Baseline Superiority**: The V2 ExtraTrees Classifier remains the top-performing machine learning model, achieving **₹842,050.27** expected net recovery (77.34% recovery rate) and **53.85% Oracle action match**.
2. **Rejection of Action-Specific Model Split**: Splitting training data across 5 distinct action sub-models reduced sample size per model from 13,975 to 2,795 rows, increasing prediction variance and reducing net recovery to ₹828,857.04.
3. **Rejection of Sigmoid Probability Calibration**: Probability calibration smoothing reduced net recovery to ₹825,982.29.
4. **Final Model Promotion Verdict**: Per strict scientific acceptance criteria, **V2 ExtraTrees baseline is retained as the production ML predictor**, while V3 engineering upgrades (SQLite persistence, execution adapters, and safety guardrails) are promoted into V3.
