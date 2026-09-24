from __future__ import annotations

from app.core.models import DocumentQuality, ServiceResponse, ServiceStatus
from app.services.state import PipelineState


async def run_document_verifier(state: PipelineState) -> ServiceResponse:
    requirements = state.policy.get_required_documents(state.record.submission.claim_category)
    required_types = requirements["required"]
    detected_types = [artifact.detected_type for artifact in state.record.normalized_documents]

    missing = [doc_type for doc_type in required_types if doc_type not in detected_types]
    if missing:
        uploaded = ", ".join(doc_type.value for doc_type in detected_types) or "none"
        needed = ", ".join(doc_type.value for doc_type in missing)
        return ServiceResponse(
            status=ServiceStatus.BLOCKED,
            blocking_message=(
                f"You uploaded {uploaded}, but this {state.record.submission.claim_category.value} claim "
                f"also needs {needed}. Please re-submit with the missing document type."
            ),
            confidence_delta=-0.2,
            artifacts={"uploaded_types": uploaded, "missing_required_types": needed},
        )

    unreadable = [
        artifact.file_name
        for artifact in state.record.normalized_documents
        if artifact.detected_type in required_types and artifact.quality == DocumentQuality.UNREADABLE
    ]
    if unreadable:
        file_name = unreadable[0]
        return ServiceResponse(
            status=ServiceStatus.BLOCKED,
            blocking_message=(
                f"The required document {file_name} could not be read clearly. "
                "Please re-upload a sharper image or PDF of that document."
            ),
            confidence_delta=-0.35,
            artifacts={"unreadable_documents": unreadable},
        )

    return ServiceResponse(
        status=ServiceStatus.OK,
        artifacts={
            "required_types": [doc_type.value for doc_type in required_types],
            "detected_types": [doc_type.value for doc_type in detected_types],
        },
    )
