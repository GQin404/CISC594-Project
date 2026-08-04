"""CSV/JSON claim import helpers."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .models import Claim


REQUIRED_FIELDS = [
    "claim_id",
    "payer",
    "service_date",
    "submission_date",
    "procedure_code",
    "diagnosis_code",
    "place_of_service",
]


def _row_to_claim(row: dict) -> Claim:
    missing = [f for f in REQUIRED_FIELDS if not str(row.get(f, "")).strip()]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")

    auth_raw = str(row.get("authorization_on_file", "false")).strip().lower()
    return Claim(
        claim_id=str(row["claim_id"]).strip(),
        payer=str(row["payer"]).strip(),
        service_date=row["service_date"],
        submission_date=row["submission_date"],
        procedure_code=str(row["procedure_code"]).strip(),
        diagnosis_code=str(row["diagnosis_code"]).strip(),
        modifier=(str(row["modifier"]).strip() if row.get("modifier") not in (None, "") else None),
        place_of_service=str(row["place_of_service"]).strip(),
        authorization_on_file=auth_raw in {"1", "true", "yes", "y"},
    )


def load_claims_csv(path: str | Path) -> list[Claim]:
    claims: list[Claim] = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader, start=2):
            try:
                claims.append(_row_to_claim(row))
            except Exception as exc:  # noqa: BLE001 - collect row context for callers
                raise ValueError(f"row {index}: {exc}") from exc
    return claims


def load_claims_json(path: str | Path) -> list[Claim]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("JSON claim file must contain a list")
    return [Claim.model_validate(item) for item in payload]
