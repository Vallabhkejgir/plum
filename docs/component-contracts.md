# Component Contracts

## API contracts

### `POST /api/claims`

Accepts `multipart/form-data` with:

- `member_id: str`
- `policy_id: str`
- `claim_category: ClaimCategory`
- `treatment_date: YYYY-MM-DD`
- `claimed_amount: float`
- `ytd_claims_amount?: float`
- `hospital_name?: str`
- `submission_date?: YYYY-MM-DD`
- `simulate_component_failure?: bool`
- `claims_history_json?: JSON array`
- `documents_manifest?: JSON array`
- `files?: UploadFile[]`

Returns:

- `claim_id`
- `status`
- `member_message`
- `decision`

### `GET /api/claims/{claim_id}`

Returns the full persisted `ClaimRecord`, including normalized documents, rule outcomes, fraud signals, member match data, and trace.

### `POST /api/evals/run`

Accepts:

- `case_ids?: string[]`

Returns the full `EvalRunResult` payload and writes `docs/eval-report.md`.

## Core models

### `ClaimSubmission`

Input contract for a claim:

- claim metadata
- optional claim history
- optional hospital context
- one or more `ClaimDocument` items

### `ClaimDocument`

Represents either:

- a real uploaded file with `storage_path`
- a manifest-backed structured document
- a generated eval document

Important fields:

- `actual_type`
- `quality`
- `patient_name_on_doc`
- `content`
- `storage_path`

### `ClaimRecord`

Canonical persisted object:

- `submission`
- `status`
- `normalized_documents`
- `member_match`
- `rule_outcomes`
- `fraud_signals`
- `trace`
- `decision`
- `member_message`

## Service contracts

### Intake agent

Input:

- `ClaimSubmission`

Output:

- `DocumentArtifact[]`
- `document_count`

Failure mode:

- none expected; malformed payloads are rejected before pipeline entry

### Member validation agent

Input:

- `member_id`
- `policy_id`

Output:

- matched primary member
- initial `member_match` payload

Blocking failure:

- unknown member
- unknown policy

### Classifier agent

Input:

- file name
- hinted `actual_type`
- optional structured content

Output:

- detected document type per artifact

Recoverable failure:

- unknown type lowers confidence but does not immediately fail

### Document verifier agent

Input:

- detected document types
- policy document requirements
- document quality

Output:

- required-vs-submitted comparison

Blocking failure:

- missing required document
- unreadable required document

### Extractor agent

Input:

- artifact metadata
- optional structured content
- optional file path

Output:

- structured fields
- extracted text
- field confidences

Recoverable failure:

- OCR/model unavailable
- parse failure on a binary upload

### Matcher agent

Input:

- extracted patient names
- member roster
- family floater rules

Output:

- resolved patient identity
- updated `member_match`

Blocking failure:

- conflicting patient names across documents
- patient does not match member or eligible dependent

Recoverable failure:

- simulated consistency-check timeout

### Rule engine agent

Input:

- normalized documents
- resolved member/patient
- policy terms

Output:

- `DecisionResult`
- `RuleOutcome[]`

Blocking failure:

- none; by this stage the pipeline returns hard decisions rather than intake blocks

### Fraud scorer agent

Input:

- claims history
- claim amount
- artifact warnings

Output:

- `FraudSignal[]`
- possible escalation to `MANUAL_REVIEW`

Recoverable failure:

- none currently; scorer is deterministic

## Error semantics

- `BLOCKED`: stop before a policy decision and show a member-facing correction message.
- `WARNING`: continue, but show degraded trace context and lower confidence.
- `ERROR`: reserved for recoverable internal service failures; the orchestrator should still continue when safe.
- `SKIPPED`: reserved for future optional pipeline branches.
