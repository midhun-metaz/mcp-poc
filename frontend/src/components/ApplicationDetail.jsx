import { inr, pretty, REQUIRED_DOCUMENTS, StatusBadge } from "../shared.jsx";
import DocumentUpload from "./DocumentUpload.jsx";

export default function ApplicationDetail({ application, onChange }) {
  const submitted = application.submitted_documents;

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
          {submitted.length} of {REQUIRED_DOCUMENTS.length} received
        </span>
      </h3>
      <div className="progress">
        <span style={{ width: `${(submitted.length / REQUIRED_DOCUMENTS.length) * 100}%` }} />
      </div>
      <ul className="checklist">
        {REQUIRED_DOCUMENTS.map((document) => (
          <li key={document} className={submitted.includes(document) ? "done" : ""}>
            {submitted.includes(document) ? "✓" : "○"} {pretty(document)}
          </li>
        ))}
      </ul>

      {/* The key gives each application a fresh, empty upload box. */}
      <DocumentUpload key={application.application_id} applicationId={application.application_id} onUploaded={onChange} />
    </>
  );
}
