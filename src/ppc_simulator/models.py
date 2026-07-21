"""Domain models for policies, rules, claims, and evaluation results."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class Outcome(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    MANUAL_REVIEW = "manual_review"


class RuleCategory(str, Enum):
    AUTHORIZATION = "authorization"
    MODIFIER = "modifier"
    PLACE_OF_SERVICE = "place_of_service"
    TIMELY_FILING = "timely_filing"


class Rule(BaseModel):
    rule_id: str
    category: RuleCategory
    description: str
    procedure_code: Optional[str] = None
    place_of_service: Optional[str] = None
    modifier_required: Optional[str] = None
    authorization_required: bool = False
    timely_filing_days: Optional[int] = None
    on_match_outcome: Outcome = Outcome.FAIL
    priority: int = Field(default=100, ge=1, le=1000)


class Policy(BaseModel):
    policy_id: str
    payer_name: str
    version: str
    effective_start: date
    effective_end: date
    rules: list[Rule] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dates(self) -> "Policy":
        if self.effective_end < self.effective_start:
            raise ValueError("effective_end must be on or after effective_start")
        rule_ids = [r.rule_id for r in self.rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("duplicate rule_id within policy")
        return self


class Claim(BaseModel):
    claim_id: str
    payer: str
    service_date: date
    submission_date: date
    procedure_code: str
    diagnosis_code: str
    modifier: Optional[str] = None
    place_of_service: str
    authorization_on_file: bool = False

    @field_validator("procedure_code", "diagnosis_code", "place_of_service")
    @classmethod
    def non_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("field must be non-empty")
        return value.strip()


class RuleTrace(BaseModel):
    rule_id: str
    category: RuleCategory
    matched: bool
    explanation: str


class EvaluationResult(BaseModel):
    claim_id: str
    policy_id: str
    policy_version: str
    outcome: Outcome
    explanations: list[str]
    traces: list[RuleTrace]
