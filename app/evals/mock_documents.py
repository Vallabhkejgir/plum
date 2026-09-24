from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter

from app.core.models import ClaimDocument, DocumentQuality, DocumentType


def _document_lines(case_id: str, document: dict[str, Any]) -> list[str]:
    lines = [
        f"Case: {case_id}",
        f"Type: {document['actual_type']}",
        f"Source file: {document.get('file_name', 'generated.png')}",
    ]
    if document.get("patient_name_on_doc"):
        lines.append(f"Patient: {document['patient_name_on_doc']}")
    content = document.get("content", {})
    if content:
        for key, value in content.items():
            if isinstance(value, list):
                lines.append(f"{key}: {', '.join(str(item) for item in value)}")
            else:
                lines.append(f"{key}: {value}")
    return lines


def _render_document(target: Path, lines: list[str], quality: DocumentQuality) -> None:
    image = Image.new("RGB", (1200, 1600), "white")
    draw = ImageDraw.Draw(image)
    y = 70
    for line in lines:
        wrapped = textwrap.wrap(line, width=70) or [""]
        for chunk in wrapped:
            draw.text((70, y), chunk, fill="black")
            y += 34
        y += 12

    if quality == DocumentQuality.LOW:
        image = image.filter(ImageFilter.GaussianBlur(radius=1.5))
    elif quality == DocumentQuality.UNREADABLE:
        image = image.filter(ImageFilter.GaussianBlur(radius=9))

    image.save(target)


def generate_documents(case_id: str, target_dir: Path, fixtures: list[dict[str, Any]]) -> list[ClaimDocument]:
    target_dir.mkdir(parents=True, exist_ok=True)
    documents: list[ClaimDocument] = []

    for index, fixture in enumerate(fixtures, start=1):
        quality = DocumentQuality(fixture.get("quality", "GOOD"))
        file_name = fixture.get("file_name") or f"{case_id.lower()}_{index}.png"
        if Path(file_name).suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            output_name = f"{Path(file_name).stem}.png"
        else:
            output_name = file_name
        storage_path = target_dir / output_name
        _render_document(storage_path, _document_lines(case_id, fixture), quality)

        documents.append(
            ClaimDocument(
                file_id=fixture.get("file_id"),
                file_name=output_name,
                actual_type=DocumentType(fixture["actual_type"]),
                quality=quality,
                patient_name_on_doc=fixture.get("patient_name_on_doc"),
                content=fixture.get("content"),
                mime_type="image/png",
                storage_path=str(storage_path),
                source="fixture",
            )
        )

    return documents
