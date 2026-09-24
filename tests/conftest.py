from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.models import ClaimSubmission
from app.core.settings import get_settings
from app.services.pipeline import ClaimsPipeline
from app.storage.repository import ClaimsRepository


@pytest.fixture()
def pipeline(tmp_path: Path) -> ClaimsPipeline:
    return ClaimsPipeline(ClaimsRepository(tmp_path / "claims.db"))


@pytest.fixture()
def test_cases() -> list[dict]:
    settings = get_settings()
    return json.loads(settings.test_cases_path.read_text(encoding="utf-8"))["test_cases"]


@pytest.fixture()
def load_submission(test_cases: list[dict]):
    def _load(case_id: str) -> ClaimSubmission:
        case = next(item for item in test_cases if item["case_id"] == case_id)
        return ClaimSubmission.model_validate(case["input"])

    return _load
