"""FastAPI application: browser UI plus JSON endpoints for V1 evaluation and V2 comparison."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .compare import compare_portfolio
from .engine import evaluate_portfolio
from .models import Claim, Policy
from .reporting import results_to_csv, summarize_results

PACKAGE_DIR = Path(__file__).resolve().parent
STATIC_DIR = PACKAGE_DIR / "static"
FIXTURE_DIR = PACKAGE_DIR.parent.parent / "data" / "fixtures"
ALLOWED_FIXTURES = {
    "sample_policy_v1.json",
    "sample_policy_v2.json",
    "sample_claims.csv",
}

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


@app.get("/", include_in_schema=False)
def ui_home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/fixtures/{filename}", include_in_schema=False)
def ui_fixture(filename: str):
    if filename not in ALLOWED_FIXTURES:
        raise HTTPException(status_code=404, detail="Unknown fixture")
    path = FIXTURE_DIR / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Fixture file is missing")
    media = "application/json" if path.suffix == ".json" else "text/csv"
    return FileResponse(path, media_type=media)


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


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
