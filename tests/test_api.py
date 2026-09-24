from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.pipeline import ClaimsPipeline
from app.storage.repository import ClaimsRepository


def test_manifest_only_claim_submission(tmp_path: Path):
    repository = ClaimsRepository(tmp_path / "claims.db")
    app.state.repository = repository
    app.state.pipeline = ClaimsPipeline(repository)
    client = TestClient(app)

    manifest = [
        {
            "file_id": "F007",
            "actual_type": "PRESCRIPTION",
            "content": {
                "doctor_name": "Dr. Arun Sharma",
                "doctor_registration": "KA/45678/2015",
                "patient_name": "Rajesh Kumar",
                "date": "2024-11-01",
                "diagnosis": "Viral Fever"
            }
        },
        {
            "file_id": "F008",
            "actual_type": "HOSPITAL_BILL",
            "content": {
                "hospital_name": "City Clinic, Bengaluru",
                "patient_name": "Rajesh Kumar",
                "date": "2024-11-01",
                "line_items": [
                    {"description": "Consultation Fee", "amount": 1000},
                    {"description": "CBC Test", "amount": 300},
                    {"description": "Dengue NS1 Test", "amount": 200}
                ],
                "total": 1500
            }
        }
    ]
    response = client.post(
        "/api/claims",
        data={
            "member_id": "EMP001",
            "policy_id": "PLUM_GHI_2024",
            "claim_category": "CONSULTATION",
            "treatment_date": "2024-11-01",
            "claimed_amount": "1500",
            "documents_manifest": json.dumps(manifest)
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "COMPLETED"
    assert payload["decision"]["decision"] == "APPROVED"

    detail = client.get(f"/api/claims/{payload['claim_id']}")
    assert detail.status_code == 200
    assert detail.json()["decision"]["approved_amount"] == 1350.0
