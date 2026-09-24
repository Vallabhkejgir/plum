from __future__ import annotations

from app.core.models import DecisionStatus, FraudSignal, ServiceResponse, ServiceStatus
from app.services.state import PipelineState


async def run_fraud_scorer(state: PipelineState) -> ServiceResponse:
    thresholds = state.policy.fraud_thresholds()
    submission = state.record.submission
    same_day_count = sum(1 for item in submission.claims_history if item.date == submission.treatment_date)
    same_month_count = sum(
        1
        for item in submission.claims_history
        if item.date.year == submission.treatment_date.year and item.date.month == submission.treatment_date.month
    )

    signals: list[FraudSignal] = []
    score = 0.0

    if same_day_count >= thresholds["same_day_claims_limit"]:
        signals.append(
            FraudSignal(
                code="SAME_DAY_CLAIM_SPIKE",
                severity="HIGH",
                description="Member exceeded the same-day claim threshold.",
                details={"prior_same_day_claims": same_day_count, "limit": thresholds["same_day_claims_limit"]},
            )
        )
        score += 0.9

    if same_month_count + 1 > thresholds["monthly_claims_limit"]:
        signals.append(
            FraudSignal(
                code="MONTHLY_CLAIM_SPIKE",
                severity="MEDIUM",
                description="Member exceeded the monthly claim threshold.",
                details={"month_claims_including_current": same_month_count + 1, "limit": thresholds["monthly_claims_limit"]},
            )
        )
        score += 0.45

    if submission.claimed_amount >= thresholds["high_value_claim_threshold"]:
        signals.append(
            FraudSignal(
                code="HIGH_VALUE_CLAIM",
                severity="MEDIUM",
                description="Claim amount exceeds the high-value threshold.",
                details={"claimed_amount": submission.claimed_amount, "threshold": thresholds["high_value_claim_threshold"]},
            )
        )
        score += 0.35

    for artifact in state.record.normalized_documents:
        if any("alteration" in warning.casefold() for warning in artifact.warnings):
            signals.append(
                FraudSignal(
                    code="DOCUMENT_ALTERATION",
                    severity="HIGH",
                    description="Potential alteration was detected in an uploaded document.",
                    details={"file_name": artifact.file_name},
                )
            )
            score += 0.6

    state.record.fraud_signals = signals
    manual_review = score >= thresholds["fraud_score_manual_review_threshold"] or any(
        signal.severity == "HIGH" for signal in signals
    )

    if manual_review and state.record.decision and state.record.decision.decision in {
        DecisionStatus.APPROVED,
        DecisionStatus.PARTIAL,
    }:
        state.record.decision.decision = DecisionStatus.MANUAL_REVIEW
        state.record.decision.manual_review_recommended = True
        state.record.decision.notes.append(
            "Manual review required due to unusual fraud signals."
        )

    return ServiceResponse(
        status=ServiceStatus.WARNING if signals else ServiceStatus.OK,
        warnings=[signal.description for signal in signals],
        confidence_delta=-0.12 if manual_review else 0.0,
        artifacts={
            "fraud_score": round(min(score, 1.0), 2),
            "manual_review": manual_review,
            "signals": [signal.model_dump(mode="json") for signal in signals],
        },
    )
