export const REQUIRED_DOCUMENTS = ["identity_proof", "salary_slip", "bank_statement"];

// "awaiting_documents" -> "Awaiting documents"
export const pretty = (text) => text.charAt(0).toUpperCase() + text.slice(1).replaceAll("_", " ");

// 4500000 -> "₹45,00,000"
export const inr = (amount) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(amount);

export function StatusBadge({ status }) {
  return <span className={`badge ${status}`}>{pretty(status)}</span>;
}
