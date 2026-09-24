import { EvalRunResponse } from "../lib/api";

type EvalDashboardProps = {
  onRunAll: () => Promise<void>;
  busy: boolean;
  evalRun: EvalRunResponse | null;
};

export function EvalDashboard({ onRunAll, busy, evalRun }: EvalDashboardProps) {
  return (
    <section className="panel panel-eval">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Eval Harness</p>
          <h2>Assignment suite runner</h2>
        </div>
        <button className="secondary-button" disabled={busy} onClick={() => void onRunAll()} type="button">
          {busy ? "Running evals…" : "Run all 12 cases"}
        </button>
      </div>

      {!evalRun ? (
        <p>No eval run yet. Launch the full suite to generate `docs/eval-report.md` from the backend.</p>
      ) : (
        <>
          <div className="decision-grid">
            <article className="decision-card">
              <p className="meta-label">Run ID</p>
              <strong>{evalRun.run_id}</strong>
            </article>
            <article className="decision-card">
              <p className="meta-label">Pass rate</p>
              <strong>
                {evalRun.passed_cases}/{evalRun.total_cases}
              </strong>
            </article>
            <article className="decision-card">
              <p className="meta-label">Finished</p>
              <strong>{evalRun.completed_at ?? "In progress"}</strong>
            </article>
          </div>
          <div className="table-shell">
            <table>
              <thead>
                <tr>
                  <th>Case</th>
                  <th>Expected</th>
                  <th>Actual</th>
                  <th>Pass</th>
                </tr>
              </thead>
              <tbody>
                {evalRun.results.map((result) => (
                  <tr key={result.case_id}>
                    <td>
                      {result.case_id} — {result.case_name}
                    </td>
                    <td>{String(result.expected.decision ?? "BLOCKED")}</td>
                    <td>{result.actual.decision?.decision ?? result.actual.status}</td>
                    <td>{result.passed ? "Yes" : "No"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
