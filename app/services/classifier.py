from __future__ import annotations

from app.core.models import ServiceResponse, ServiceStatus
from app.services.state import PipelineState
from app.services.utils import infer_document_type


async def run_classifier(state: PipelineState) -> ServiceResponse:
    unknown_files: list[str] = []
    for artifact in state.record.normalized_documents:
        artifact.detected_type = infer_document_type(
            file_name=artifact.file_name,
            content=artifact.structured_content,
            hinted_type=artifact.submitted_type,
        )
        if artifact.detected_type.value == "UNKNOWN":
            unknown_files.append(artifact.file_name)

    status = ServiceStatus.WARNING if unknown_files else ServiceStatus.OK
    warnings = (
        [f"Could not confidently classify: {', '.join(unknown_files)}"]
        if unknown_files
        else []
    )
    return ServiceResponse(
        status=status,
        warnings=warnings,
        confidence_delta=-0.05 if unknown_files else 0.0,
        artifacts={
            "classified_documents": {
                artifact.file_name: artifact.detected_type.value
                for artifact in state.record.normalized_documents
            }
        },
    )
