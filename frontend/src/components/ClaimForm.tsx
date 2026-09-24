import { FormEvent, useEffect, useState } from "react";

type ClaimFormProps = {
  initialManifest: string;
  initialFields: {
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
  onSubmit: (formData: FormData) => Promise<void>;
  onLoadCase: (caseId: string) => void;
  cases: Array<{ case_id: string; case_name: string; description: string }>;
  busy: boolean;
};

export function ClaimForm({
  initialManifest,
  initialFields,
  onSubmit,
  onLoadCase,
  cases,
  busy
}: ClaimFormProps) {
  const [memberId, setMemberId] = useState(initialFields.memberId);
  const [policyId, setPolicyId] = useState(initialFields.policyId);
  const [claimCategory, setClaimCategory] = useState(initialFields.claimCategory);
  const [treatmentDate, setTreatmentDate] = useState(initialFields.treatmentDate);
  const [claimedAmount, setClaimedAmount] = useState(initialFields.claimedAmount);
  const [ytdClaimsAmount, setYtdClaimsAmount] = useState(initialFields.ytdClaimsAmount);
  const [hospitalName, setHospitalName] = useState(initialFields.hospitalName);
  const [claimsHistoryJson, setClaimsHistoryJson] = useState(initialFields.claimsHistoryJson);
  const [simulateComponentFailure, setSimulateComponentFailure] = useState(
    initialFields.simulateComponentFailure
  );
  const [documentsManifest, setDocumentsManifest] = useState(initialManifest);
  const [files, setFiles] = useState<FileList | null>(null);

  useEffect(() => {
    setMemberId(initialFields.memberId);
    setPolicyId(initialFields.policyId);
    setClaimCategory(initialFields.claimCategory);
    setTreatmentDate(initialFields.treatmentDate);
    setClaimedAmount(initialFields.claimedAmount);
    setYtdClaimsAmount(initialFields.ytdClaimsAmount);
    setHospitalName(initialFields.hospitalName);
    setClaimsHistoryJson(initialFields.claimsHistoryJson);
    setSimulateComponentFailure(initialFields.simulateComponentFailure);
  }, [initialFields]);

  useEffect(() => {
    setDocumentsManifest(initialManifest);
  }, [initialManifest]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData();
    formData.set("member_id", memberId);
    formData.set("policy_id", policyId);
    formData.set("claim_category", claimCategory);
    formData.set("treatment_date", treatmentDate);
    formData.set("claimed_amount", claimedAmount);
    formData.set("ytd_claims_amount", ytdClaimsAmount || "0");
    formData.set("hospital_name", hospitalName);
    formData.set("claims_history_json", claimsHistoryJson);
    formData.set("documents_manifest", documentsManifest);
    formData.set("simulate_component_failure", String(simulateComponentFailure));
    if (files) {
      Array.from(files).forEach((file) => formData.append("files", file));
    }
    await onSubmit(formData);
  }

  return (
    <section className="panel panel-form">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Submission Studio</p>
          <h2>Claim intake with uploads or structured fixtures</h2>
        </div>
        <select
          aria-label="Load test case"
          className="case-picker"
          defaultValue=""
          onChange={(event) => {
            if (event.target.value) {
              onLoadCase(event.target.value);
              event.target.value = "";
            }
          }}
        >
          <option value="">Load assignment case…</option>
          {cases.map((item) => (
            <option key={item.case_id} value={item.case_id}>
              {item.case_id} — {item.case_name}
            </option>
          ))}
        </select>
      </div>

      <form className="claim-form" onSubmit={handleSubmit}>
        <label>
          Member ID
          <input value={memberId} onChange={(event) => setMemberId(event.target.value)} />
        </label>
        <label>
          Policy ID
          <input value={policyId} onChange={(event) => setPolicyId(event.target.value)} />
        </label>
        <label>
          Category
          <select value={claimCategory} onChange={(event) => setClaimCategory(event.target.value)}>
            <option value="CONSULTATION">Consultation</option>
            <option value="DIAGNOSTIC">Diagnostic</option>
            <option value="PHARMACY">Pharmacy</option>
            <option value="DENTAL">Dental</option>
            <option value="VISION">Vision</option>
            <option value="ALTERNATIVE_MEDICINE">Alternative medicine</option>
          </select>
        </label>
        <label>
          Treatment date
          <input type="date" value={treatmentDate} onChange={(event) => setTreatmentDate(event.target.value)} />
        </label>
        <label>
          Claimed amount
          <input value={claimedAmount} onChange={(event) => setClaimedAmount(event.target.value)} />
        </label>
        <label>
          YTD claims amount
          <input value={ytdClaimsAmount} onChange={(event) => setYtdClaimsAmount(event.target.value)} />
        </label>
        <label className="span-2">
          Hospital name
          <input value={hospitalName} onChange={(event) => setHospitalName(event.target.value)} />
        </label>
        <label className="span-2">
          Upload files
          <input multiple type="file" onChange={(event) => setFiles(event.target.files)} />
        </label>
        <label className="span-2">
          Claims history JSON
          <textarea
            rows={4}
            value={claimsHistoryJson}
            onChange={(event) => setClaimsHistoryJson(event.target.value)}
          />
        </label>
        <label className="span-2">
          Documents manifest JSON
          <textarea
            rows={10}
            value={documentsManifest}
            onChange={(event) => setDocumentsManifest(event.target.value)}
          />
        </label>
        <label className="toggle span-2">
          <input
            checked={simulateComponentFailure}
            type="checkbox"
            onChange={(event) => setSimulateComponentFailure(event.target.checked)}
          />
          Simulate component failure for graceful degradation
        </label>
        <button className="submit-button span-2" disabled={busy} type="submit">
          {busy ? "Processing claim…" : "Submit claim"}
        </button>
      </form>
    </section>
  );
}
