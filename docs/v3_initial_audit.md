# RecoveryOS V3 — Forensic Audit & Architectural Blueprint

> **Branch**: `v3-dev`  
> **Control Group Baseline**: V2 Commit `3ff7976` (`test: harden V2 runtime and API safeguards`)  
> **Target**: Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery

---

## 1. Audit of Current V2 Baseline Strengths & Weaknesses

### Strengths of RecoveryOS V2
1. **Counterfactual Economic Value Engine**: Scores 6 candidate actions (`RETRY_NOW`, `WAIT_AND_RETRY`, `SEND_REMINDER`, `PAYMENT_LINK`, `UPDATE_PAYMENT_METHOD`, `STOP`) per failure.
2. **Deterministic Safety Guardrails**: Enforces bounded autonomy boundaries (`ALLOW`, `HUMAN`, `STOP`). High-value payments ($\ge ₹10,000$) with low confidence ($< 0.70$) escalate to `HUMAN`.
3. **Data Leakage Prevention**: Ground-truth probabilities and future recovery outcomes are strictly prohibited from inference feature pipelines.
4. **Comprehensive Test Coverage**: 25/25 automated unit/API tests passing cleanly in 0.60 seconds.
5. **Clean Local Repository**: GitHub-safe compressed model file (`counterfactual_model.pkl.gz` 54.42 MB).

### Known Weaknesses of RecoveryOS V2
1. **ML Policy vs Rules Deficit**: On synthetic test evaluation, static failure-aware rules slightly outperform the ExtraTrees ML policy on realized simulated net recovery (-2.12% gap). This occurs because the ExtraTrees model predicts overall recovery probability without explicitly learning treatment effects (uplift) per action.
2. **In-Memory Idempotency & Audit Trail**: Event deduplication and audit lineage logs are stored in in-memory Python dictionaries and vanish if the process restarts.
3. **Monolithic Model Predictor**: V2 uses a single multi-class model predicting recovery probability rather than action-specific counterfactual probability estimators $\hat{P}(Y=1 \mid X, a)$.
4. **Greedy Portfolio Optimization**: While optimal for unweighted unit capacity $K$, greedy priority sorting does not guarantee exact 0/1 Knapsack global optimality under continuous monetary budget constraints $B$.

---

## 2. Solvable V3 Engineering Objectives

| Objective | V3 Upgrade Strategy |
| :--- | :--- |
| **1. Counterfactual Uplift & Action Models** | Train action-specific calibrated estimators $\hat{P}(Y=1 \mid X, a)$ or uplift models to maximize net recovery over heuristic rules. |
| **2. Durable Persistence Layer** | Implement a lightweight SQLite-backed persistent store (`simulator/persistence.py`) so idempotency records, decision lineage, and outcomes survive server restarts. |
| **3. Portfolio Optimization Upgrade** | Introduce a 0/1 Multi-Choice Knapsack / Dynamic Programming solver in `simulator/portfolio_optimizer.py` with exact budget constraint guarantees. |
| **4. Razorpay Execution Adapter Interface** | Build `simulator/execution_adapters.py` establishing clean interfaces for `SimulationExecutionAdapter` and `RazorpayTestModeAdapter`. |
| **5. Multi-Seed & Ablation Suite** | Build `simulator/v3_multi_seed_evaluation.py` and `simulator/v3_ablation.py` to evaluate 5 independent seeds and document component contributions in `docs/v3_ablation_results.md`. |

---

## 3. Explicit Non-Goals & Limitations

- **No Fake Live Razorpay Transactions**: All automated dispatches remain explicitly labeled as `SIMULATED_EXECUTION` unless test API keys are provided.
- **No Unnecessary External Dependencies**: No PostgreSQL, Kafka, Kubernetes, vector databases, or LLMs will be added.
- **No Benchmark Cherry-Picking**: Final evaluation test sets will remain untouched until evaluation.
