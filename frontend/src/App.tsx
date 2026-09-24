import { startTransition, useEffect, useState } from "react";

import { ClaimForm } from "./components/ClaimForm";
import { DecisionView } from "./components/DecisionView";
import { EvalDashboard } from "./components/EvalDashboard";
import { TraceView } from "./components/TraceView";
import { ApiClaimRecord, EvalRunResponse, createClaim, fetchClaim, fetchJson, runEvalSuite } from "./lib/api";

type AssignmentCase = {
  case_id: string;
  case_name: string;
  description: string;
  input: Record<string, unknown>;
};

type FormFields = {
  memberId: string;
  policyId: string;
  claimCategory: string;
  treatmentDate: string;
  claimedAmount: string;
  ytdClaimsAmount: string;
  hospitalName: string;
  claimsHistoryJson: string;
  simulateComponentFailure: boolean;
};

const defaultFields: FormFields = {
  memberId: "EMP001",
  policyId: "PLUM_GHI_2024",
  claimCategory: "CONSULTATION",
  treatmentDate: "2024-11-01",
  claimedAmount: "1500",
  ytdClaimsAmount: "0",
  hospitalName: "",
  claimsHistoryJson: "[]",
  simulateComponentFailure: false
};

export function App() {
  const [policy, setPolicy] = useState<Record<string, unknown> | null>(null);
  const [cases, setCases] = useState<AssignmentCase[]>([]);
  const [fields, setFields] = useState<FormFields>(defaultFields);
  const [manifest, setManifest] = useState("[]");
  const [claim, setClaim] = useState<ApiClaimRecord | null>(null);
  const [evalRun, setEvalRun] = useState<EvalRunResponse | null>(null);
  const [busyClaim, setBusyClaim] = useState(false);
  const [busyEval, setBusyEval] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);

  useEffect(() => {
    async function loadBootstrap() {
      try {
        const [policyPayload, casesPayload] = await Promise.all([
          fetchJson<Record<string, unknown>>("/api/policy"),
          fetchJson<{ test_cases: AssignmentCase[] }>("/api/test-cases")
        ]);
        setPolicy(policyPayload);
        setCases(casesPayload.test_cases);
      } catch (error) {
        setFlash(error instanceof Error ? error.message : "Failed to load bootstrap data.");
      }
    }
    void loadBootstrap();
  }, []);

  function loadCase(caseId: string) {
    const selected = cases.find((item) => item.case_id === caseId);
    if (!selected) {
      return;
    }
    const input = selected.input;
    startTransition(() => {
      setFields({
        memberId: String(input.member_id ?? ""),
        policyId: String(input.policy_id ?? ""),
        claimCategory: String(input.claim_category ?? "CONSULTATION"),
        treatmentDate: String(input.treatment_date ?? ""),
        claimedAmount: String(input.claimed_amount ?? ""),
        ytdClaimsAmount: String(input.ytd_claims_amount ?? "0"),
        hospitalName: String(input.hospital_name ?? ""),
        claimsHistoryJson: JSON.stringify(input.claims_history ?? [], null, 2),
        simulateComponentFailure: Boolean(input.simulate_component_failure)
      });
      setManifest(JSON.stringify(input.documents ?? [], null, 2));
      setFlash(`Loaded ${selected.case_id} into the submission form.`);
    });
  }

  async function handleSubmit(formData: FormData) {
    setBusyClaim(true);
    setFlash(null);
    try {
      const summary = await createClaim(formData);
      const record = await fetchClaim(summary.claim_id);
      setClaim(record);
      setFlash(`Processed ${summary.claim_id} with status ${summary.status}.`);
    } catch (error) {
      setFlash(error instanceof Error ? error.message : "Claim submission failed.");
    } finally {
      setBusyClaim(false);
    }
  }

  async function handleRunAllEvals() {
    setBusyEval(true);
    setFlash(null);
    try {
      const run = await runEvalSuite();
      setEvalRun(run);
      setFlash(`Eval suite complete: ${run.passed_cases}/${run.total_cases} passed.`);
    } catch (error) {
      setFlash(error instanceof Error ? error.message : "Eval run failed.");
    } finally {
      setBusyEval(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="hero">
        <div>
          <p className="eyebrow">Plum Claims Pipeline Showcase</p>
          <h1>Reliable, explainable health-claim adjudication with an agent-style trace.</h1>
          <p className="hero-copy">
            Submit real uploads, replay the assignment fixtures, or run the full 12-case evaluation from one place.
          </p>
        </div>
        <div className="hero-stat-stack">
          <article>
            <span>Policy</span>
            <strong>{String(policy?.policy_id ?? "Loading…")}</strong>
          </article>
          <article>
            <span>Cases loaded</span>
            <strong>{cases.length || "…"}</strong>
          </article>
          <article>
            <span>Latest claim</span>
            <strong>{claim?.claim_id ?? "None yet"}</strong>
          </article>
        </div>
      </section>

      {flash ? <div className="flash-banner">{flash}</div> : null}

      <section className="grid-primary">
        <ClaimForm
          busy={busyClaim}
          cases={cases}
          initialFields={fields}
          initialManifest={manifest}
          onLoadCase={loadCase}
          onSubmit={handleSubmit}
        />
        <DecisionView claim={claim} />
      </section>

      <section className="grid-secondary">
        <TraceView claim={claim} />
        <EvalDashboard busy={busyEval} evalRun={evalRun} onRunAll={handleRunAllEvals} />
      </section>
    </main>
  );
}
