from __future__ import annotations

import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case_id", "expected_status", "expected_decision", "expected_amount", "message_fragment"),
    [
        ("TC001", "BLOCKED", None, None, "needs HOSPITAL_BILL"),
        ("TC002", "BLOCKED", None, None, "could not be read clearly"),
        ("TC003", "BLOCKED", None, None, "do not belong to the same person"),
        ("TC004", "COMPLETED", "APPROVED", 1350.0, None),
        ("TC005", "COMPLETED", "REJECTED", 0.0, None),
        ("TC006", "COMPLETED", "PARTIAL", 8000.0, None),
        ("TC007", "COMPLETED", "REJECTED", 0.0, None),
        ("TC008", "COMPLETED", "REJECTED", 0.0, None),
        ("TC009", "COMPLETED", "MANUAL_REVIEW", 4320.0, None),
        ("TC010", "COMPLETED", "APPROVED", 3240.0, None),
        ("TC011", "COMPLETED", "APPROVED", 4000.0, None),
        ("TC012", "COMPLETED", "REJECTED", 0.0, None),
    ],
)
async def test_assignment_cases_match_expected_decisions(
    pipeline,
    load_submission,
    case_id,
    expected_status,
    expected_decision,
    expected_amount,
    message_fragment,
):
    result = await pipeline.process(load_submission(case_id))

    assert result.status.value == expected_status
    if expected_decision is None:
        assert result.decision is None
        assert message_fragment in (result.member_message or "")
    else:
        assert result.decision is not None
        assert result.decision.decision.value == expected_decision
        assert round(result.decision.approved_amount, 2) == expected_amount


@pytest.mark.asyncio
async def test_waiting_period_rejection_surfaces_eligibility_date(pipeline, load_submission):
    result = await pipeline.process(load_submission("TC005"))

    assert result.decision is not None
    assert "2024-11-30" in " ".join(result.decision.notes)


@pytest.mark.asyncio
async def test_dental_partial_approval_itemizes_approved_and_rejected_items(pipeline, load_submission):
    result = await pipeline.process(load_submission("TC006"))

    assert result.decision is not None
    line_items = {item.description: item for item in result.decision.line_items}
    assert line_items["Root Canal Treatment"].approved_amount == 8000
    assert line_items["Teeth Whitening"].approved_amount == 0
    assert "cosmetic" in line_items["Teeth Whitening"].reason.casefold()


@pytest.mark.asyncio
async def test_graceful_degradation_marks_manual_review_recommendation(pipeline, load_submission):
    result = await pipeline.process(load_submission("TC011"))

    assert result.decision is not None
    assert result.decision.manual_review_recommended is True
    assert any(trace.recoverable_error for trace in result.trace)
