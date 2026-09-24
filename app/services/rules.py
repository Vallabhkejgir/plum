from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.core.models import (
    ClaimCategory,
    DecisionLineItem,
    DecisionResult,
    DecisionStatus,
    RuleOutcome,
    ServiceResponse,
    ServiceStatus,
)
from app.services.state import PipelineState
from app.services.utils import collect_clinical_text


def _append_rule(
    state: PipelineState,
    rule_id: str,
    passed: bool,
    reason: str,
    status: ServiceStatus = ServiceStatus.OK,
    details: dict[str, Any] | None = None,
    approved_amount_impact: float | None = None,
) -> None:
    state.add_rule(
        RuleOutcome(
            rule_id=rule_id,
            passed=passed,
            status=status if passed else ServiceStatus.WARNING if status == ServiceStatus.OK else status,
            reason=reason,
            details=details or {},
            approved_amount_impact=approved_amount_impact,
        )
    )


def _get_join_date(state: PipelineState) -> str | None:
    matched = state.matched_patient or state.member
    if matched and matched.get("join_date"):
        return matched["join_date"]
    if matched and matched.get("primary_member_id"):
        primary = state.policy.get_member(matched["primary_member_id"])
        if primary:
            return primary.get("join_date")
    if state.member:
        return state.member.get("join_date")
    return None


def _bill_payload(state: PipelineState) -> dict[str, Any]:
    for artifact in state.record.normalized_documents:
        if artifact.detected_type.value in {"HOSPITAL_BILL", "PHARMACY_BILL"}:
            return artifact.structured_content
    return {}


def _extract_line_items(state: PipelineState) -> list[dict[str, Any]]:
    payload = _bill_payload(state)
    line_items = payload.get("line_items")
    if isinstance(line_items, list) and line_items:
        return line_items
    total = payload.get("total", state.record.submission.claimed_amount)
    return [{"description": "Claim total", "amount": float(total)}]


def _has_pre_auth_document(state: PipelineState) -> bool:
    return any(artifact.detected_type.value == "PRE_AUTH" for artifact in state.record.normalized_documents)


def _soft_limit_warning(state: PipelineState, amount: float) -> None:
    _append_rule(
        state=state,
        rule_id="PER_CLAIM_LIMIT_SOFT_SIGNAL",
        passed=True,
        reason="Per-claim limit traced as a soft signal for this category in v1.",
        details={"claimed_amount": amount, "policy_per_claim_limit": state.policy.per_claim_limit()},
    )


async def run_rule_engine(state: PipelineState) -> ServiceResponse:
    submission = state.record.submission
    clinical_text = collect_clinical_text(
        [artifact.structured_content for artifact in state.record.normalized_documents],
        submission.claim_category,
    )
    line_items = _extract_line_items(state)
    bill_payload = _bill_payload(state)
    total_billed = float(bill_payload.get("total", submission.claimed_amount))
    join_date = _get_join_date(state)

    decision = DecisionResult(
        decision=DecisionStatus.APPROVED,
        approved_amount=0.0,
        confidence_score=state.confidence,
    )

    submission_date = submission.submission_date or submission.treatment_date
    elapsed_days = (submission_date - submission.treatment_date).days
    if elapsed_days > state.policy.submission_deadline_days():
        decision.decision = DecisionStatus.REJECTED
        decision.reason = "Claim was submitted after the allowed submission window."
        decision.rejection_reasons = ["SUBMISSION_DEADLINE_MISSED"]
        _append_rule(
            state,
            "SUBMISSION_DEADLINE",
            False,
            "Claim missed the submission deadline.",
            ServiceStatus.WARNING,
            {"elapsed_days": elapsed_days},
        )
        state.record.decision = decision
        return ServiceResponse(status=ServiceStatus.OK, artifacts={"decision": decision.model_dump(mode="json")})

    _append_rule(
        state,
        "SUBMISSION_DEADLINE",
        True,
        "Claim was submitted within the allowed deadline.",
        details={"elapsed_days": elapsed_days},
    )

    exclusion = state.policy.exclusion_match(clinical_text)
    if exclusion:
        if submission.claim_category == ClaimCategory.DENTAL:
            covered_items: list[DecisionLineItem] = []
            excluded_items: list[DecisionLineItem] = []
            for item in line_items:
                description = item.get("description", "Line item")
                amount = float(item.get("amount", 0))
                if state.policy.exclusion_match(description):
                    excluded_items.append(
                        DecisionLineItem(
                            description=description,
                            claimed_amount=amount,
                            approved_amount=0.0,
                            status=DecisionStatus.REJECTED,
                            reason="Excluded cosmetic dental procedure.",
                        )
                    )
                else:
                    covered_items.append(
                        DecisionLineItem(
                            description=description,
                            claimed_amount=amount,
                            approved_amount=amount,
                            status=DecisionStatus.APPROVED,
                            reason="Covered dental procedure.",
                        )
                    )

            approved_amount = sum(item.approved_amount for item in covered_items)
            decision.line_items = covered_items + excluded_items
            decision.approved_amount = approved_amount
            if approved_amount > 0 and excluded_items:
                decision.decision = DecisionStatus.PARTIAL
                decision.reason = "Covered dental items were approved and cosmetic items were rejected."
                decision.notes.append("Rejected line items were excluded cosmetic dental procedures.")
            else:
                decision.decision = DecisionStatus.REJECTED
                decision.reason = "All billed items were excluded under dental exclusions."
                decision.rejection_reasons = ["EXCLUDED_CONDITION"]

            _append_rule(
                state,
                "EXCLUSION_CHECK",
                approved_amount > 0,
                "Dental exclusions applied at the line-item level.",
                details={"matched_exclusion": exclusion},
                approved_amount_impact=approved_amount,
            )
            state.record.decision = decision
            return ServiceResponse(status=ServiceStatus.OK, artifacts={"decision": decision.model_dump(mode="json")})

        decision.decision = DecisionStatus.REJECTED
        decision.reason = f"Treatment is excluded under the policy: {exclusion}."
        decision.rejection_reasons = ["EXCLUDED_CONDITION"]
        _append_rule(
            state,
            "EXCLUSION_CHECK",
            False,
            "Claim matched a policy exclusion.",
            ServiceStatus.WARNING,
            {"matched_exclusion": exclusion},
        )
        state.record.decision = decision
        return ServiceResponse(status=ServiceStatus.OK, artifacts={"decision": decision.model_dump(mode="json")})

    _append_rule(state, "EXCLUSION_CHECK", True, "No policy exclusions matched this claim.")

    waiting_period_key, waiting_period_days = state.policy.waiting_period_days(clinical_text)
    if join_date:
        join_date_value = date.fromisoformat(join_date)
        initial_eligibility = join_date_value + timedelta(days=state.policy.raw["waiting_periods"]["initial_waiting_period_days"])
        if submission.treatment_date < initial_eligibility:
            decision.decision = DecisionStatus.REJECTED
            decision.reason = (
                f"Initial waiting period applies until {initial_eligibility.isoformat()}."
            )
            decision.rejection_reasons = ["WAITING_PERIOD"]
            _append_rule(
                state,
                "INITIAL_WAITING_PERIOD",
                False,
                "Claim falls within the initial waiting period.",
                ServiceStatus.WARNING,
                {"eligible_from": initial_eligibility.isoformat()},
            )
            state.record.decision = decision
            return ServiceResponse(status=ServiceStatus.OK, artifacts={"decision": decision.model_dump(mode="json")})

        _append_rule(
            state,
            "INITIAL_WAITING_PERIOD",
            True,
            "Initial waiting period has been satisfied.",
            details={"eligible_from": initial_eligibility.isoformat()},
        )

    if waiting_period_key and waiting_period_days and join_date:
        eligibility_date = state.policy.waiting_period_eligibility_date(join_date, waiting_period_days)
        if submission.treatment_date < eligibility_date:
            decision.decision = DecisionStatus.REJECTED
            decision.reason = (
                f"{waiting_period_key.replace('_', ' ').title()} is covered only after {eligibility_date.isoformat()}."
            )
            decision.rejection_reasons = ["WAITING_PERIOD"]
            decision.notes.append(
                f"Eligible for {waiting_period_key.replace('_', ' ')} claims from {eligibility_date.isoformat()}."
            )
            _append_rule(
                state,
                "SPECIFIC_WAITING_PERIOD",
                False,
                "Claim falls within a specific-condition waiting period.",
                ServiceStatus.WARNING,
                {"condition": waiting_period_key, "eligible_from": eligibility_date.isoformat()},
            )
            state.record.decision = decision
            return ServiceResponse(status=ServiceStatus.OK, artifacts={"decision": decision.model_dump(mode="json")})

        _append_rule(
            state,
            "SPECIFIC_WAITING_PERIOD",
            True,
            "Specific-condition waiting period has been satisfied.",
            details={"condition": waiting_period_key, "eligible_from": eligibility_date.isoformat()},
        )

    descriptions = [str(item.get("description", "")) for item in line_items]
    pre_auth_required, matched_test = state.policy.pre_auth_requirement(
        submission.claim_category,
        descriptions,
        total_billed,
    )
    if pre_auth_required and not _has_pre_auth_document(state):
        decision.decision = DecisionStatus.REJECTED
        decision.reason = (
            f"Pre-authorization was required for {matched_test} and was not provided."
        )
        decision.rejection_reasons = ["PRE_AUTH_MISSING"]
        decision.notes.append("Please re-submit this claim with the pre-authorization approval document.")
        _append_rule(
            state,
            "PRE_AUTH_CHECK",
            False,
            "Pre-authorization was required but missing.",
            ServiceStatus.WARNING,
            {"matched_test": matched_test, "total_billed": total_billed},
        )
        state.record.decision = decision
        return ServiceResponse(status=ServiceStatus.OK, artifacts={"decision": decision.model_dump(mode="json")})

    _append_rule(
        state,
        "PRE_AUTH_CHECK",
        True,
        "No unmet pre-authorization requirement was found.",
        details={"matched_test": matched_test},
    )

    if submission.claimed_amount < state.policy.minimum_claim_amount():
        decision.decision = DecisionStatus.REJECTED
        decision.reason = "Claim amount is below the policy minimum claim amount."
        decision.rejection_reasons = ["MINIMUM_CLAIM_AMOUNT"]
        _append_rule(
            state,
            "MINIMUM_CLAIM_AMOUNT",
            False,
            "Claimed amount is below the minimum claim amount.",
            ServiceStatus.WARNING,
            {"claimed_amount": submission.claimed_amount, "minimum": state.policy.minimum_claim_amount()},
        )
        state.record.decision = decision
        return ServiceResponse(status=ServiceStatus.OK, artifacts={"decision": decision.model_dump(mode="json")})

    _append_rule(
        state,
        "MINIMUM_CLAIM_AMOUNT",
        True,
        "Claimed amount is above the minimum claim amount.",
        details={"claimed_amount": submission.claimed_amount},
    )

    if submission.claim_category == ClaimCategory.CONSULTATION and submission.claimed_amount > state.policy.per_claim_limit():
        decision.decision = DecisionStatus.REJECTED
        decision.reason = (
            f"Claimed amount {submission.claimed_amount:.0f} exceeds the per-claim limit "
            f"of {state.policy.per_claim_limit():.0f}."
        )
        decision.rejection_reasons = ["PER_CLAIM_EXCEEDED"]
        _append_rule(
            state,
            "PER_CLAIM_LIMIT",
            False,
            "Consultation claim exceeds the per-claim limit.",
            ServiceStatus.WARNING,
            {"claimed_amount": submission.claimed_amount, "per_claim_limit": state.policy.per_claim_limit()},
        )
        state.record.decision = decision
        return ServiceResponse(status=ServiceStatus.OK, artifacts={"decision": decision.model_dump(mode="json")})

    if submission.claimed_amount > state.policy.per_claim_limit():
        _soft_limit_warning(state, submission.claimed_amount)
    else:
        _append_rule(
            state,
            "PER_CLAIM_LIMIT",
            True,
            "Claim is within the per-claim limit.",
            details={"claimed_amount": submission.claimed_amount, "per_claim_limit": state.policy.per_claim_limit()},
        )

    approved_amount = sum(float(item.get("amount", 0)) for item in line_items)
    if not decision.line_items:
        decision.line_items = [
            DecisionLineItem(
                description=str(item.get("description", "Line item")),
                claimed_amount=float(item.get("amount", 0)),
                approved_amount=float(item.get("amount", 0)),
                status=DecisionStatus.APPROVED,
                reason="Covered under the submitted claim category.",
            )
            for item in line_items
        ]

    category_terms = state.policy.get_category_terms(submission.claim_category)
    hospital_name = submission.hospital_name or bill_payload.get("hospital_name")
    network_discount_percent = float(category_terms.get("network_discount_percent", 0))
    copay_percent = float(category_terms.get("copay_percent", 0))

    if state.policy.is_network_hospital(hospital_name):
        discounted_amount = approved_amount * (1 - network_discount_percent / 100)
        decision.notes.append(
            f"Network discount of {network_discount_percent:.0f}% applied before co-pay."
        )
        _append_rule(
            state,
            "NETWORK_DISCOUNT",
            True,
            "Network discount applied before co-pay.",
            details={"hospital_name": hospital_name, "discount_percent": network_discount_percent},
            approved_amount_impact=discounted_amount,
        )
    else:
        discounted_amount = approved_amount
        _append_rule(
            state,
            "NETWORK_DISCOUNT",
            True,
            "No network discount applied.",
            details={"hospital_name": hospital_name},
            approved_amount_impact=discounted_amount,
        )

    final_amount = discounted_amount * (1 - copay_percent / 100)
    if copay_percent:
        decision.notes.append(f"Co-pay of {copay_percent:.0f}% applied to the discounted amount.")
    _append_rule(
        state,
        "COPAY",
        True,
        "Category co-pay applied.",
        details={"copay_percent": copay_percent},
        approved_amount_impact=final_amount,
    )

    decision.approved_amount = round(final_amount, 2)
    decision.reason = f"Claim approved under {submission.claim_category.value} benefits."

    projected_total = submission.ytd_claims_amount + decision.approved_amount
    if projected_total > state.policy.annual_opd_limit():
        decision.notes.append(
            "Projected year-to-date OPD amount exceeds the annual OPD limit; traced as a soft signal in v1."
        )
        _append_rule(
            state,
            "ANNUAL_OPD_LIMIT_SOFT_SIGNAL",
            True,
            "Annual OPD limit exceeded but only traced as a signal in v1.",
            details={"projected_total": projected_total, "annual_opd_limit": state.policy.annual_opd_limit()},
        )
    else:
        _append_rule(
            state,
            "ANNUAL_OPD_LIMIT",
            True,
            "Claim remains within the annual OPD limit.",
            details={"projected_total": projected_total},
        )

    state.record.decision = decision
    return ServiceResponse(status=ServiceStatus.OK, artifacts={"decision": decision.model_dump(mode="json")})
