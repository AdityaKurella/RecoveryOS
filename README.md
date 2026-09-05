# RecoveryOS V3.1 — AI Revenue Recovery Decision Platform

> **Track**: Razorpay AI Buildathon 2026 — Track 03 (AI Revenue Recovery)  
> **Status**: Complete, Hardened & Submission-Ready (38/38 Automated Tests Passing)

RecoveryOS is an AI-powered economic decisioning engine that transforms payment failure recovery from blind retries into a portfolio-optimized, value-maximizing system.

---

## 1. Why RecoveryOS is Different

> **Core Philosophy**: *RecoveryOS optimizes recovery effort, not merely recovery probability.*

Standard recovery systems focus strictly on predicting whether a payment can be recovered. RecoveryOS goes further by weighing predicted recovery against intervention costs, customer friction, and budget capacity. By evaluating expected net value across all candidate actions—including a zero-cost `STOP` option—RecoveryOS prevents merchants from destroying value on unrecoverable or low-margin payments.

---

## 2. Problem & Solution Overview

When subscription payments fail, merchants face a trilemma:
1. **Blind Retries**: Waste intervention costs (₹1–₹3 per attempt) and risk customer churn or card network penalties.
2. **Static Heuristic Rules**: Ignore customer engagement, failure context, and individual payment economics.
3. **Unconstrained Actions**: Attempt high-cost dispatches on low-value payments, destroying net revenue.

RecoveryOS solves this by evaluating 6 candidate actions (`RETRY_NOW`, `WAIT_AND_RETRY`, `SEND_REMINDER`, `PAYMENT_LINK`, `UPDATE_PAYMENT_METHOD`, `STOP`) per failure, predicting ML recovery probabilities $\hat{P}$, subtracting intervention costs, and optimizing expected net recovery under portfolio capacity constraints.

$$\text{Expected Gross Recovery} = \text{Amount} \times \hat{P}(\text{Recovery})$$
$$\text{Expected Net Recovery} = \text{Expected Gross Recovery} - \text{Intervention Cost}$$

---

## 3. Platform Evolution (V1 → V2 → V3)

- **V1 Baseline**: Foundation heuristic retry policy and early portfolio selection.
- **V2 Platform**: Introduced the ExtraTrees decision engine, economic value modeling, portfolio optimization, bounded safety policy engine, and event-driven runtime safeguards.
- **V3 Research & Hardening**: Introduced durable SQLite persistence, pluggable execution adapters, the ₹35 Uncertainty-Aware Hybrid Policy, forensic policy-regret analysis, and 5-seed multi-seed evaluation.

---

## 4. Complete V3 System Architecture

```
[Payment Failure Event: payment.failed]
                  │
                  ▼
   [Validation & Idempotency Check] ──(Duplicate Event)──> [Cached Response]
                  │
                  ▼
    [Context & Feature Builder]
                  │
                  ▼
  [ExtraTrees Recovery Probability Model]
                  │
                  ▼
  [Counterfactual Economic Value Engine] ──(Scores 6 Actions: 5 Active + STOP)
                  │
                  ▼
      [Portfolio Optimizer] ──────────────(Constrains by Capacity K & Budget B)
                  │
                  ▼
 [₹35 Uncertainty-Aware Policy Engine] ──(Margin < ₹35 Fallback to Rules)
                  │
                  ▼
     [Safety & Policy Guardrails] ────────(Assigns ALLOW, HUMAN, STOP)
                  │
     ┌────────────┼────────────┐
     │            │            │
  [ALLOW]      [HUMAN]      [STOP]
     │            │            │
     ▼            ▼            ▼
[Execution     [Review     [Zero Action
 Adapter]       Queue]       Logged]
     │
     ▼
[Durable SQLite State Store]
     │
     ▼
[Cryptographically Identified Audit Lineage]
```

---

## 5. Benchmark Summary (559 Held-Out Synthetic Test Cases)

> **Note on Benchmark Metrics**: The ₹842,866.91 figure represents **ground-truth expected net recovery on 559 held-out synthetic cases** under counterfactual evaluation, and is **NOT observed production revenue**.

| Strategy / Model | Revenue at Risk (₹) | Expected Gross (₹) | Intervention Cost (₹) | Expected NET Recovery (₹) | Recovery Rate % | Oracle Match % |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **V1 Baseline** | ₹1,090,563.78 | ₹843,404.27 | ₹1,354.00 | **₹842,050.27** | 77.34% | 53.85% |
| **V2 Control Engine** | ₹1,090,563.78 | ₹843,404.27 | ₹1,354.00 | **₹842,050.27** | 77.34% | 53.85% |
| **V3 Promoted Hybrid Policy (Threshold ₹35)** | ₹1,090,563.78 | ₹844,202.91 | ₹1,336.00 | **₹842,866.91** | **77.41%** | **55.81%** |
| **Failure-Aware Rules Baseline** | ₹1,090,563.78 | ₹844,158.90 | ₹1,287.00 | **₹842,871.90** | 77.41% | N/A |
| **Oracle Upper Bound** | ₹1,090,563.78 | ₹856,711.57 | ₹1,382.00 | **₹855,329.57** | 78.56% | 100.00% |

> **Key Result**: The V3 Promoted Hybrid Policy achieves **+₹816.63 higher expected net recovery** over V2 Control. On this synthetic benchmark, the V3 hybrid policy is **approximately at parity with the deterministic Failure-Aware Rules baseline** (within ₹4.99 of the baseline).

---

## 6. Key Architectural Capabilities

1. **Counterfactual Economic Decision Engine**: Evaluates expected net recovery across all 6 candidate actions per failure.
2. **Genuinely Selectable `STOP` Option**: For low-value or low-probability payments where intervention costs exceed gross recovery, `STOP` ($\text{cost}=0$, $\text{gross}=0$, $\text{net}=0$) ranks #1 to prevent loss.
3. **Portfolio Optimizer under Capacity $K$**: Constrains active interventions to capacity K (e.g., top 100 cases). In the evaluated top-100 portfolio experiment, the optimizer captured 68.5% of total model net recovery while incurring 18.6% of total intervention cost—an 81.4% reduction relative to executing across the full candidate set.
4. **₹35 Uncertainty-Aware Fallback Policy**: When the economic margin between the top ML action and the second-best action is $< \text{₹35}$, the system defaults to domain heuristic rules to prevent low-confidence errors.
5. **Bounded Autonomy & Policy Guardrails**: Eligible low-risk actions may be executed automatically (`ALLOW`), while policy-sensitive or high-value cases with low confidence escalate to manual review (`HUMAN`) or zero-action (`STOP`).
6. **Durable SQLite Persistence Store** (`simulator/persistence.py`): Process-restart resilient storage (`data/recoveryos_v3_state.db`) for idempotency deduplication.
7. **Pluggable Execution Adapters**: Supports `SimulationExecutionAdapter` and `RazorpayTestModeAdapter`.
8. **Strict Data Isolation**: Ground-truth recovery probabilities and future outcomes are 100% excluded from inference feature pipelines.

---

## 7. Setup & Running Instructions

### Run All Automated Tests (38 Tests)
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
python simulator/v3_evaluation.py
python simulator/multi_seed_evaluation.py
```

### Start FastAPI Backend Service
```powershell
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

### Start React Frontend Console
```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

---

## 8. Technical Limitations & Disclaimers

- **Synthetic Counterfactual Benchmark**: Evaluated revenue numbers represent ground-truth expected net recovery on a 559 held-out synthetic test dataset under counterfactual evaluation, and are not observed production revenue.
- **No Real Money Dispatched**: Automated executions are dispatched via `SimulationExecutionAdapter` or `RazorpayTestModeAdapter`. Live Razorpay API credentials are not tracked.
- **Local SQLite Persistence**: Persistence uses a local SQLite database for process restart resilience rather than a distributed cloud cluster.
