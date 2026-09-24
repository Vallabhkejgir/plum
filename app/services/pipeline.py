from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.core.models import ClaimRecord, ClaimSubmission, ProcessingStatus
from app.core.policy import load_policy
from app.storage.repository import ClaimsRepository
from app.services.classifier import run_classifier
from app.services.extractor import run_extractor
from app.services.fraud import run_fraud_scorer
from app.services.intake import run_intake
from app.services.matcher import run_member_matcher
from app.services.member_validation import run_member_validation
from app.services.rules import run_rule_engine
from app.services.state import PipelineState
from app.services.verifier import run_document_verifier


class ClaimsPipeline:
    def __init__(self, repository: ClaimsRepository) -> None:
        self.repository = repository
        self.policy = load_policy()

    async def process(self, submission: ClaimSubmission) -> ClaimRecord:
        claim_id = submission.claim_id or f"CLM_{uuid4().hex[:10].upper()}"
        submission.claim_id = claim_id
        record = ClaimRecord(
            claim_id=claim_id,
            submission=submission,
            status=ProcessingStatus.PROCESSING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.repository.save_claim(record)

        state = PipelineState(record=record, policy=self.policy)

        for step, agent, runner, summary in [
            ("intake", "intake-agent", run_intake, "Claim intake completed."),
            ("member_validation", "member-agent", run_member_validation, "Policy and member validation completed."),
            ("classification", "classifier-agent", run_classifier, "Document classification completed."),
            ("verification", "verifier-agent", run_document_verifier, "Document requirement verification completed."),
            ("extraction", "extractor-agent", run_extractor, "Document extraction completed."),
            ("matching", "matcher-agent", run_member_matcher, "Patient normalization and matching completed."),
            ("rules", "adjudicator-agent", run_rule_engine, "Policy adjudication completed."),
            ("fraud", "fraud-agent", run_fraud_scorer, "Fraud scoring completed."),
        ]:
            response = await runner(state)
            state.add_trace(step=step, agent=agent, response=response, summary=summary)
            self.repository.save_claim(state.record)
            if state.blocked:
                break

        if state.blocked:
            state.record.status = ProcessingStatus.BLOCKED
        else:
            state.record.status = ProcessingStatus.COMPLETED
            if state.record.decision:
                state.record.decision.confidence_score = round(state.confidence, 2)
                if any(trace.recoverable_error for trace in state.record.trace):
                    state.record.decision.notes.append(
                        "One or more components degraded gracefully during processing."
                    )
                    state.record.decision.notes.append(
                        "Manual review is recommended because part of the processing pipeline was skipped or degraded."
                    )
                    if state.record.decision.decision is not None:
                        state.record.decision.manual_review_recommended = True

        state.record.updated_at = datetime.utcnow()
        self.repository.save_claim(state.record)
        return state.record
