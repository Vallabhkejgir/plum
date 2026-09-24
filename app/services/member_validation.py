from __future__ import annotations

from app.core.models import ServiceResponse, ServiceStatus
from app.services.state import PipelineState


async def run_member_validation(state: PipelineState) -> ServiceResponse:
    submission = state.record.submission
    if submission.policy_id != state.policy.policy_id:
        return ServiceResponse(
            status=ServiceStatus.BLOCKED,
            blocking_message=(
                f"Policy {submission.policy_id} is not available. "
                f"Please submit this claim under policy {state.policy.policy_id}."
            ),
            confidence_delta=-0.25,
            artifacts={"submitted_policy_id": submission.policy_id},
        )

    member = state.policy.get_member(submission.member_id)
    if not member:
        return ServiceResponse(
            status=ServiceStatus.BLOCKED,
            blocking_message=(
                f"Member ID {submission.member_id} was not found in policy {state.policy.policy_id}. "
                "Please check the employee ID and try again."
            ),
            confidence_delta=-0.25,
            artifacts={"member_id": submission.member_id},
        )

    state.member = member
    state.record.member_match = {
        "submitted_member_id": submission.member_id,
        "policy_member_name": member["name"],
        "matched_member_id": member["member_id"],
        "matched_member_name": member["name"],
        "match_type": "PRIMARY_MEMBER",
    }
    return ServiceResponse(
        status=ServiceStatus.OK,
        artifacts={
            "member_id": submission.member_id,
            "member_name": member["name"],
            "relationship": member["relationship"],
        },
    )
