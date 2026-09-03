# RecoveryOS V2 Architecture Review & Strategic Blueprint

> **System**: RecoveryOS V2 (Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery)  
> **Baseline Commit**: `e1ef9ed1026771ed3a3c1105b5e36d39ecf83773` (V1 Frozen)

---

## 1. Executive Summary & V1 Baseline Audit

RecoveryOS V1 established a 16-stage batch pipeline (M1–M16) using an `ExtraTreesClassifier` model to score 5 candidate payment recovery actions (`RETRY_NOW`, `WAIT_AND_RETRY`, `SEND_REMINDER`, `PAYMENT_LINK`, `UPDATE_PAYMENT_METHOD`).

### V1 Baseline Strengths
1. **Deterministic Foundations**: Fixed random seeds (`seed=42`) and SHA-256 hash hashing ensure 100% reproducible data generation and simulated outcomes.
2. **Ground-Truth Counterfactual Environment**: Pre-calculated counterfactual probabilities allow rigorous offline evaluation against baseline rules and theoretical oracle ceilings.
3. **Bounded Autonomy Framework**: Clear separation between ML candidate action selection and deterministic policy guardrails (`ALLOW`, `HUMAN`, `STOP`).
4. **Verified Performance Baseline**: Achieves ₹842,050.27 expected net recovery on 559 test cases (77.34% recovery rate), outperforming unguided retry strategies.

### V1 Baseline Weaknesses & Technical Debt
1. **Unconstrained Per-Failure Optimization**: V1 evaluates each failure independently without portfolio-level capacity constraints or intervention budgets.
2. **Static Read-Only File Architecture**: FastAPI serves pre-computed CSV files from `data/` and lacks dynamic event ingestion, real-time decisioning, or write endpoints.
3. **Absence of `STOP` Action in Value Optimization**: Active interventions were forced even when expected gross recovery fell below intervention costs.
4. **Hardcoded Configuration Constants**: Thresholds, action costs, and parameters are scattered across 26 individual Python scripts.
5. **Lack of Idempotency & Event Safety**: No event deduplication, stale decision guards, or execution tracking IDs existed.

---

## 2. Proposed V2 Target Architecture

RecoveryOS V2 transforms the static batch pipeline into an **Event-Driven Counterfactual Recovery Platform** featuring portfolio optimization, idempotent execution, decision lineage, multi-seed evaluation, and a decision console:

```
[Payment Failure Event: payment.failed]
                  │
                  ▼
   [Validation & Idempotency Engine] ──(Duplicate Check)──> [Rejection / Cached Response]
                  │
                  ▼
    [Context & Feature Builder]
                  │
                  ▼
   [ExtraTrees Counterfactual Model]
                  │
                  ▼
  [Counterfactual Economic Value Engine] ──(Evaluates 6 Actions: 5 Active + STOP)
                  │
                  ▼
      [Portfolio Optimizer] ──────────────(Constrains by Capacity K & Budget B)
                  │
                  ▼
     [Policy & Guardrail Engine] ─────────(Assigns ALLOW, HUMAN, STOP)
                  │
                  ▼
    ┌─────────────┼─────────────┐
    │             │             │
 [ALLOW]       [HUMAN]       [STOP]
    │             │             │
    ▼             ▼             ▼
[Simulated   [Review Queue] [Zero Action
 Execution]                  Logged]
    │
    ▼
[Outcome Engine & SHA-256 Audit Trail]
    │
    ▼
[Multi-Seed Evaluation & Diagnostics Console]
```

---

## 3. Core V2 Modules & Migration Strategy

| Milestone | Component | Purpose & Implementation Details |
| :--- | :--- | :--- |
| **M1** | Value Engine | Evaluates 6 candidate actions (`RETRY_NOW`, `WAIT_AND_RETRY`, `SEND_REMINDER`, `PAYMENT_LINK`, `UPDATE_PAYMENT_METHOD`, `STOP`) using vector expected net formulas. |
| **M2** | Config Layer | Centralizes costs, thresholds, capacity, and versioning in `simulator/config.py`. |
| **M3** | Portfolio Optimizer | Selects top $K$ candidate decisions maximizing total portfolio net recovery under capacity/budget constraints. |
| **M4** | Event Runtime | Ingests `payment.failed` event JSON payloads, performs context lookups, and triggers real-time decisioning. |
| **M5** | Safety & Idempotency | Enforces duplicate event protection, duplicate execution prevention, stale payment guards, and retry limits. |
| **M6** | Decision Lineage | Records immutable audit trails (`decision_id`, `event_id`, features, probabilities, economics, policy checks, execution state). |
| **M7** | Outcome Engine | Simulates and logs realized outcomes (`recovered`, `simulated_revenue`, `outcome_id`) with strict label separation. |
| **M8** | Multi-Seed Evaluation | Runs 5 independent seeds across V1, V2, Rules, and Oracle, reporting mean, std, min, max for all key metrics. |
| **M9** | Model Diagnostics | Computes probability calibration, ranking quality, policy regret, and oracle opportunity loss segmentations. |
| **M10** | Automated Testing | Builds comprehensive unit, integration, idempotency, and API tests (`tests/test_*.py`). |
| **M11** | FastAPI Service | Hardens FastAPI with Pydantic schemas, CORS, `/health`, `/api/v2/events/failure`, `/api/v2/decisions`, `/api/v2/portfolio`, `/api/v2/audit`, `/api/v2/evaluation`. |
| **M12** | React Decision Console | Upgrades UI with portfolio capacity sliders, candidate action matrix, decision lineage drawer, and evaluation benchmarks. |
| **M13** | Demo Runner | Creates deterministic end-to-end demo scenarios (high-value recovery, HUMAN escalation, STOP, duplicate rejection, stale rejection). |
| **M14** | Buildathon Report | Generates `docs/buildathon_evaluation.md` assessing RecoveryOS against Razorpay Track 03 criteria. |
| **M15–M18** | Hygiene & Final Release | Security audit, performance benchmark (1,000–10,000 events), final regression verification, and `RECOVERYOS_V2_FINAL_REPORT.md`. |

---

## 4. Key Security & Non-Goals

### Security & Data Isolation Principles
1. **Strict Inference Data Separation**: `true_recovery_probability`, `oracle_probability`, and future outcome fields are strictly prohibited from inference feature pipelines.
2. **Zero Secrets in Codebase**: Environment variables and API credentials managed via config without committed secrets.
3. **Sanitized Input Schemas**: Pydantic models validate all incoming event payloads.

### Explicit Non-Goals
- **No LLMs for Decisioning**: All recovery probabilities and decisions are derived strictly from ML model inference and economic value calculations.
- **No Unnecessary External Services**: No Kafka, Kubernetes, vector DBs, microservice meshes, or external SaaS dependencies.
- **No Fake Live Integrations**: All execution dispatches are transparently labeled as `SIMULATED_EXECUTION`.
