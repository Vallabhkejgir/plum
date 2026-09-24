from __future__ import annotations

from app.core.models import ClaimRecord, DocumentArtifact, DocumentQuality, ServiceResponse, ServiceStatus
from app.services.state import PipelineState


async def run_intake(state: PipelineState) -> ServiceResponse:
    artifacts: list[DocumentArtifact] = []
    for index, document in enumerate(state.record.submission.documents, start=1):
        artifacts.append(
            DocumentArtifact(
                document_id=document.file_id or f"DOC_{index:03d}",
                file_name=document.file_name or document.file_id or f"document_{index}.bin",
                submitted_type=document.actual_type,
                mime_type=document.mime_type,
                quality=document.quality or DocumentQuality.UNKNOWN,
                quality_score=1.0 if document.quality != DocumentQuality.UNREADABLE else 0.0,
                structured_content=document.content or {},
                storage_path=document.storage_path,
            )
        )

    state.record.normalized_documents = artifacts
    return ServiceResponse(
        status=ServiceStatus.OK,
        artifacts={"document_count": len(artifacts)},
    )
