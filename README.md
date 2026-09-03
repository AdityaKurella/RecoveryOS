# RecoveryOS V3 — Autonomous AI Revenue Recovery Platform

> **Track**: Razorpay AI Buildathon 2026 — Track 03 (AI Revenue Recovery)  
> **Status**: Complete, Verified & Tested (30/30 Automated Tests Passing)

RecoveryOS is an autonomous economic decisioning engine that transforms payment failure recovery from heuristic retries into a portfolio-optimized, value-maximizing system.

---

## 1. Problem & Core Solution

When subscription payments fail, merchants face a trilemma:
1. **Blind Retries**: Waste intervention costs (₹1–₹3 per attempt) and risk customer churn or card network penalties.
2. **Static Rules**: Ignore customer engagement, failure context, and individual payment economics.
3. **Unconstrained Actions**: Attempt high-cost dispatches on low-value payments, destroying net revenue.

RecoveryOS solves this by evaluating 6 candidate actions (`RETRY_NOW`, `WAIT_AND_RETRY`, `SEND_REMINDER`, `PAYMENT_LINK`, `UPDATE_PAYMENT_METHOD`, `STOP`) per failure, predicting ML recovery probabilities $\hat{P}$, subtracting intervention costs, and optimizing expected net recovery under portfolio capacity constraints.

$$\text{Expected Gross Recovery} = \text{Amount} \times \hat{P}(\text{Recovery})$$
$$\text{Expected Net Recovery} = \text{Expected Gross Recovery} - \text{Intervention Cost}$$

---

## 2. Key V3 Architectural Features

1. **Counterfactual Value Engine**: Evaluates expected net recovery across all 6 candidate actions per failure.
2. **Genuinely Selectable `STOP` Option**: For low-value or low-probability payments where intervention costs exceed gross recovery, `STOP` ($\text{cost}=0$, $\text{gross}=0$, $\text{net}=0$) ranks #1 to prevent loss.
3. **Portfolio Optimizer under Capacity $K$**: Constrains active interventions to capacity $K$ (e.g., top 100 cases), reducing intervention costs by 81.4%.
4. **Durable SQLite Persistence Store** (`simulator/persistence.py`): Survives process crashes and restarts, guaranteeing idempotent event handling.
5. **Bounded Autonomy & Safety Policy Engine**: High-value payments ($\ge ₹10,000$) with low confidence ($< 0.70$) escalate to manual review (`HUMAN`).
6. **Pluggable Execution Adapters**: Supports `SimulationExecutionAdapter` and `RazorpayTestModeAdapter`.
7. **Strict Data Isolation**: Ground-truth recovery probabilities and future outcomes are 100% excluded from inference feature pipelines.

---

## 3. Benchmark Summary (559 Test Cases)

| Strategy | Revenue at Risk (₹) | Expected Gross (₹) | Intervention Cost (₹) | Expected NET Recovery (₹) | Recovery Rate % | Action Match vs Oracle |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **RecoveryOS V2/V3 Engine** | ₹1,090,563.78 | ₹843,404.27 | ₹1,354.00 | **₹842,050.27** | **77.34%** | **53.85%** |
| **Failure-Aware Rules** | ₹1,090,563.78 | ₹844,158.90 | ₹1,287.00 | **₹842,871.90** | 77.41% | N/A |
| **Oracle Ceiling** | ₹1,090,563.78 | ₹856,711.57 | ₹1,382.00 | **₹855,329.57** | 78.56% | 100.00% |

---

## 4. Setup & Running Instructions

### Run All Automated Tests (30 Tests)
```powershell
python -m unittest discover tests
```

### Run Deterministic End-to-End Demo (5 Scenarios)
```powershell
python simulator/demo_runner.py
```

### Run Benchmark Evaluation
```powershell
$env:PYTHONIOENCODING="utf-8"
python simulator/v2_evaluation.py
python simulator/multi_seed_evaluation.py
```

### Start FastAPI Backend Service
```powershell
python -m uvicorn api.main:app --reload --port 8000
```

---

## 5. Synthetic Data & Architectural Disclaimers

- **Synthetic Simulation**: Evaluated revenue figures represent simulated net recovery in a controlled synthetic environment.
- **No Real Money Dispatched**: Automated executions use `SimulationExecutionAdapter` or `RazorpayTestModeAdapter`.
- **No LLMs Used for Decisioning**: Recovery probabilities and decisions are computed strictly from ML inference and vector economic formulas.
