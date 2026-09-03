# RecoveryOS V3 — System Architecture & Engineering Blueprint

> **Branch**: `v3-dev`  
> **Control Group Baseline**: V2 Commit `3ff7976` (`test: harden V2 runtime and API safeguards`)

---

## 1. System Architecture Overview

RecoveryOS V3 expands the V2 event-driven architecture by introducing:
1. **Durable SQLite Persistence Store** (`simulator/persistence.py`): Replaces in-memory idempotency state with process-restart resilient storage.
2. **Pluggable Execution Adapters** (`simulator/execution_adapters.py`): Establishes abstract interfaces for `SimulationExecutionAdapter` and `RazorpayTestModeAdapter`.
3. **Action-Specific & Calibrated Machine Learning Pipelines** (`simulator/v3_counterfactual_model.py` & `simulator/v3_calibrated_model.py`): Evaluates counterfactual probability estimators.
4. **Empirical Ablation & Multi-Seed Framework** (`simulator/v3_ablation.py`): Measures exact component value contributions.

```
[Payment Failure Event: payment.failed]
                  │
                  ▼
   [Durable SQLite Idempotency Engine] ──(Duplicate Event)──> [Cached Response]
                  │
                  ▼
    [Context & Feature Builder]
                  │
                  ▼
   [ExtraTrees Counterfactual Model]
                  │
                  ▼
  [Counterfactual Economic Value Engine] ──(Scores 6 Actions: 5 Active + STOP)
                  │
                  ▼
      [Portfolio Optimizer] ──────────────(Constrains by Capacity K & Budget B)
                  │
                  ▼
     [Policy & Safety Engine] ─────────(Assigns ALLOW, HUMAN, STOP)
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
[Durable Audit Lineage & Outcome Engine]
```

---

## 2. Pluggable Execution Adapters

```python
class BaseExecutionAdapter(ABC):
    @abstractmethod
    def execute_action(self, decision_record: Dict[str, Any]) -> Dict[str, Any]:
        pass

class SimulationExecutionAdapter(BaseExecutionAdapter): ...
class RazorpayTestModeAdapter(BaseExecutionAdapter): ...
```

---

## 3. Data Isolation Guarantees

Inference pipelines are strictly isolated from ground-truth counterfactual environment probabilities. `true_recovery_probability`, `oracle_probability`, and `recovered` fields are 100% prohibited from inference inputs.
