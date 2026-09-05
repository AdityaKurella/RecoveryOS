import hmac
import hashlib
import os
import json
import base64
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import sys
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from simulator.config import SystemConfig, MODEL_VERSION, POLICY_VERSION, SYSTEM_NAME, RAZORPAY_WEBHOOK_SECRET
from simulator.event_runtime import EventDrivenRuntime
from simulator.value_engine import CounterfactualValueEngine
from simulator.portfolio_optimizer import PortfolioOptimizer
from simulator.v2_counterfactual_policy import load_model, MODEL_PATH, MODEL_FEATURES

DATA_DIR = BASE_DIR / "data"

app = FastAPI(
    title="RecoveryOS V3.1 API",
    version="3.1.0",
    description="Counterfactual AI Recovery Optimization & Decision Platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Runtime & Model Instances
config = SystemConfig()
runtime = EventDrivenRuntime(config=config)
model = load_model(MODEL_PATH)
value_engine = CounterfactualValueEngine()
portfolio_optimizer = PortfolioOptimizer(capacity=config.capacity)


# Pydantic Schemas
class PaymentFailedEventPayload(BaseModel):
    event_id: Optional[str] = None
    failure_id: str
    payment_id: str
    customer_id: str
    amount: float = Field(..., gt=0, description="Payment failure amount in INR")
    failure_reason: str
    behavior_profile: str = "normal"
    account_age_days: int = 30
    successful_payments: int = 1
    failed_payments: int = 0
    total_payments: int = 1
    payment_success_rate: float = 1.0
    historical_recovery_rate: float = 0.5
    engagement_score: float = 0.8
    payment_status: str = "FAILED"


def load_csv(relative_path: str) -> pd.DataFrame:
    path = DATA_DIR / relative_path
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")
    return pd.read_csv(path)


def money(value) -> float:
    return round(float(value), 2)


# ==================================================
# V2 API Endpoints
# ==================================================

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "system": SYSTEM_NAME,
        "model_version": MODEL_VERSION,
        "policy_version": POLICY_VERSION,
        "model_loaded": model is not None,
    }


@app.get("/api/v2/config")
def get_system_config():
    return config.to_dict()


@app.post("/api/v2/events/failure")
def process_payment_failure_event(payload: PaymentFailedEventPayload):
    try:
        event_dict = payload.model_dump()
        result = runtime.process_payment_failed_event(event_dict, model, MODEL_FEATURES)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v2/webhooks/razorpay")
async def handle_razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None, alias="X-Razorpay-Signature"),
    x_razorpay_event_id: Optional[str] = Header(None, alias="x-razorpay-event-id"),
):
    """
    Inbound Razorpay Test Mode webhook adapter.
    Normalizes payment.failed webhooks into RecoveryOS event schema.
    """
    try:
        raw_body = await request.body()
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to read request body")

    # 1. HMAC SHA256 Signature Verification if secret is configured
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET") or RAZORPAY_WEBHOOK_SECRET
    if secret:
        if not x_razorpay_signature:
            raise HTTPException(status_code=400, detail="Missing X-Razorpay-Signature header")

        expected_signature = hmac.new(
            secret.encode("utf-8"),
            raw_body,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_signature, x_razorpay_signature):
            raise HTTPException(status_code=401, detail="Invalid X-Razorpay-Signature")

    # 2. JSON Body Parsing
    try:
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload must be a JSON object")

    # 3. Validate Razorpay Event Type
    event_type = payload.get("event")
    if event_type != "payment.failed":
        return {
            "accepted": False,
            "status": "IGNORED",
            "message": f"Event type '{event_type}' ignored. Only 'payment.failed' is processed.",
            "event_id": x_razorpay_event_id or payload.get("event_id"),
        }

    # 4. Extract Payment Entity
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity")
    if not isinstance(payment_entity, dict):
        raise HTTPException(status_code=400, detail="Missing payment entity in Razorpay webhook payload")

    payment_id = payment_entity.get("id")
    raw_amount = payment_entity.get("amount")

    if not payment_id or raw_amount is None:
        raise HTTPException(status_code=400, detail="Razorpay webhook payload missing required payment id or amount")

    try:
        amount_paisa = float(raw_amount)
        if amount_paisa <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid payment amount in Razorpay payload")

    # Convert paisa to INR (e.g. 250000 paisa -> 2500.00 INR)
    amount_inr = round(amount_paisa / 100.0, 2)

    # Extract customer ID
    raw_cust_id = payment_entity.get("customer_id")
    customer_id = str(raw_cust_id) if raw_cust_id else "cust_unknown"

    # Normalize Failure Reason
    raw_reason = payment_entity.get("error_reason") or payment_entity.get("error_description") or "PAYMENT_FAILED"
    failure_reason = str(raw_reason).upper().replace(" ", "_")

    # Determine Event ID & Failure ID
    event_id = x_razorpay_event_id or payload.get("event_id")
    if not event_id:
        raise HTTPException(status_code=400, detail="Missing x-razorpay-event-id header or payload event_id")

    failure_id = f"FAIL_{payment_id}"

    # Build Normalized RecoveryOS Failure Event with Integration Defaults
    normalized_event = {
        "event_id": str(event_id),
        "failure_id": failure_id,
        "payment_id": str(payment_id),
        "customer_id": customer_id,
        "amount": amount_inr,
        "failure_reason": failure_reason,
        "behavior_profile": "normal",            # Integration default
        "account_age_days": 30,                  # Integration default
        "successful_payments": 1,               # Integration default
        "failed_payments": 0,                   # Integration default
        "total_payments": 1,                    # Integration default
        "payment_success_rate": 1.0,            # Integration default
        "historical_recovery_rate": 0.5,         # Integration default
        "engagement_score": 0.8,                 # Integration default
        "payment_status": "FAILED",
    }

    # 5. Process through existing RecoveryOS Runtime
    try:
        result = runtime.process_payment_failed_event(normalized_event, model, MODEL_FEATURES)
        return {
            "accepted": True,
            "event_id": str(event_id),
            "status": result.get("status"),
            "message": result.get("message"),
            "decision_id": result.get("record", {}).get("decision_id") if result.get("record") else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v2/test/razorpay-order")
def create_test_razorpay_order(amount: float = 2500.0):
    """
    Test Mode helper endpoint to create a Razorpay Test Order.
    Never exposes API secrets.
    """
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret:
        raise HTTPException(status_code=400, detail="RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET not set in environment.")

    amount_paisa = int(round(amount * 100))
    auth_bytes = f"{key_id}:{key_secret}".encode("utf-8")
    b64_auth = base64.b64encode(auth_bytes).decode("utf-8")

    payload = {
        "amount": amount_paisa,
        "currency": "INR",
        "receipt": f"rcpt_demo_{int(time.time()*1000)}",
        "notes": {
            "purpose": "RecoveryOS Test Failure Demonstration"
        }
    }

    try:
        req = urllib.request.Request(
            "https://api.razorpay.com/v1/orders",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Basic {b64_auth}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            order_data = json.loads(resp.read().decode("utf-8"))
            return {
                "status": "SUCCESS",
                "order_id": order_data.get("id"),
                "amount_inr": amount,
                "amount_paisa": amount_paisa,
                "currency": "INR",
                "key_id": key_id,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create Razorpay Order: {str(e)}")


@app.get("/test/checkout", response_class=HTMLResponse)
def test_checkout_page(amount: float = 2500.0):
    """
    Minimal Razorpay Standard Checkout test page for generating Test Mode payment.failed events.
    """
    key_id = os.getenv("RAZORPAY_KEY_ID") or ""
    key_secret = os.getenv("RAZORPAY_KEY_SECRET") or ""

    if not key_id or not key_secret:
        return HTMLResponse("<h3>Error: RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET not set in environment.</h3>", status_code=400)

    amount_paisa = int(round(amount * 100))
    auth_bytes = f"{key_id}:{key_secret}".encode("utf-8")
    b64_auth = base64.b64encode(auth_bytes).decode("utf-8")

    payload = {
        "amount": amount_paisa,
        "currency": "INR",
        "receipt": f"rcpt_demo_{int(time.time()*1000)}",
        "notes": {"purpose": "RecoveryOS Test Failure Demo"}
    }

    order_id = ""
    try:
        req = urllib.request.Request(
            "https://api.razorpay.com/v1/orders",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Basic {b64_auth}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            order_data = json.loads(resp.read().decode("utf-8"))
            order_id = order_data.get("id", "")
    except Exception as e:
        return HTMLResponse(f"<h3>Error creating Razorpay order: {e}</h3>", status_code=500)

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>RecoveryOS Razorpay Test Checkout</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 40px; background: #0f172a; color: #f8fafc; text-align: center; }}
        .card {{ max-width: 480px; margin: 0 auto; background: #1e293b; padding: 32px; border-radius: 12px; border: 1px solid #334155; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5); }}
        .btn {{ background: #ea580c; color: white; border: none; padding: 14px 28px; font-size: 16px; border-radius: 8px; cursor: pointer; font-weight: 600; margin-top: 20px; width: 100%; transition: background 0.2s; }}
        .btn:hover {{ background: #c2410c; }}
        .badge {{ display: inline-block; background: #38bdf8; color: #0f172a; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: bold; margin-bottom: 16px; }}
        code {{ background: #0f172a; padding: 4px 8px; border-radius: 4px; font-family: monospace; color: #38bdf8; }}
    </style>
</head>
<body>
    <div class="card">
        <span class="badge">RAZORPAY TEST MODE DEMO</span>
        <h2>RecoveryOS Payment Failure Demo</h2>
        <p>Order ID: <code>{order_id}</code></p>
        <p>Amount: <strong>₹{amount:,.2f} INR</strong> ({amount_paisa} paisa)</p>
        <hr style="border-color: #334155; margin: 20px 0;">
        <p style="font-size: 14px; color: #94a3b8; text-align: left;">
            <strong>Instructions to emit a <code>payment.failed</code> event:</strong><br>
            1. Click the button below to launch Razorpay Checkout.<br>
            2. Select <strong>Netbanking</strong> &rarr; Pick any bank.<br>
            3. On the test screen, click <strong>"Failure"</strong> (or close the modal).<br>
            4. Razorpay emits a real Test Mode <code>payment.failed</code> webhook to RecoveryOS.
        </p>
        <button id="rzp-button" class="btn">Launch Test Checkout Modal &rarr;</button>
    </div>
    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
    <script>
    var options = {{
        "key": "{key_id}",
        "amount": "{amount_paisa}",
        "currency": "INR",
        "name": "RecoveryOS Test Store",
        "description": "Payment Failure Recovery Test",
        "order_id": "{order_id}",
        "handler": function (response){{ alert("Payment Succeeded: " + response.razorpay_payment_id); }},
        "prefill": {{
            "name": "Test Customer",
            "email": "customer@example.com",
            "contact": "9999999999"
        }},
        "theme": {{ "color": "#ea580c" }}
    }};
    var rzp1 = new Razorpay(options);
    document.getElementById('rzp-button').onclick = function(e){{
        rzp1.open();
        e.preventDefault();
    }}
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content, status_code=200)


@app.get("/api/v2/decisions")
def get_v2_decisions():
    try:
        dec_path = DATA_DIR / "ml_decision" / "v2_policy_decisions.csv"
        cand_path = DATA_DIR / "ml_decision" / "v2_candidate_action_values.csv"

        dec_df = pd.read_csv(dec_path) if dec_path.exists() else pd.DataFrame()
        cand_df = pd.read_csv(cand_path) if cand_path.exists() else pd.DataFrame()

        return {
            "decisions_count": len(dec_df),
            "candidates_count": len(cand_df),
            "decisions": dec_df.fillna("").to_dict(orient="records"),
            "candidates": cand_df.fillna("").to_dict(orient="records"),
            "candidates_sample": cand_df.head(30).fillna("").to_dict(orient="records"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v2/portfolio")
def get_v2_portfolio(capacity: Optional[int] = None):
    try:
        cand_path = DATA_DIR / "ml_decision" / "v2_candidate_action_values.csv"
        if not cand_path.exists():
            raise FileNotFoundError("v2_candidate_action_values.csv not found. Run policy optimization first.")

        cand_df = pd.read_csv(cand_path)
        opt = PortfolioOptimizer(capacity=capacity or config.capacity)
        portfolio_df = opt.optimize_portfolio(cand_df)

        selected = portfolio_df[portfolio_df["portfolio_selected"] == True]

        return {
            "capacity": opt.capacity,
            "total_evaluated": len(portfolio_df),
            "selected_count": len(selected),
            "total_revenue_at_risk": money(portfolio_df["amount"].sum()),
            "selected_expected_net": money(selected["expected_net_recovery"].sum()),
            "portfolio": portfolio_df.fillna("").to_dict(orient="records"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v2/audit")
def get_v2_audit_trail():
    return {
        "audit_count": len(runtime.audit_log),
        "audit_trail": runtime.audit_log,
    }


# ==================================================
# V1 Legacy Backward Compatibility Endpoints
# ==================================================

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "RecoveryOS API",
        "version": "3.1.0",
        "environment": "simulation",
    }


@app.get("/api/overview")
def get_overview():
    try:
        portfolio_df = load_csv("portfolio/m11_recovery_portfolio.csv")
        outcomes_df = load_csv("outcomes/recoveryos_outcomes.csv")

        selected_cases = portfolio_df[portfolio_df["selected"] == True]

        total_failures = len(portfolio_df)
        selected_count = len(selected_cases)
        total_value_at_risk = money(portfolio_df["amount"].sum())

        expected_recovered_amount = money(selected_cases["expected_net_recovery"].sum())

        actual_recovered_amount = money(
            outcomes_df[outcomes_df["recovered"] == True]["amount"].sum()
        )

        overall_recovery_rate = round((actual_recovered_amount / total_value_at_risk) * 100, 2)

        return {
            "total_failures": total_failures,
            "selected_cases": selected_count,
            "total_value_at_risk": total_value_at_risk,
            "expected_recovered_amount": expected_recovered_amount,
            "actual_recovered_amount": actual_recovered_amount,
            "overall_recovery_rate": overall_recovery_rate,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolio")
def get_portfolio():
    df = load_csv("portfolio/m11_recovery_portfolio.csv")
    return df.fillna("").to_dict(orient="records")


@app.get("/api/decisions")
def get_decisions():
    df = load_csv("decisions/recoveryos_decisions.csv")
    return df.fillna("").to_dict(orient="records")


@app.get("/api/policy")
def get_policy():
    df = load_csv("policy/recoveryos_policy_decisions.csv")
    return df.fillna("").to_dict(orient="records")


@app.get("/api/execution")
def get_execution():
    df = load_csv("execution/recoveryos_execution_results.csv")
    return df.fillna("").to_dict(orient="records")


@app.get("/api/outcomes")
def get_outcomes():
    df = load_csv("outcomes/recoveryos_outcomes.csv")
    return df.fillna("").to_dict(orient="records")


@app.get("/api/evaluation")
def get_evaluation():
    df = load_csv("evaluation/recoveryos_evaluation_summary.csv")
    return df.fillna("").to_dict(orient="records")