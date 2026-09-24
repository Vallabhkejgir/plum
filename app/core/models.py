from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ClaimCategory(str, Enum):
    CONSULTATION = "CONSULTATION"
    DIAGNOSTIC = "DIAGNOSTIC"
    PHARMACY = "PHARMACY"
    DENTAL = "DENTAL"
    VISION = "VISION"
    ALTERNATIVE_MEDICINE = "ALTERNATIVE_MEDICINE"


class DocumentType(str, Enum):
    PRESCRIPTION = "PRESCRIPTION"
    HOSPITAL_BILL = "HOSPITAL_BILL"
    LAB_REPORT = "LAB_REPORT"
    PHARMACY_BILL = "PHARMACY_BILL"
    DENTAL_REPORT = "DENTAL_REPORT"
    DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY"
    PRE_AUTH = "PRE_AUTH"
    UNKNOWN = "UNKNOWN"


class ProcessingStatus(str, Enum):
    RECEIVED = "RECEIVED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


class DecisionStatus(str, Enum):
    APPROVED = "APPROVED"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    BLOCKED = "BLOCKED"


class ServiceStatus(str, Enum):
    OK = "OK"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


class DocumentQuality(str, Enum):
    GOOD = "GOOD"
    LOW = "LOW"
    UNREADABLE = "UNREADABLE"
    UNKNOWN = "UNKNOWN"


class ClaimHistoryItem(BaseModel):
    claim_id: str
    date: date
    amount: float
    provider: str | None = None


class ClaimDocument(BaseModel):
    file_id: str | None = None
    file_name: str = ""
    actual_type: DocumentType | None = None
    quality: DocumentQuality | None = None
    patient_name_on_doc: str | None = None
    content: dict[str, Any] | None = None
    mime_type: str | None = None
    storage_path: str | None = None
    source: str = "upload"


class ClaimSubmission(BaseModel):
    claim_id: str | None = None
    member_id: str
    policy_id: str
    claim_category: ClaimCategory
    treatment_date: date
    claimed_amount: float = Field(ge=0)
    ytd_claims_amount: float = Field(default=0, ge=0)
    hospital_name: str | None = None
    claims_history: list[ClaimHistoryItem] = Field(default_factory=list)
    documents: list[ClaimDocument] = Field(default_factory=list)
    submission_date: date | None = None
    simulate_component_failure: bool = False


class DocumentArtifact(BaseModel):
    document_id: str
    file_name: str
    detected_type: DocumentType = DocumentType.UNKNOWN
    submitted_type: DocumentType | None = None
    expected_type: DocumentType | None = None
    mime_type: str | None = None
    quality: DocumentQuality = DocumentQuality.UNKNOWN
    quality_score: float = 1.0
    patient_name: str | None = None
    provider_name: str | None = None
    hospital_name: str | None = None
    extracted_text: str | None = None
    structured_content: dict[str, Any] = Field(default_factory=dict)
    field_confidences: dict[str, float] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    storage_path: str | None = None


class TraceEvent(BaseModel):
    step: str
    agent: str
    status: ServiceStatus
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    confidence_delta: float = 0.0
    recoverable_error: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ServiceResponse(BaseModel):
    status: ServiceStatus
    warnings: list[str] = Field(default_factory=list)
    confidence_delta: float = 0.0
    artifacts: dict[str, Any] = Field(default_factory=dict)
    recoverable_error: str | None = None
    blocking_message: str | None = None


class RuleOutcome(BaseModel):
    rule_id: str
    passed: bool
    status: ServiceStatus
    reason: str
    details: dict[str, Any] = Field(default_factory=dict)
    approved_amount_impact: float | None = None


class FraudSignal(BaseModel):
    code: str
    severity: str
    description: str
    details: dict[str, Any] = Field(default_factory=dict)


class DecisionLineItem(BaseModel):
    description: str
    claimed_amount: float
    approved_amount: float
    status: DecisionStatus
    reason: str


class DecisionResult(BaseModel):
    decision: DecisionStatus | None = None
    approved_amount: float = 0.0
    confidence_score: float = 1.0
    reason: str = ""
    notes: list[str] = Field(default_factory=list)
    rejection_reasons: list[str] = Field(default_factory=list)
    line_items: list[DecisionLineItem] = Field(default_factory=list)
    manual_review_recommended: bool = False


class ClaimRecord(BaseModel):
    claim_id: str
    submission: ClaimSubmission
    status: ProcessingStatus
    normalized_documents: list[DocumentArtifact] = Field(default_factory=list)
    member_match: dict[str, Any] = Field(default_factory=dict)
    rule_outcomes: list[RuleOutcome] = Field(default_factory=list)
    fraud_signals: list[FraudSignal] = Field(default_factory=list)
    trace: list[TraceEvent] = Field(default_factory=list)
    decision: DecisionResult | None = None
    member_message: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EvalCaseResult(BaseModel):
    case_id: str
    case_name: str
    expected: dict[str, Any]
    actual: ClaimRecord
    passed: bool
    notes: list[str] = Field(default_factory=list)


class EvalRunResult(BaseModel):
    run_id: str
    started_at: datetime
    completed_at: datetime | None = None
    total_cases: int = 0
    passed_cases: int = 0
    results: list[EvalCaseResult] = Field(default_factory=list)
