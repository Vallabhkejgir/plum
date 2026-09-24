from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.core.models import ClaimCategory, DocumentType


TYPE_KEYWORDS = {
    DocumentType.PRESCRIPTION: ("prescription", "rx", "doctor", "medicines"),
    DocumentType.HOSPITAL_BILL: ("bill", "invoice", "receipt", "hospital"),
    DocumentType.LAB_REPORT: ("lab", "diagnostic", "report", "mri", "scan", "cbc"),
    DocumentType.PHARMACY_BILL: ("pharmacy", "medicine bill", "drug", "chemist"),
    DocumentType.DENTAL_REPORT: ("dental report", "x-ray", "odont", "tooth"),
    DocumentType.DISCHARGE_SUMMARY: ("discharge", "summary"),
    DocumentType.PRE_AUTH: ("pre auth", "pre-auth", "authorization"),
}


def normalize_name(value: str | None) -> str:
    if not value:
        return ""
    lowered = value.casefold()
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def relationship_matches_policy(relationship: str | None, allowed_relationships: list[str]) -> bool:
    if not relationship:
        return False
    mapping = {
        "SELF": "SELF",
        "SPOUSE": "SPOUSE",
        "CHILD": "CHILDREN",
        "CHILDREN": "CHILDREN",
        "PARENT": "PARENTS",
        "PARENTS": "PARENTS",
    }
    canonical = mapping.get(relationship.upper(), relationship.upper())
    return canonical in allowed_relationships


def infer_document_type(
    file_name: str,
    content: dict[str, Any] | None = None,
    hinted_type: DocumentType | None = None,
) -> DocumentType:
    if hinted_type:
        return hinted_type

    haystack_parts = [file_name.casefold()]
    if content:
        haystack_parts.append(json.dumps(content).casefold())
    haystack = " ".join(haystack_parts)

    for document_type, keywords in TYPE_KEYWORDS.items():
        if any(keyword in haystack for keyword in keywords):
            return document_type

    return DocumentType.UNKNOWN


def try_load_text_file(file_path: str | None) -> tuple[str | None, dict[str, Any] | None]:
    if not file_path:
        return None, None
    target = Path(file_path)
    if not target.exists() or not target.is_file():
        return None, None

    suffix = target.suffix.lower()
    if suffix not in {".txt", ".md", ".json"}:
        return None, None

    text = target.read_text(encoding="utf-8")
    if suffix == ".json":
        try:
            return text, json.loads(text)
        except json.JSONDecodeError:
            return text, None
    return text, None


def extract_patient_name(content: dict[str, Any]) -> str | None:
    for key in ("patient_name", "patient", "member_name"):
        value = content.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def extract_provider_name(content: dict[str, Any]) -> str | None:
    for key in ("doctor_name", "pathologist_name", "pharmacist_name", "provider_name"):
        value = content.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def extract_hospital_name(content: dict[str, Any]) -> str | None:
    for key in ("hospital_name", "clinic_name", "lab_name", "pharmacy_name"):
        value = content.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def collect_clinical_text(documents: list[dict[str, Any]], category: ClaimCategory) -> str:
    parts: list[str] = [category.value]
    for payload in documents:
        for key in (
            "diagnosis",
            "treatment",
            "tests_ordered",
            "medicines",
            "remarks",
            "covered_items",
        ):
            value = payload.get(key)
            if isinstance(value, list):
                parts.extend(str(item) for item in value)
            elif value:
                parts.append(str(value))

        for line_item in payload.get("line_items", []):
            description = line_item.get("description")
            if description:
                parts.append(str(description))

    return " | ".join(parts)
