from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.core.models import ClaimSubmission, EvalCaseResult, EvalRunResult
from app.core.settings import get_settings
from app.evals.mock_documents import generate_documents
from app.services.pipeline import ClaimsPipeline


def _load_test_cases() -> dict:
    settings = get_settings()
    with settings.test_cases_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _build_submission(case: dict, output_dir: Path) -> ClaimSubmission:
    payload = dict(case["input"])
    payload["documents"] = generate_documents(case["case_id"], output_dir, payload["documents"])
    return ClaimSubmission.model_validate(payload)


def _case_passed(expected: dict, actual: dict) -> tuple[bool, list[str]]:
    notes: list[str] = []
    passed = True

    expected_decision = expected.get("decision")
    actual_decision = actual.get("decision", {}).get("decision") if actual.get("decision") else None
    if expected_decision != actual_decision:
        passed = False
        notes.append(f"Expected decision {expected_decision}, got {actual_decision}.")

    if "approved_amount" in expected and actual.get("decision"):
        approved_amount = round(actual["decision"]["approved_amount"], 2)
        if round(expected["approved_amount"], 2) != approved_amount:
            passed = False
            notes.append(
                f"Expected approved amount {expected['approved_amount']}, got {approved_amount}."
            )

    return passed, notes


def render_eval_markdown(result: EvalRunResult) -> str:
    lines = [
        "# Eval Report",
        "",
        f"- Run ID: `{result.run_id}`",
        f"- Started: `{result.started_at.isoformat()}`",
        f"- Completed: `{result.completed_at.isoformat() if result.completed_at else 'in-progress'}`",
        f"- Passed: `{result.passed_cases}/{result.total_cases}`",
        "",
    ]
    for item in result.results:
        lines.extend(
            [
                f"## {item.case_id} - {item.case_name}",
                "",
                f"- Passed: `{item.passed}`",
                f"- Expected: `{item.expected.get('decision')}`",
                f"- Actual: `{item.actual.decision.decision.value if item.actual.decision and item.actual.decision.decision else None}`",
                f"- Member message: `{item.actual.member_message}`",
                "",
                "### Trace",
                "",
            ]
        )
        for trace in item.actual.trace:
            lines.append(
                f"- `{trace.step}` / `{trace.status.value}`: {trace.summary} | warnings={trace.warnings} | error={trace.recoverable_error}"
            )
        if item.notes:
            lines.extend(["", "### Notes", ""])
            lines.extend([f"- {note}" for note in item.notes])
        lines.append("")
    return "\n".join(lines)


async def run_eval_suite(
    pipeline: ClaimsPipeline,
    case_ids: list[str] | None = None,
) -> EvalRunResult:
    settings = get_settings()
    suite = _load_test_cases()
    selected_cases = [
        case for case in suite["test_cases"] if not case_ids or case["case_id"] in case_ids
    ]

    run_id = f"EVAL_{uuid4().hex[:10].upper()}"
    started_at = datetime.utcnow()
    result = EvalRunResult(
        run_id=run_id,
        started_at=started_at,
        total_cases=len(selected_cases),
    )

    output_dir = settings.eval_dir / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    for case in selected_cases:
        submission = _build_submission(case, output_dir)
        actual = await pipeline.process(submission)
        passed, notes = _case_passed(case["expected"], actual.model_dump(mode="json"))
        result.results.append(
            EvalCaseResult(
                case_id=case["case_id"],
                case_name=case["case_name"],
                expected=case["expected"],
                actual=actual,
                passed=passed,
                notes=notes,
            )
        )
        if passed:
            result.passed_cases += 1

    result.completed_at = datetime.utcnow()
    report_path = settings.root_dir / "docs" / "eval-report.md"
    report_path.write_text(render_eval_markdown(result), encoding="utf-8")
    return result
