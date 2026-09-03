from pathlib import Path

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


# --------------------------------------------------
# Paths
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


# --------------------------------------------------
# App
# --------------------------------------------------

app = FastAPI(
    title="RecoveryOS API",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173",
    "http://localhost:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def load_csv(relative_path: str) -> pd.DataFrame:
    path = DATA_DIR / relative_path

    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")

    return pd.read_csv(path)


def money(value) -> float:
    return round(float(value), 2)


def json_records(df: pd.DataFrame):
    return df.fillna("").to_dict(orient="records")


# --------------------------------------------------
# Health
# --------------------------------------------------

@app.get("/")
def root():
    return {
        "service": "RecoveryOS API",
        "status": "online",
        "environment": "simulation",
    }


# --------------------------------------------------
# Overview
# --------------------------------------------------

@app.get("/api/overview")
def overview():

    # M11 portfolio contains 559 candidates.
    # Only selected=True belongs to the final portfolio.
    portfolio = load_csv(
        "portfolio/m11_recovery_portfolio.csv"
    )

    portfolio["selected"] = (
        portfolio["selected"]
        .astype(str)
        .str.lower()
        .isin(["true", "1", "yes"])
    )

    selected_portfolio = portfolio[
        portfolio["selected"]
    ].copy()

    # M15 outcomes
    outcomes = load_csv(
        "outcomes/recoveryos_outcomes.csv"
    )

    recovered = outcomes[
        outcomes["outcome_status"] == "RECOVERED"
    ]

    executed = outcomes[
        outcomes["outcome_status"].isin(
            ["RECOVERED", "NOT_RECOVERED"]
        )
    ]

    revenue_at_risk = selected_portfolio[
        "amount"
    ].sum()

    expected_recovery = selected_portfolio[
        "expected_gross_recovery"
    ].sum()

    simulated_recovered = recovered[
        "actual_recovered_amount"
    ].sum()

    recovery_rate = (
        len(recovered) / len(executed) * 100
        if len(executed) > 0
        else 0
    )

    return {
        "revenue_at_risk": money(revenue_at_risk),
        "expected_recovery": money(expected_recovery),
        "simulated_recovered": money(simulated_recovered),
        "recovery_rate": round(recovery_rate, 2),
        "portfolio_cases": len(selected_portfolio),
        "executed_cases": len(executed),
        "recovered_cases": len(recovered),
        "human_cases": len(
            outcomes[
                outcomes["outcome_status"]
                == "AWAITING_HUMAN"
            ]
        ),
    }


# --------------------------------------------------
# Portfolio
# --------------------------------------------------

@app.get("/api/portfolio")
def portfolio():

    df = load_csv(
        "portfolio/m11_recovery_portfolio.csv"
    )

    df["selected"] = (
        df["selected"]
        .astype(str)
        .str.lower()
        .isin(["true", "1", "yes"])
    )

    # Show final selected portfolio first.
    df = df.sort_values(
        by=["selected", "portfolio_rank"],
        ascending=[False, True],
    )

    return {
        "count": int(df["selected"].sum()),
        "candidate_count": len(df),
        "items": json_records(df),
    }


# --------------------------------------------------
# Decisions
# --------------------------------------------------

@app.get("/api/decisions")
def decisions():

    df = load_csv(
        "decisions/recoveryos_decisions.csv"
    )

    return {
        "count": len(df),
        "items": json_records(df),
    }


# --------------------------------------------------
# Policy decisions
# --------------------------------------------------

@app.get("/api/policy")
def policy():

    df = load_csv(
        "policy/recoveryos_policy_decisions.csv"
    )

    return {
        "count": len(df),
        "items": json_records(df),
    }


# --------------------------------------------------
# Execution
# --------------------------------------------------

@app.get("/api/execution")
def execution():

    df = load_csv(
        "execution/recoveryos_execution_results.csv"
    )

    return {
        "count": len(df),
        "items": json_records(df),
    }


# --------------------------------------------------
# Outcomes
# --------------------------------------------------

@app.get("/api/outcomes")
def outcomes():

    df = load_csv(
        "outcomes/recoveryos_outcomes.csv"
    )

    return {
        "count": len(df),
        "items": json_records(df),
    }


# --------------------------------------------------
# Evaluation
# --------------------------------------------------

@app.get("/api/evaluation")
def evaluation():

    path = DATA_DIR / (
        "evaluation/recoveryos_evaluation_summary.csv"
    )

    if not path.exists():
        return {
            "available": False,
            "items": [],
        }

    df = pd.read_csv(path)

    return {
        "available": True,
        "count": len(df),
        "items": json_records(df),
    }