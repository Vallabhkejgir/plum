from __future__ import annotations

import pytest

from app.core.models import ClaimCategory, ClaimDocument, ClaimSubmission, DocumentType


async def _process(pipeline, submission: ClaimSubmission):
    return await pipeline.process(submission)


def test_fixture_loader_smoke(load_submission):
    submission = load_submission("TC004")
    assert submission.member_id == "EMP001"
    assert submission.claim_category.value == "CONSULTATION"


@pytest.mark.asyncio
async def test_family_floater_allows_eligible_dependent_name_match(pipeline):
    submission = ClaimSubmission(
        member_id="EMP001",
        policy_id="PLUM_GHI_2024",
        claim_category=ClaimCategory.CONSULTATION,
        treatment_date="2024-11-01",
        claimed_amount=1000,
        documents=[
            ClaimDocument(
                file_name="dep_prescription.png",
                actual_type=DocumentType.PRESCRIPTION,
                content={
                    "patient_name": "Sunita Kumar",
                    "doctor_name": "Dr. Arun Sharma",
                    "diagnosis": "Viral Fever",
                },
            ),
            ClaimDocument(
                file_name="dep_bill.png",
                actual_type=DocumentType.HOSPITAL_BILL,
                content={
                    "patient_name": "Sunita Kumar",
                    "hospital_name": "City Clinic",
                    "total": 1000,
                },
            ),
        ],
    )

    result = await _process(pipeline, submission)

    assert result.status.value == "COMPLETED"
    assert result.member_match["match_type"] == "DEPENDENT"
    assert result.member_match["matched_patient_name"] == "Sunita Kumar"
    assert result.decision is not None
    assert result.decision.decision.value == "APPROVED"


@pytest.mark.asyncio
async def test_network_discount_is_applied_before_copay(pipeline, load_submission):
    result = await _process(pipeline, load_submission("TC010"))

    assert result.decision is not None
    assert result.decision.approved_amount == 3240.0
    assert any("Network discount" in note for note in result.decision.notes)


@pytest.mark.asyncio
async def test_per_claim_limit_rejection_names_limit_and_claim_amount(pipeline, load_submission):
    result = await _process(pipeline, load_submission("TC008"))

    assert result.decision is not None
    assert "7500" in result.decision.reason
    assert "5000" in result.decision.reason
