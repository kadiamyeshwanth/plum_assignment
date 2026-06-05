"""
Pydantic models for the Plum OPD Adjudication API.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Any, Dict, List, Optional, Union
from datetime import datetime


class Prescription(BaseModel):
    doctor_name: Optional[str] = None
    doctor_reg: Optional[str] = None
    diagnosis: Optional[str] = None
    medicines_prescribed: Optional[List[str]] = None
    tests_prescribed: Optional[List[str]] = None
    tests: Optional[List[str]] = None
    procedures: Optional[List[str]] = None
    treatment: Optional[str] = None


class Documents(BaseModel):
    prescription: Optional[Dict[str, Any]] = None
    bill: Optional[Dict[str, Any]] = None
    reports: Optional[Dict[str, Any]] = None


class ClaimRequest(BaseModel):
    case_id: str = Field(default="CLM_XXXXX", description="Unique claim identifier")
    member_id: Optional[str] = None
    member_name: Optional[str] = None
    claim_amount: float = Field(..., gt=0, description="Total claimed amount in INR")
    treatment_date: str = Field(..., description="Date of treatment (YYYY-MM-DD)")
    member_join_date: Optional[str] = Field(None, description="Policy start date (YYYY-MM-DD)")
    hospital: Optional[str] = None
    cashless_request: bool = False
    previous_claims_same_day: int = Field(default=0, ge=0)
    pre_auth_obtained: bool = False
    documents: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("treatment_date", "member_join_date", mode="before")
    @classmethod
    def validate_dates(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError(f"Invalid date format. Expected YYYY-MM-DD, got: {v}")
        return v


class ExtractionResult(BaseModel):
    extracted_fields: Dict[str, Any] = Field(default_factory=dict)
    validation_flags: List[str] = Field(default_factory=list)
    doctor_reg_valid: bool = True
    documents_complete: bool = True
    extraction_confidence: float = Field(default=0.95, ge=0.0, le=1.0)


class AdjudicationResult(BaseModel):
    claim_id: str
    decision: str  # APPROVED | REJECTED | PARTIAL | MANUAL_REVIEW
    approved_amount: float = 0
    rejection_reasons: List[str] = Field(default_factory=list)
    rejected_items: List[str] = Field(default_factory=list)
    confidence_score: float = Field(default=0.9, ge=0.0, le=1.0)
    notes: str = ""
    next_steps: str = ""
    deductions: Optional[Dict[str, Any]] = None
    network_discount: Optional[float] = None
    flags: Optional[List[str]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    # Extraction metadata
    extraction: Optional[ExtractionResult] = None
