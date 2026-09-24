import { ApiClaimRecord } from "../lib/api";

type DecisionViewProps = {
  claim: ApiClaimRecord | null;
};

export function DecisionView({ claim }: DecisionViewProps) {
  if (!claim) {
    return (
      <section className="panel panel-empty">
        <p className="eyebrow">Decision Review</p>
        <h2>No claim loaded yet</h2>
        <p>Submit a claim or load an assignment case to inspect the full trace.</p>
      </section>
    );
  }

  const decision = claim.decision;
  return (
    <section className="panel panel-decision">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Decision Review</p>
          <h2>{claim.claim_id}</h2>
        </div>
        <span className={`status-pill status-${claim.status.toLowerCase()}`}>{claim.status}</span>
      </div>

      {claim.member_message ? (
        <div className="message-block blocked">{claim.member_message}</div>
      ) : null}

      {decision ? (
        <div className="decision-grid">
          <article className="decision-card">
            <p className="meta-label">Decision</p>
            <strong>{decision.decision}</strong>
            <p>{decision.reason}</p>
          </article>
          <article className="decision-card">
            <p className="meta-label">Approved amount</p>
            <strong>INR {decision.approved_amount.toFixed(2)}</strong>
            <p>Confidence {decision.confidence_score.toFixed(2)}</p>
          </article>
          <article className="decision-card">
            <p className="meta-label">Flags</p>
            <strong>{decision.manual_review_recommended ? "Manual review advised" : "No escalation"}</strong>
            <p>{decision.rejection_reasons.join(", ") || "No hard rejection reasons"}</p>
          </article>
        </div>
      ) : null}

      {decision?.notes.length ? (
        <div className="subpanel">
          <h3>Decision notes</h3>
          <ul>
            {decision.notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {decision?.line_items.length ? (
        <div className="subpanel">
          <h3>Line-item treatment</h3>
          <div className="table-shell">
            <table>
              <thead>
                <tr>
                  <th>Description</th>
                  <th>Status</th>
                  <th>Claimed</th>
                  <th>Approved</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {decision.line_items.map((item) => (
                  <tr key={`${item.description}-${item.reason}`}>
                    <td>{item.description}</td>
                    <td>{item.status}</td>
                    <td>{item.claimed_amount}</td>
                    <td>{item.approved_amount}</td>
                    <td>{item.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      <div className="subpanel">
        <h3>Rule outcomes</h3>
        <div className="rule-list">
          {claim.rule_outcomes.map((rule) => (
            <article className="rule-card" key={rule.rule_id}>
              <header>
                <strong>{rule.rule_id}</strong>
                <span className={`status-pill status-${rule.status.toLowerCase()}`}>{rule.status}</span>
              </header>
              <p>{rule.reason}</p>
            </article>
          ))}
        </div>
      </div>

      <div className="subpanel">
        <h3>Fraud signals</h3>
        {claim.fraud_signals.length ? (
          <ul>
            {claim.fraud_signals.map((signal) => (
              <li key={signal.code}>
                <strong>{signal.code}</strong>: {signal.description}
              </li>
            ))}
          </ul>
        ) : (
          <p>No fraud signals triggered.</p>
        )}
      </div>
    </section>
  );
}
