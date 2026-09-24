from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel

from app.core.models import ClaimDocument, ClaimHistoryItem, ClaimSubmission, ClaimCategory, DocumentQuality, DocumentType
from app.evals.runner import run_eval_suite
from app.services.pipeline import ClaimsPipeline
from app.storage.repository import ClaimsRepository


router = APIRouter(prefix="/api")


class EvalRunRequest(BaseModel):
    case_ids: list[str] | None = None


def _repository(request: Request) -> ClaimsRepository:
    return request.app.state.repository


def _pipeline(request: Request) -> ClaimsPipeline:
    return request.app.state.pipeline


def _settings(request: Request):
    return request.app.state.settings


def _parse_documents_manifest(raw_manifest: str | None) -> list[dict[str, Any]]:
    if not raw_manifest:
        return []
    try:
        payload = json.loads(raw_manifest)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid documents manifest JSON: {exc}") from exc
    if not isinstance(payload, list):
        raise HTTPException(status_code=400, detail="documents_manifest must be a JSON array.")
    return payload


def _parse_claim_history(raw_history: str | None) -> list[ClaimHistoryItem]:
    if not raw_history:
        return []
    try:
        payload = json.loads(raw_history)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid claims history JSON: {exc}") from exc
    if not isinstance(payload, list):
        raise HTTPException(status_code=400, detail="claims_history_json must be a JSON array.")
    return [ClaimHistoryItem.model_validate(item) for item in payload]


async def _save_upload(request: Request, upload: UploadFile) -> str:
    settings = _settings(request)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload.filename or "upload.bin").suffix
    file_name = f"{uuid4().hex}{suffix}"
    target = settings.upload_dir / file_name
    content = await upload.read()
    target.write_bytes(content)
    return str(target)


@router.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/policy")
async def policy_summary(request: Request) -> dict[str, Any]:
    pipeline = _pipeline(request)
    return pipeline.policy.raw


@router.get("/test-cases")
async def test_cases(request: Request) -> dict[str, Any]:
    settings = _settings(request)
    return json.loads(settings.test_cases_path.read_text(encoding="utf-8"))


@router.post("/claims")
async def create_claim(
    request: Request,
    member_id: str = Form(...),
    policy_id: str = Form(...),
    claim_category: ClaimCategory = Form(...),
    treatment_date: date = Form(...),
    claimed_amount: float = Form(...),
    ytd_claims_amount: float = Form(0),
    hospital_name: str | None = Form(None),
    submission_date: date | None = Form(None),
    simulate_component_failure: bool = Form(False),
    claims_history_json: str | None = Form(None),
    documents_manifest: str | None = Form(None),
    files: list[UploadFile] | None = File(default=None),
) -> dict[str, Any]:
    manifest = _parse_documents_manifest(documents_manifest)
    manifest_by_name = {item.get("file_name"): item for item in manifest}
    documents: list[ClaimDocument] = []

    for upload in files or []:
        storage_path = await _save_upload(request, upload)
        entry = manifest_by_name.get(upload.filename, {})
        documents.append(
            ClaimDocument(
                file_id=entry.get("file_id"),
                file_name=upload.filename or Path(storage_path).name,
                actual_type=DocumentType(entry["actual_type"]) if entry.get("actual_type") else None,
                quality=DocumentQuality(entry["quality"]) if entry.get("quality") else None,
                patient_name_on_doc=entry.get("patient_name_on_doc"),
                content=entry.get("content"),
                mime_type=upload.content_type,
                storage_path=storage_path,
                source="upload",
            )
        )

    for entry in manifest:
        if entry.get("file_name") not in {document.file_name for document in documents}:
            documents.append(
                ClaimDocument(
                    file_id=entry.get("file_id"),
                    file_name=entry.get("file_name", f"{uuid4().hex}.json"),
                    actual_type=DocumentType(entry["actual_type"]) if entry.get("actual_type") else None,
                    quality=DocumentQuality(entry["quality"]) if entry.get("quality") else None,
                    patient_name_on_doc=entry.get("patient_name_on_doc"),
                    content=entry.get("content"),
                    mime_type=entry.get("mime_type"),
                    storage_path=entry.get("storage_path"),
                    source="manifest",
                )
            )

    if not documents:
        raise HTTPException(status_code=400, detail="At least one document is required.")

    submission = ClaimSubmission(
        member_id=member_id,
        policy_id=policy_id,
        claim_category=claim_category,
        treatment_date=treatment_date,
        claimed_amount=claimed_amount,
        ytd_claims_amount=ytd_claims_amount,
        hospital_name=hospital_name,
        claims_history=_parse_claim_history(claims_history_json),
        documents=documents,
        submission_date=submission_date,
        simulate_component_failure=simulate_component_failure,
    )
    pipeline = _pipeline(request)
    record = await pipeline.process(submission)
    return {
        "claim_id": record.claim_id,
        "status": record.status.value,
        "member_message": record.member_message,
        "decision": record.decision.model_dump(mode="json") if record.decision else None,
    }


@router.get("/claims/{claim_id}")
async def get_claim(claim_id: str, request: Request) -> dict[str, Any]:
    repository = _repository(request)
    record = repository.get_claim(claim_id)
    if not record:
        raise HTTPException(status_code=404, detail="Claim not found.")
    return record.model_dump(mode="json")


@router.post("/evals/run")
async def run_evals(request: Request, payload: EvalRunRequest | None = None) -> dict[str, Any]:
    pipeline = _pipeline(request)
    repository = _repository(request)
    result = await run_eval_suite(pipeline=pipeline, case_ids=payload.case_ids if payload else None)
    repository.save_eval_run(result)
    return result.model_dump(mode="json")


@router.get("/evals/{run_id}")
async def get_eval(run_id: str, request: Request) -> dict[str, Any]:
    repository = _repository(request)
    result = repository.get_eval_run(run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Eval run not found.")
    return result
