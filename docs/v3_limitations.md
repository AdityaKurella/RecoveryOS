# RecoveryOS V3 — System Limitations & Disclaimers

> **Document Purpose**: Explicitly document known architectural and evaluation limitations of RecoveryOS V3 for hackathon judges and software reviewers.

---

## 1. Known Architectural Limitations

1. **Synthetic Environment Data Generator**: Benchmark evaluations are conducted against a synthetic counterfactual generator. Evaluated revenue numbers (e.g. ₹842,050.27) represent simulated net recovery, not live Razorpay revenue.
2. **Rules Baseline Alignment**: On synthetic data, fixed heuristic rules (`NETWORK_ERROR` $\rightarrow$ retry, `CARD_EXPIRED` $\rightarrow$ update payment method) perform slightly higher (+₹821.62 expected net) because the synthetic data generator was built using similar rules.
3. **Local SQLite Persistence**: While V3 introduces durable SQLite storage for idempotency and audit trails, enterprise deployment would replace SQLite with Redis and PostgreSQL.
4. **Offline Batch Model Training**: Machine learning model weights are trained offline on static dataset splits rather than through real-time online reinforcement learning.

---

## 2. Explicit Disclaimers

- **No Live Money Transactions**: All automated payment retry dispatches are executed via `SimulationExecutionAdapter` or `RazorpayTestModeAdapter`.
- **No LLM Decision Making**: All recovery decisions are derived from deterministic counterfactual economic value formulas ($\text{Gross} - \text{Cost}$) and ML probability inference.
