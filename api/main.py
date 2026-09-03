from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import sys
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from simulator.config import SystemConfig, MODEL_VERSION, POLICY_VERSION, SYSTEM_NAME
from simulator.event_runtime import EventDrivenRuntime
from simulator.value_engine import CounterfactualValueEngine
from simulator.portfolio_optimizer import PortfolioOptimizer
from simulator.v2_counterfactual_policy import load_model, MODEL_PATH, MODEL_FEATURES

DATA_DIR = BASE_DIR / "data"

app = FastAPI(
    title="RecoveryOS V2 API",
    version="2.0.0",
    description="Counterfactual AI Recovery Optimization & Decision Platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
        "version": "2.0.0",
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