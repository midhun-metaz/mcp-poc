import { useState } from "react";
import * as api from "../api.js";

const EMPTY = { full_name: "", email: "", monthly_income: "", loan_type: "personal", loan_amount: "", tenure_months: "" };
const toNumber = (value) => (value === "" ? null : Number(value));

export default function NewApplicationForm({ onCreated, onCancel }) {
  const [form, setForm] = useState(EMPTY);
  const [message, setMessage] = useState(null);

  // A functional update, so quick changes to several fields are not lost.
  const update = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }));

  async function submit(event) {
    event.preventDefault();
    const result = await api.createApplication({
      ...form,
      monthly_income: toNumber(form.monthly_income),
      loan_amount: toNumber(form.loan_amount),
      tenure_months: toNumber(form.tenure_months),
    });
    if (result.outcome === "created") onCreated(result.application_id);
    else if (result.outcome === "already_exists") setMessage(`This person already has this loan type: ${result.application_id}.`);
    else if (result.outcome === "needs_information") setMessage(`Please fill in: ${result.missing_fields.join(", ").replaceAll("_", " ")}.`);
    else setMessage("Please check the values.");
  }

  return (
    <form className="new-form" onSubmit={submit}>
      <div>
        <h2>New application</h2>
        <p className="muted">Saved as a draft through the app server's REST API.</p>
      </div>

      <label>
        Full name
        <input value={form.full_name} onChange={update("full_name")} />
      </label>
      <label>
        Email
        <input type="email" value={form.email} onChange={update("email")} />
      </label>
      <div className="row">
        <label>
          Loan type
          <select value={form.loan_type} onChange={update("loan_type")}>
            <option value="personal">Personal</option>
            <option value="home">Home</option>
            <option value="auto">Auto</option>
          </select>
        </label>
        <label>
          Monthly income (₹)
          <input type="number" min="0" value={form.monthly_income} onChange={update("monthly_income")} />
        </label>
      </div>
      <div className="row">
        <label>
          Loan amount (₹)
          <input type="number" min="0" value={form.loan_amount} onChange={update("loan_amount")} />
        </label>
        <label>
          Tenure (months)
          <input type="number" min="1" value={form.tenure_months} onChange={update("tenure_months")} />
        </label>
      </div>

      {message && <p className="result rejected">{message}</p>}

      <div className="actions">
        <button type="button" onClick={onCancel}>
          Cancel
        </button>
        <button className="primary">Create draft</button>
      </div>
    </form>
  );
}
