from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.models import DocumentQuality, ServiceResponse, ServiceStatus
from app.core.settings import get_settings
from app.services.provider import TuringGatewayClient
from app.services.state import PipelineState
from app.services.utils import (
    extract_hospital_name,
    extract_patient_name,
    extract_provider_name,
    try_load_text_file,
)


def _build_prompt(document_type: str) -> str:
    return (
        "Extract claim-relevant fields from this medical document. "
        f"The detected type is {document_type}. "
        "Return JSON only with keys like patient_name, doctor_name, hospital_name, date, "
        "diagnosis, treatment, line_items, total, tests_ordered, medicines, remarks, and any registration numbers."
    )


async def _extract_from_path(
    gateway: TuringGatewayClient,
    storage_path: str | None,
    detected_type: str,
) -> tuple[dict[str, Any], str | None]:
    if not storage_path:
        return {}, None

    raw_text, json_payload = try_load_text_file(storage_path)
    if json_payload is not None:
        return json_payload, raw_text
    if raw_text is not None:
        return {"raw_text": raw_text}, raw_text

    if not gateway.configured:
        raise RuntimeError("OCR provider is not configured for binary uploads.")
    result = await gateway.extract_document(Path(storage_path), _build_prompt(detected_type))
    return result.content, result.raw_text


async def run_extractor(state: PipelineState) -> ServiceResponse:
    settings = get_settings()
    gateway = TuringGatewayClient(settings)
    warnings: list[str] = []
    confidence_delta = 0.0

    for source_document, artifact in zip(
        state.record.submission.documents,
        state.record.normalized_documents,
        strict=False,
    ):
        content = source_document.content or {}
        raw_text = None

        if artifact.quality == DocumentQuality.UNREADABLE:
            artifact.warnings.append("Document marked unreadable.")
            confidence_delta -= 0.15
            continue

        if not content:
            try:
                content, raw_text = await _extract_from_path(
                    gateway=gateway,
                    storage_path=artifact.storage_path,
                    detected_type=artifact.detected_type.value,
                )
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"{artifact.file_name}: {exc}")
                artifact.warnings.append(str(exc))
                confidence_delta -= 0.12
                content = {}

        if source_document.patient_name_on_doc and "patient_name" not in content:
            content["patient_name"] = source_document.patient_name_on_doc

        if not content and artifact.submitted_type is not None:
            content["document_type"] = artifact.submitted_type.value

        artifact.structured_content = content
        artifact.extracted_text = raw_text or json.dumps(content, ensure_ascii=True)
        artifact.patient_name = extract_patient_name(content)
        artifact.provider_name = extract_provider_name(content)
        artifact.hospital_name = extract_hospital_name(content)
        artifact.field_confidences = {
            key: (0.98 if artifact.quality in {DocumentQuality.GOOD, DocumentQuality.UNKNOWN} else 0.78)
            for key in content.keys()
        }
        if artifact.quality == DocumentQuality.LOW:
            artifact.warnings.append("Low-quality image; extracted fields may be incomplete.")
            confidence_delta -= 0.08

    status = ServiceStatus.WARNING if warnings else ServiceStatus.OK
    return ServiceResponse(
        status=status,
        warnings=warnings,
        confidence_delta=confidence_delta,
        recoverable_error="; ".join(warnings) if warnings else None,
        artifacts={
            "extracted_documents": {
                artifact.file_name: list(artifact.structured_content.keys())
                for artifact in state.record.normalized_documents
            }
        },
    )
