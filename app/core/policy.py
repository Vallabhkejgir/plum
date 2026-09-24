from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.models import ClaimCategory, DocumentType
from app.core.settings import get_settings


CATEGORY_TO_POLICY_KEY = {
    ClaimCategory.CONSULTATION: "consultation",
    ClaimCategory.DIAGNOSTIC: "diagnostic",
    ClaimCategory.PHARMACY: "pharmacy",
    ClaimCategory.DENTAL: "dental",
    ClaimCategory.VISION: "vision",
    ClaimCategory.ALTERNATIVE_MEDICINE: "alternative_medicine",
}


DOCUMENT_TYPE_ALIASES = {
    "CONSULTATION": DocumentType.PRESCRIPTION,
    "DIAGNOSTIC": DocumentType.LAB_REPORT,
    "PRESCRIPTION": DocumentType.PRESCRIPTION,
    "HOSPITAL_BILL": DocumentType.HOSPITAL_BILL,
    "LAB_REPORT": DocumentType.LAB_REPORT,
    "DIAGNOSTIC_REPORT": DocumentType.LAB_REPORT,
    "PHARMACY_BILL": DocumentType.PHARMACY_BILL,
    "DENTAL_REPORT": DocumentType.DENTAL_REPORT,
    "DISCHARGE_SUMMARY": DocumentType.DISCHARGE_SUMMARY,
    "PRE_AUTH": DocumentType.PRE_AUTH,
}


WAITING_PERIOD_KEYWORDS = {
    "diabetes": ("diabetes", "type 2 diabetes", "t2dm", "diabetes mellitus"),
    "hypertension": ("hypertension", "htn"),
    "thyroid_disorders": ("thyroid", "hypothyroid", "hyperthyroid"),
    "joint_replacement": ("joint replacement",),
    "maternity": ("maternity", "pregnancy", "delivery"),
    "mental_health": ("mental", "depression", "anxiety", "psychiatric"),
    "obesity_treatment": ("obesity", "bariatric", "weight loss", "diet program"),
    "hernia": ("hernia",),
    "cataract": ("cataract",),
}


@dataclass(frozen=True)
class PolicyView:
    raw: dict[str, Any]

    @property
    def policy_id(self) -> str:
        return self.raw["policy_id"]

    def get_member(self, member_id: str) -> dict[str, Any] | None:
        return next((member for member in self.raw["members"] if member["member_id"] == member_id), None)

    def get_dependents_for_member(self, member_id: str) -> list[dict[str, Any]]:
        return [
            member
            for member in self.raw["members"]
            if member.get("primary_member_id") == member_id
        ]

    def get_category_terms(self, category: ClaimCategory) -> dict[str, Any]:
        return self.raw["opd_categories"][CATEGORY_TO_POLICY_KEY[category]]

    def get_required_documents(self, category: ClaimCategory) -> dict[str, list[DocumentType]]:
        requirements = self.raw["document_requirements"][category.value]
        return {
            key: [DOCUMENT_TYPE_ALIASES[item] for item in values]
            for key, values in requirements.items()
        }

    def is_network_hospital(self, hospital_name: str | None) -> bool:
        if not hospital_name:
            return False
        normalized = hospital_name.casefold().strip()
        return any(item.casefold() == normalized for item in self.raw["network_hospitals"])

    def minimum_claim_amount(self) -> float:
        return float(self.raw["submission_rules"]["minimum_claim_amount"])

    def per_claim_limit(self) -> float:
        return float(self.raw["coverage"]["per_claim_limit"])

    def annual_opd_limit(self) -> float:
        return float(self.raw["coverage"]["annual_opd_limit"])

    def submission_deadline_days(self) -> int:
        return int(self.raw["submission_rules"]["deadline_days_from_treatment"])

    def waiting_period_days(self, clinical_text: str) -> tuple[str | None, int | None]:
        haystack = clinical_text.casefold()
        for key, patterns in WAITING_PERIOD_KEYWORDS.items():
            if any(
                re.search(rf"\b{re.escape(pattern.casefold())}\b", haystack)
                for pattern in patterns
            ):
                return key, int(self.raw["waiting_periods"]["specific_conditions"][key])
        return None, None

    def waiting_period_eligibility_date(self, join_date: str, days: int) -> date:
        return date.fromisoformat(join_date) + timedelta(days=days)

    def exclusion_match(self, clinical_text: str) -> str | None:
        haystack = clinical_text.casefold()
        exclusions = (
            list(self.raw["exclusions"]["conditions"])
            + list(self.raw["exclusions"]["dental_exclusions"])
            + list(self.raw["exclusions"]["vision_exclusions"])
        )
        for exclusion in exclusions:
            if exclusion.casefold() in haystack:
                return exclusion
        if "bariatric" in haystack:
            return "Bariatric surgery"
        if "teeth whitening" in haystack:
            return "Teeth whitening"
        return None

    def fraud_thresholds(self) -> dict[str, Any]:
        return self.raw["fraud_thresholds"]

    def pre_auth_requirement(
        self,
        category: ClaimCategory,
        line_item_descriptions: list[str],
        total_amount: float,
    ) -> tuple[bool, str | None]:
        category_terms = self.get_category_terms(category)
        threshold = float(category_terms.get("pre_auth_threshold", 0))
        high_value_tests = category_terms.get("high_value_tests_requiring_pre_auth", [])
        combined = " ".join(line_item_descriptions).casefold()
        for test in high_value_tests:
            if test.casefold() in combined and total_amount >= threshold:
                return True, test
        if "pet scan" in combined:
            return True, "PET scan"
        return False, None


@lru_cache(maxsize=1)
def load_policy(path: Path | None = None) -> PolicyView:
    settings = get_settings()
    target = path or settings.policy_path
    with target.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return PolicyView(raw=payload)
