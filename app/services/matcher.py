from __future__ import annotations

from app.core.models import ServiceResponse, ServiceStatus
from app.services.state import PipelineState
from app.services.utils import normalize_name, relationship_matches_policy


async def run_member_matcher(state: PipelineState) -> ServiceResponse:
    patient_map = {
        artifact.file_name: artifact.patient_name
        for artifact in state.record.normalized_documents
        if artifact.patient_name
    }

    if state.record.submission.simulate_component_failure:
        matched = state.member
        state.matched_patient = matched
        if matched:
            state.record.member_match = {
                **state.record.member_match,
                "matched_patient_id": matched["member_id"],
                "matched_patient_name": matched["name"],
                "match_type": "PRIMARY_MEMBER_PARTIAL_CHECK",
            }
        return ServiceResponse(
            status=ServiceStatus.WARNING,
            warnings=["Secondary consistency-check agent timed out; cross-document identity verification was partially skipped."],
            confidence_delta=-0.18,
            recoverable_error="Consistency-check agent timeout",
            artifacts={
                "matched_patient": matched["name"] if matched else None,
                "partial_patient_map": patient_map,
            },
        )

    unique_names = {
        normalize_name(name): name
        for name in patient_map.values()
        if normalize_name(name)
    }
    if len(unique_names) > 1:
        name_pairs = ", ".join(f"{file_name}: {name}" for file_name, name in patient_map.items())
        return ServiceResponse(
            status=ServiceStatus.BLOCKED,
            blocking_message=(
                f"The uploaded documents do not belong to the same person. "
                f"We found these names: {name_pairs}. Please upload documents for a single patient."
            ),
            confidence_delta=-0.25,
            artifacts={"patient_names": patient_map},
        )

    member = state.member
    dependents = state.policy.get_dependents_for_member(member["member_id"]) if member else []
    allowed_relationships = state.policy.raw["coverage"]["family_floater"]["covered_relationships"]

    if unique_names:
        normalized_target = next(iter(unique_names.keys()))
        if member and normalize_name(member["name"]) == normalized_target:
            state.matched_patient = member
        else:
            for dependent in dependents:
                if (
                    normalize_name(dependent["name"]) == normalized_target
                    and relationship_matches_policy(dependent.get("relationship"), allowed_relationships)
                ):
                    state.matched_patient = dependent
                    break

        if not state.matched_patient:
            return ServiceResponse(
                status=ServiceStatus.BLOCKED,
                blocking_message=(
                    f"The patient name {next(iter(unique_names.values()))} does not match member "
                    f"{member['name']} or an eligible dependent on this policy."
                ),
                confidence_delta=-0.2,
                artifacts={"patient_names": patient_map},
            )
    else:
        state.matched_patient = member

    if state.matched_patient:
        state.record.member_match = {
            **state.record.member_match,
            "matched_patient_id": state.matched_patient["member_id"],
            "matched_patient_name": state.matched_patient["name"],
            "match_type": (
                "PRIMARY_MEMBER"
                if state.matched_patient["member_id"] == member["member_id"]
                else "DEPENDENT"
            ),
        }

    return ServiceResponse(
        status=ServiceStatus.OK,
        artifacts={
            "patient_names": patient_map,
            "matched_patient": state.matched_patient["name"] if state.matched_patient else None,
        },
    )
