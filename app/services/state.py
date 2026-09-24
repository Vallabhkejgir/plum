from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.models import ClaimRecord, ProcessingStatus, RuleOutcome, ServiceResponse, ServiceStatus, TraceEvent
from app.core.policy import PolicyView


@dataclass
class PipelineState:
    record: ClaimRecord
    policy: PolicyView
    confidence: float = 0.96
    member: dict[str, Any] | None = None
    matched_patient: dict[str, Any] | None = None
    notes: list[str] = field(default_factory=list)
    blocked: bool = False

    def add_trace(
        self,
        step: str,
        agent: str,
        response: ServiceResponse,
        summary: str,
    ) -> None:
        self.confidence = min(0.99, max(0.05, self.confidence + response.confidence_delta))
        self.record.trace.append(
            TraceEvent(
                step=step,
                agent=agent,
                status=response.status,
                summary=summary,
                details=response.artifacts,
                warnings=response.warnings,
                confidence_delta=response.confidence_delta,
                recoverable_error=response.recoverable_error,
            )
        )
        self.record.updated_at = datetime.utcnow()
        if response.status == ServiceStatus.BLOCKED:
            self.blocked = True
            self.record.status = ProcessingStatus.BLOCKED
            self.record.member_message = response.blocking_message

    def add_rule(self, outcome: RuleOutcome) -> None:
        self.record.rule_outcomes.append(outcome)
        self.record.updated_at = datetime.utcnow()
