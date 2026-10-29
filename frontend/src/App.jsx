import { useEffect, useState } from "react";
import * as api from "./api.js";
import ApplicationDetail from "./components/ApplicationDetail.jsx";
import ApplicationList from "./components/ApplicationList.jsx";
import ChatPanel from "./components/ChatPanel.jsx";
import NewApplicationForm from "./components/NewApplicationForm.jsx";

export default function App() {
  const [applications, setApplications] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState(null);

  // Reload the list after anything that may change data: the form, an upload or a chat answer.
  async function refresh() {
    const list = await api.listApplications();
    if (Array.isArray(list)) {
      setApplications(list);
      setError(null);
    } else {
      setError("The app server is not reachable. Start it with: .venv/bin/python -m app_server.main");
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  function select(applicationId) {
    setSelectedId(applicationId);
    setCreating(false);
  }

  const selected = applications.find((application) => application.application_id === selectedId);

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo">LOS</span>
          <div>
            <h1>LOS Copilot</h1>
            <p>Loan origination · synthetic data</p>
          </div>
        </div>
        <button className="primary" onClick={() => setCreating(true)}>
          + New application
        </button>
      </header>

      {error && <p className="banner">{error}</p>}

      <main className="layout">
        <ApplicationList applications={applications} selectedId={creating ? null : selectedId} onSelect={select} />

        <section className="panel">
          {creating ? (
            <NewApplicationForm
              onCancel={() => setCreating(false)}
              onCreated={async (applicationId) => {
                await refresh();
                select(applicationId);
              }}
            />
          ) : selected ? (
            <ApplicationDetail application={selected} onChange={refresh} />
          ) : (
            <div className="application-empty">
              <span className="empty-icon" aria-hidden="true">✦</span>
              <h2>Your workspace, your starting point</h2>
              <p>Chat with Copilot to look up applications or create a draft. Select an applicant on the left when you want to review their details.</p>
              <span className="document-tag">No application selected</span>
            </div>
          )}
        </section>

        <ChatPanel application={creating ? null : selected} onReply={refresh} onClearApplication={() => select(null)} />
      </main>
    </div>
  );
}
