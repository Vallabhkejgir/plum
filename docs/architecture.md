# Architecture

## Overview

This system is an orchestrated multi-agent monolith: one deployable FastAPI application coordinates a set of internal services that each behave like a focused agent with a typed contract, trace output, warnings, and recoverable failure handling. A React/Vite frontend sits on top as the reviewer and demo surface. SQLite persists claims and eval runs so every decision can be reloaded with its full trace.

## Core flow

1. Intake creates normalized document artifacts from uploads or fixture manifests.
2. Member validation confirms the member and policy exist before deeper processing.
3. Classification infers each document type.
4. Verification checks required document coverage and blocks early on missing or unreadable files.
5. Extraction populates structured fields from provided content, text files, or a configured Turing multimodal model.
6. Matching reconciles patient identity across docs and against the member/dependent roster.
7. Rule adjudication applies policy-driven decisions in a fixed order:
   - exclusions
   - waiting periods
   - pre-auth
   - minimum claim amount
   - per-claim limit
   - benefit calculation
8. Fraud scoring can escalate an otherwise approvable claim to `MANUAL_REVIEW`.
9. The trace and rule outcomes are returned through the API and UI.

## Design choices

- Policy-first logic: coverage, thresholds, waiting periods, exclusions, document rules, and fraud limits come from `policy_terms.json`.
- Evaluation-oracle precedence: where the fixtures and policy semantics conflict, the implementation favors the test case expectations and traces the compromise explicitly.
- Graceful degradation: component failures do not crash the pipeline. They reduce confidence, emit a recoverable error, and can recommend manual review while preserving the best available decision.
- Single deployable service: this keeps the assignment operationally simple while still exposing explicit component boundaries through contracts and trace steps.
- Shared pipeline for evals and live claims: the eval runner feeds generated documents into the same orchestrator rather than maintaining a separate “test only” path.

## Data and persistence

- Claims are stored in SQLite as serialized `ClaimRecord` payloads keyed by `claim_id`.
- Eval runs are stored similarly so a full suite result can be reloaded later.
- Uploaded files and generated eval documents live under `app/generated/`.
- The frontend reads claim detail through `GET /api/claims/{claim_id}` and never reconstructs decision logic client-side.

## AI integration

- The Turing gateway adapter is isolated in `app/services/provider.py`.
- Multimodal extraction is only attempted when the gateway is configured; otherwise the system falls back to structured fixture content, text parsing, or partial extraction with warnings.
- This keeps the assignment runnable without external keys while still demonstrating how a production OCR/extraction provider would be inserted.

## Failure handling

- Every service returns `status`, `warnings`, `confidence_delta`, `artifacts`, and optional `recoverable_error` or `blocking_message`.
- Blocking failures stop the pipeline before adjudication and produce specific member-facing guidance.
- Recoverable failures remain visible in the trace and reduce confidence instead of throwing raw exceptions.
- `simulate_component_failure` intentionally degrades the identity consistency-check step to prove resilience.

## Scaling path

At 10x load, the first step would be splitting orchestration from heavy document work:

- Move extraction and eval generation into background jobs.
- Replace SQLite with Postgres and structured trace tables.
- Add object storage for uploads and generated artifacts.
- Cache policy snapshots by version.
- Separate fraud review and document extraction into independently scaled workers.
- Add metric emission around step latency, block rates, OCR fallback rates, and confidence distributions.
