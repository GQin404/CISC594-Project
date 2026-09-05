"""Minimal FastAPI surface for V1 evaluation and V2 comparison."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from .compare import compare_portfolio
from .engine import evaluate_portfolio
from .models import Claim, Policy
from .reporting import results_to_csv, summarize_results

app = FastAPI(
    title="Payer Policy Change Impact Simulator",
    version="0.2.0",
    description="Deterministic policy evaluation (V1) and policy-change impact comparison (V2).",
)


class EvaluateRequest(BaseModel):
    policy: Policy
    claims: list[Claim] = Field(min_length=1)


class CompareRequest(BaseModel):
    baseline: Policy
    proposed: Policy
    claims: list[Claim] = Field(min_length=1)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/evaluate")
def evaluate(request: EvaluateRequest):
    try:
        results = evaluate_portfolio(request.policy, request.claims)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "summary": summarize_results(results).model_dump(mode="json"),
        "results": [item.model_dump(mode="json") for item in results],
    }


@app.post("/v1/evaluate/export", response_class=PlainTextResponse)
def evaluate_export(request: EvaluateRequest) -> str:
    try:
        results = evaluate_portfolio(request.policy, request.claims)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return results_to_csv(results)


@app.post("/v2/compare")
def compare(request: CompareRequest):
    try:
        summary = compare_portfolio(request.baseline, request.proposed, request.claims)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return summary.model_dump(mode="json")
