export type ApiClaimSummary = {
  claim_id: string;
  status: string;
  member_message: string | null;
  decision: ApiDecision | null;
};

export type ApiDecision = {
  decision: string | null;
  approved_amount: number;
  confidence_score: number;
  reason: string;
  notes: string[];
  rejection_reasons: string[];
  line_items: Array<{
    description: string;
    claimed_amount: number;
    approved_amount: number;
    status: string;
    reason: string;
  }>;
  manual_review_recommended: boolean;
};

export type ApiClaimRecord = {
  claim_id: string;
  status: string;
  member_message: string | null;
  submission: Record<string, unknown>;
  decision: ApiDecision | null;
  rule_outcomes: Array<{
    rule_id: string;
    passed: boolean;
    status: string;
    reason: string;
    details: Record<string, unknown>;
    approved_amount_impact?: number | null;
  }>;
  fraud_signals: Array<{
    code: string;
    severity: string;
    description: string;
    details: Record<string, unknown>;
  }>;
  trace: Array<{
    step: string;
    agent: string;
    status: string;
    summary: string;
    details: Record<string, unknown>;
    warnings: string[];
    recoverable_error?: string | null;
    confidence_delta: number;
    timestamp: string;
  }>;
  normalized_documents: Array<{
    file_name: string;
    detected_type: string;
    patient_name?: string | null;
    warnings: string[];
  }>;
};

export type EvalRunResponse = {
  run_id: string;
  started_at: string;
  completed_at: string | null;
  total_cases: number;
  passed_cases: number;
  results: Array<{
    case_id: string;
    case_name: string;
    expected: Record<string, unknown>;
    actual: ApiClaimRecord;
    passed: boolean;
    notes: string[];
  }>;
};

export async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function createClaim(formData: FormData): Promise<ApiClaimSummary> {
  const response = await fetch("/api/claims", {
    method: "POST",
    body: formData
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return (await response.json()) as ApiClaimSummary;
}

export async function fetchClaim(claimId: string): Promise<ApiClaimRecord> {
  return fetchJson<ApiClaimRecord>(`/api/claims/${claimId}`);
}

export async function runEvalSuite(caseIds?: string[]): Promise<EvalRunResponse> {
  const response = await fetch("/api/evals/run", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(caseIds ? { case_ids: caseIds } : {})
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return (await response.json()) as EvalRunResponse;
}
