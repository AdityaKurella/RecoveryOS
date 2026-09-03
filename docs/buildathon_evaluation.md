# Razorpay AI Buildathon 2026 — Track 03 Evaluation

> **Project**: RecoveryOS V2 — Counterfactual AI Revenue Recovery Engine  
> **Track**: Track 03 — AI Revenue Recovery  
> **System Status**: Complete, Verified & Tested (22/22 Automated Tests Passed)

---

## 1. Executive Summary & Assessment

RecoveryOS V2 is an autonomous economic decisioning engine that transforms payment recovery from heuristic retries into a portfolio-optimized, value-maximizing system.

### Core Problem Solved
When subscription payments fail, merchants face a trilemma:
1. **Blind Retries**: Waste intervention costs (₹1–₹3 per attempt) and risk customer churn or card network penalties.
2. **Static Rules**: Ignore customer engagement, failure context, and individual payment economics.
3. **Unconstrained Actions**: Attempt high-cost dispatches on low-value payments, destroying net revenue.

RecoveryOS V2 solves this by evaluating 6 candidate actions (`RETRY_NOW`, `WAIT_AND_RETRY`, `SEND_REMINDER`, `PAYMENT_LINK`, `UPDATE_PAYMENT_METHOD`, `STOP`) per failure, predicting machine learning recovery probabilities $\hat{P}$, subtracting intervention costs, and optimizing expected net recovery under portfolio capacity constraints.

---

## 2. Evaluation Against Razorpay Track 03 Criteria

| Criterion | Implementation in RecoveryOS V2 | Verification Evidence |
| :--- | :--- | :--- |
| **1. Revenue at Risk Detection** | Automatically ingests `payment.failed` events and quantifies total revenue at risk (₹1,090,563.78 across 559 test failures). | Measured in `simulator/v2_counterfactual_policy.py` & API `/api/v2/portfolio`. |
| **2. Counterfactual Intervention Selection** | Evaluates expected net value across all 6 candidate actions per failure. Selects action maximizing expected net recovery. | Implemented in `simulator/value_engine.py`. Unit tested in `tests/test_value_engine.py`. |
| **3. Portfolio-Level Optimization** | Constrains active recovery dispatches to capacity $K$ (e.g. top 100 cases), falling back to `STOP` when capacity is exceeded. | Implemented in `simulator/portfolio_optimizer.py`. Tested in `tests/test_portfolio.py`. |
| **4. Bounded Autonomy & Safety** | Enforces deterministic policy guardrails: minimum net value (₹50), high-value confidence controls (escalates $\ge ₹10,000$ to `HUMAN`), and retry limits. | Implemented in `simulator/event_runtime.py`. |
| **5. Idempotency & Event Safety** | Prevents duplicate event dispatches (`REJECTED_DUPLICATE_EVENT`), duplicate executions, and already-recovered retries (`REJECTED_ALREADY_RECOVERED`). | Verified in `tests/test_event_runtime.py` & `simulator/demo_runner.py`. |
| **6. Auditability & Lineage** | Generates unique deterministic tracking IDs (`event_id`, `decision_id`, `execution_id`, `outcome_id`) recording full context lineage. | Exposed via API `/api/v2/audit`. |
| **7. Multi-Seed Rigor** | Benchmarked across 5 independent random seeds (42, 101, 202, 303, 404), providing distribution metrics (mean, std, min, max). | Implemented in `simulator/multi_seed_evaluation.py`. |

---

## 3. Benchmark Summary (559 Test Cases)

| Strategy | Revenue at Risk (₹) | Expected Gross (₹) | Intervention Cost (₹) | Expected NET Recovery (₹) | Recovery Rate % | Action Match vs Oracle |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **RecoveryOS V2** | ₹1,090,563.78 | ₹843,404.27 | ₹1,354.00 | **₹842,050.27** | **77.34%** | **53.85%** |
| **Failure-Aware Rules** | ₹1,090,563.78 | ₹844,158.90 | ₹1,287.00 | **₹842,871.90** | 77.41% | N/A |
| **Oracle Ceiling** | ₹1,090,563.78 | ₹856,711.57 | ₹1,382.00 | **₹855,329.57** | 78.56% | 100.00% |

---

## 4. Commands to Run & Verify

- **Run All Automated Tests (22 Tests)**:
  ```powershell
  python -m unittest discover tests
  ```
- **Run Deterministic End-to-End Demo (5 Scenarios)**:
  ```powershell
  python simulator/demo_runner.py
  ```
- **Run 5-Seed Multi-Seed Evaluation**:
  ```powershell
  python simulator/multi_seed_evaluation.py
  ```
- **Start FastAPI Service**:
  ```powershell
  python -m uvicorn api.main:app --reload --port 8000
  ```
