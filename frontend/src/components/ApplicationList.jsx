import { useState } from "react";
import { inr, pretty, StatusBadge } from "../shared.jsx";

const FILTERS = ["all", "draft", "awaiting_documents", "under_review"];

export default function ApplicationList({ applications, selectedId, onSelect }) {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");

  const shown = applications
    .filter((application) => filter === "all" || application.status === filter)
    .filter((application) =>
      `${application.application_id} ${application.full_name}`.toLowerCase().includes(search.toLowerCase()),
    )
    .reverse(); // newest first

  return (
    <section className="panel">
      <h2>
        Applications <span className="count">{applications.length}</span>
      </h2>
      <input
        className="search"
        placeholder="Search by name or ID"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
      />
      <div className="chips">
        {FILTERS.map((status) => (
          <button key={status} className={filter === status ? "chip active" : "chip"} onClick={() => setFilter(status)}>
            {pretty(status)}
          </button>
        ))}
      </div>

      <ul className="cards">
        {shown.map((application) => (
          <li key={application.application_id}>
            <button
              className={application.application_id === selectedId ? "card selected" : "card"}
              onClick={() => onSelect(application.application_id)}
            >
              <span className="card-top">
                <strong>{application.full_name}</strong>
                <StatusBadge status={application.status} />
              </span>
              <span className="muted">
                {application.application_id} · {pretty(application.loan_type)} · {inr(application.loan_amount)}
              </span>
            </button>
          </li>
        ))}
        {shown.length === 0 && <li className="muted">No applications match.</li>}
      </ul>
    </section>
  );
}
