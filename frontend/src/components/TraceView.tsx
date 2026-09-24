import { ApiClaimRecord } from "../lib/api";

type TraceViewProps = {
  claim: ApiClaimRecord | null;
};

export function TraceView({ claim }: TraceViewProps) {
  return (
    <section className="panel panel-trace">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Pipeline Trace</p>
          <h2>Agent-by-agent reasoning trail</h2>
        </div>
      </div>

      {!claim ? (
        <p>Trace events will appear here after a claim is processed.</p>
      ) : (
        <div className="trace-list">
          {claim.trace.map((step) => (
            <article className="trace-card" key={`${step.step}-${step.timestamp}`}>
              <header>
                <div>
                  <strong>{step.step}</strong>
                  <p>{step.agent}</p>
                </div>
                <span className={`status-pill status-${step.status.toLowerCase()}`}>{step.status}</span>
              </header>
              <p>{step.summary}</p>
              {step.warnings.length ? (
                <ul>
                  {step.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              ) : null}
              {step.recoverable_error ? <p className="error-text">{step.recoverable_error}</p> : null}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
