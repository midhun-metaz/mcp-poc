import { inr, pretty, REQUIRED_DOCUMENTS, StatusBadge } from "../shared.jsx";
import DocumentUpload from "./DocumentUpload.jsx";

export default function ApplicationDetail({ application, onChange }) {
  const submitted = application.submitted_documents;
  const received = REQUIRED_DOCUMENTS.filter((document) => submitted.includes(document)).length;
  const complete = received === REQUIRED_DOCUMENTS.length;

  return (
    <>
      <div className="detail-head">
        <div>
          <h2>{application.full_name}</h2>
          <p className="muted">
            {application.application_id} · {application.email}
          </p>
        </div>
        <StatusBadge status={application.status} />
      </div>

      <dl className="facts">
        <div>
          <dt>Loan type</dt>
          <dd>{pretty(application.loan_type)}</dd>
        </div>
        <div>
          <dt>Amount</dt>
          <dd>{inr(application.loan_amount)}</dd>
        </div>
        <div>
          <dt>Tenure</dt>
          <dd>{application.tenure_months} months</dd>
        </div>
        <div>
          <dt>Monthly income</dt>
          <dd>{inr(application.monthly_income)}</dd>
        </div>
      </dl>

      <h3>
        Documents
        <span className="muted">
          {received} of {REQUIRED_DOCUMENTS.length} received
        </span>
      </h3>
      <div className="progress">
        <span style={{ width: `${(received / REQUIRED_DOCUMENTS.length) * 100}%` }} />
      </div>
      <ul className="checklist">
        {REQUIRED_DOCUMENTS.map((document) => (
          <li key={document} className={submitted.includes(document) ? "done" : ""}>
            {submitted.includes(document) ? "✓" : "○"} {pretty(document)}
          </li>
        ))}
      </ul>

      {/* The key gives each application a fresh, empty upload box. */}
      {complete ? (
        <div className="documents-complete" role="status">
          <span className="complete-icon" aria-hidden="true">✓</span>
          <div><h3>All required documents received</h3>
            <p>No more uploads needed. Document review and loan approval are separate steps.</p>
          </div>
        </div>
      ) : (
        <>
          {received === 0 && <p className="documents-empty">No documents yet. Add an identity proof, salary slip and bank statement to get started.</p>}
          <DocumentUpload key={application.application_id} applicationId={application.application_id} onUploaded={onChange} />
        </>
      )}
    </>
  );
}
