# RecoveryOS
> **AI-powered revenue recovery decision system for failed payments.**

> **Built for Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery**

RecoveryOS is an intelligent decision engine that determines which failed subscription payments deserve recovery effort, which intervention is most valuable, and when to stop.

---

## 1. The Problem

Subscription payments fail for many different reasons, from expired cards to temporary bank server downtime.

- **Different payment failures require different recovery actions**: A temporary bank failure may simply need a delayed retry, while an expired card requires customer outreach.
- **Blind retries waste money and create customer friction**: Retrying every failed payment blindly incurs unnecessary payment processing fees and risks annoying customers.
- **Current systems focus on probability, not value**: Predicting whether a payment can recover is not enough if the cost of recovering it exceeds the payment amount.
- **RecoveryOS optimizes recovery effort**: It focuses recovery actions where they generate the highest expected net revenue.

---

## 2. The Solution

When a payment fails, RecoveryOS processes it through a clear decision flow:

```
Failed Payment Event
        ↓
1. Understand Context
        ↓
2. Compare Recovery Actions
        ↓
3. Estimate Expected Net Value
        ↓
4. Choose Best Safe Action
        ↓
5. ALLOW / HUMAN / STOP Decision
        ↓
6. Execute Simulation / Stop
        ↓
7. Record Outcome in Audit Store
```

- **Understand Context**: Reads payment amount, failure reason, and customer payment history.
- **Compare Recovery Actions**: Evaluates all available recovery interventions at the same time.
- **Estimate Expected Net Value**: Calculates predicted gross recovery minus the cost of taking each action.
- **Choose Best Safe Action**: Selects the best recovery action based on expected value and safety.
- **ALLOW / HUMAN / STOP Decision**: Determines if the action can run automatically, needs human review, or should stop.
- **Execute Simulation / Stop**: Executes the selected action via a sandbox adapter or logs a zero-action `STOP`.
- **Record Outcome**: Persists decision lineage and keeps decisions and outcomes available after a restart.

---

## 3. Recovery Actions

For every payment failure, RecoveryOS evaluates six candidate recovery actions:

- **Retry now**: Immediate payment retry (₹2.00 intervention cost)
- **Retry later**: Scheduled delay retry (₹2.00 intervention cost)
- **Send reminder**: Email or SMS customer notification (₹1.00 intervention cost)
- **Send payment link**: Dedicated payment link dispatch (₹3.00 intervention cost)
- **Ask customer to update payment method**: Billing update request (₹3.00 intervention cost)
- **Stop**: Take no action to avoid wasting money (₹0.00 intervention cost)

### Core Economic Formula

$$\text{Expected Net Value} = \text{Amount} \times \text{Probability of Recovery} - \text{Cost of Intervention}$$

*In plain English: "We choose an action based on how much money it is expected to recover after accounting for the cost of taking that action."*

---

## 4. Why RecoveryOS Is Different

### 1. It compares actions
Instead of simply predicting whether a payment will recover, RecoveryOS compares different possible actions for the exact same failed payment to find the best option.

### 2. It considers money, not just probability
A 90% chance of recovering a ₹50 payment (Expected Gross: ₹45) after a ₹3 retry cost yields ₹42 net value. A 70% chance of recovering a ₹10,000 payment (Expected Gross: ₹7,000) after a ₹3 cost yields ₹6,997 net value. RecoveryOS focuses on the net revenue recovered.

### 3. It prioritizes the portfolio
When recovery capacity or budget is limited, RecoveryOS uses a **Greedy Priority Portfolio Optimizer** to prioritize the top $K$ failed payments where recovery effort produces the highest expected net return under cumulative budget and frequency constraints.

### 4. It knows when not to act
When intervention costs exceed expected gross recovery, RecoveryOS selects `STOP` (zero cost, zero friction) to prevent value destruction.

---

## 5. Razorpay Test Mode Integration

Razorpay provides payment infrastructure and failure events. RecoveryOS acts as the decision layer that receives failure events and decides the best recovery action based on expected value and safety.

```
Razorpay Infrastructure → Failed Payment Event → RecoveryOS Decision Engine → Recovery Action → Audit Log
```

- **Razorpay Test API**: Uses official Razorpay API credentials (`RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`) to create test orders (`POST /api/v2/test/razorpay-order`).
- **Standard Checkout**: Uses embedded Razorpay Standard Checkout (`checkout.js`) at `/test/checkout` to simulate customer payments.
- **`payment.failed` Webhook**: Ingests real webhook notifications via `POST /api/v2/webhooks/razorpay`.
- **HMAC-SHA256 Signature Verification**: Computes HMAC signatures over raw HTTP request bodies to verify authenticity.
- **Event ID Idempotency**: Uses Razorpay `x-razorpay-event-id` headers to prevent processing the same event twice.
- **Customer Context**: Razorpay Test Mode webhook events currently use safe default context values when historical customer context is unavailable.
- **Public HTTPS Tunnel**: Exposed via Cloudflare tunnel for external webhook delivery testing.

> **Disclaimer**: Test Mode only. No real money is moved.

---

## 6. Safety

Every decision is assigned an **ALLOW / HUMAN / STOP safety decision**:

- **ALLOW**: Safe to execute autonomously.
- **HUMAN**: High-value payment or low-confidence prediction escalated to human review.
- **STOP**: No recovery action should be taken.

### Key Safeguards
- **Retry Limits**: Escalates to human review when maximum retry attempts are reached.
- **Already Recovered Protection**: Rejects events for payments that are already successful.
- **Duplicate Event Protection**: Prevents duplicate execution on webhook retries using event ID claims.
- **Stale Payment Protection**: Blocks autonomous execution on payment failures older than 30 days.
- **High-Value Human Review**: Escalates high-value payments (e.g. $\ge \text{₹10,000}$) with low ML confidence.

---

## 7. Results

### Held-Out Synthetic Evaluation

Evaluated on **559 held-out synthetic failed-payment cases** (Total revenue at risk: **₹1,090,563.78**):

| Metric | RecoveryOS V3 Hybrid Policy | Failure-Aware Rules Baseline | Oracle Upper Bound |
| :--- | :---: | :---: | :---: |
| **Expected Gross Recovery** | ₹844,202.91 | ₹844,158.90 | ₹856,711.57 |
| **Intervention Cost** | ₹1,336.00 | ₹1,287.00 | ₹1,382.00 |
| **Expected Net Recovery** | **₹842,866.91** | ₹842,871.90 | **₹855,329.57** |
| **Recovery Rate** | **77.41%** | 77.41% | **78.56%** |
| **Action Match with Oracle** | **55.81% (312 / 559)** | — | 100.00% |
| **Oracle Opportunity Gap** | **₹12,462.66 (1.46%)** | — | 0.00% |

### Portfolio Optimization Scope (Capacity K=100)

Using the **Greedy Priority Portfolio Optimizer** under capacity ($K=100$) and budget constraints:
- **Prioritized Cases**: 100 of 559 inbound failures
- **Portfolio Revenue at Risk**: ₹720,749.40
- **Expected Net Recovery**: ₹564,671.66
- **Simulated Recovered Amount**: ₹532,461.00
- **Portfolio Recovery Rate**: **73.88%** (Overall Pipeline Recovery Rate: 48.82%)

> **Disclaimer**: These results come from a held-out synthetic evaluation environment. They reflect simulated recovery outcomes, not real Razorpay revenue.

---

## 8. Quick Start

### Prerequisites & Credentials
Copy `.env.example` to `.env` and fill in your Razorpay Test Mode credentials:

```bash
cp .env.example .env
```

```env
RAZORPAY_KEY_ID=rzp_test_your_key_id
RAZORPAY_KEY_SECRET=your_key_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
```

### Commands

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   cd frontend && npm install && cd ..
   ```

2. **Run Automated Tests** (59 / 59 passing):
   ```bash
   python -m unittest discover tests
   ```

3. **Run Benchmark Evaluation**:
   ```bash
   python simulator/v3_evaluation.py
   ```

4. **Start Backend Server**:
   ```bash
   python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
   ```

5. **Start Frontend Dashboard**:
   ```bash
   cd frontend && npm run dev -- --host 127.0.0.1 --port 5173
   ```

6. **Launch Razorpay Test Mode Demo**:
   Open [http://127.0.0.1:8000/test/checkout](http://127.0.0.1:8000/test/checkout) to launch Razorpay Test Checkout and simulate payment failure events.

---

## 9. Technology

- **Python + FastAPI**: High-performance backend API and event processing pipeline.
- **React + Vite**: Interactive frontend console with real-time Decision Replay.
- **ExtraTrees Classifier**: Machine learning model trained to predict recovery probabilities across candidate actions.
- **SQLite**: Durable SQLite audit trail with Write-Ahead Logging (WAL) that keeps decisions and outcomes available after a restart.
- **Razorpay Test Mode**: Inbound event integration using Orders API, Standard Checkout, and Webhooks.
- **Cloudflare Tunnel**: Public HTTPS URL forwarding for external webhook testing.

---

## 10. Technical Limitations & Disclaimers

- **Synthetic Benchmark**: Benchmark metrics reflect expected net recovery on a synthetic 559-case held-out test dataset, not live production revenue.
- **Test Mode Only**: Razorpay integration uses Test Mode only; no live customer money is moved.
- **Integration Defaults**: Webhook events currently use safe default context values when historical customer context is unavailable.
- **Batch Portfolio Prioritization**: Single-event webhooks evaluate actions per failure; portfolio optimization operates on batch failed-payment datasets.
- **Simulated Execution**: Action execution uses simulation adapters (`SimulationExecutionAdapter`).
- **Local Storage**: State store uses a local SQLite database (`data/recoveryos_v3_state.db`).
- **Buildathon Prototype**: RecoveryOS is an evaluation prototype built for the Razorpay AI Buildathon 2026.

---

## 11. Project Structure

- `api/`: FastAPI routes, request schemas, and webhook handlers.
- `frontend/`: React + Vite dashboard source code and Decision Replay Console.
- `simulator/`: Decision engine, ML value model, safety guardrails, state store, and evaluation benchmarks.
- `tests/`: Automated unit and integration test suite (59 tests).
- `data/`: Evaluation datasets, synthetic payment features, and trained ML model artifacts.
- `docs/`: Technical research notes, forensic audit logs, and ablation study reports.

---

## 12. Buildathon Details

- **Project**: RecoveryOS
- **Event**: Razorpay AI Buildathon 2026
- **Track**: Track 03 — AI Revenue Recovery
- **Repository**: [RecoveryOS GitHub Repository](https://github.com/AdityaKurella/RecoveryOS)
