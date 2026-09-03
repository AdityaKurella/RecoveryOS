# RecoveryOS V3 — Ablation Study Results

> **Objective**: Quantify the marginal contribution of each system component across capacity constraints and safety guardrails.

---

## 1. Summary of Ablation Scenarios

| Ablation Scenario | Dispatched Active Cases | Expected Gross (₹) | Intervention Cost (₹) | Expected NET Recovery (₹) | Key Contribution |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Ablation 1: Unconstrained Value Engine ($K=\infty$)** | 559 | ₹825,141.59 | ₹1,354.00 | **₹823,787.59** | Evaluates all 559 failures independently without capacity limits. |
| **Ablation 2: Portfolio Optimizer (Capacity $K=100$)** | 100 | ₹564,923.66 | ₹252.00 | **₹564,671.66** | Selects top 100 active cases by net recovery, reducing intervention cost by 81.4%. |
| **Ablation 3: Full V3 Platform ($K=100$ + Safety Guardrails)** | 66 | ₹406,852.80 | ₹180.00 | **₹406,672.80** | Enforces `HUMAN` escalation for high-value cases ($\ge ₹10,000$) with low confidence, eliminating risk on ₹158,071 value at risk. |

---

## 2. Key Engineering Takeaways

1. **Portfolio Capacity Efficiency**: Restricting active interventions to the top 100 cases recovers **68.5% of total net revenue** while incurring only **18.6% of total intervention costs**.
2. **Safety Bounded Autonomy**: Safety guardrails escalate 34 high-value / low-confidence cases to manual review (`HUMAN`), preventing unverified autonomous actions on high-stakes transactions.
