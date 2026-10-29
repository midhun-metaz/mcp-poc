import { useState } from "react";
import * as api from "../api.js";
import { SAMPLE_PDFS } from "../samples.js";
import { pretty } from "../shared.jsx";

export default function DocumentUpload({ applicationId, onUploaded }) {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  function choose(newFile) {
    setFile(newFile);
    setResult(null);
  }

  // Load a sample PDF as if the user had picked it from their computer.
  async function loadSample(path) {
    const blob = await (await fetch(path)).blob();
    choose(new File([blob], path.slice(1), { type: "application/pdf" }));
  }

  async function submit() {
    setBusy(true);
    const response = await api.submitPdf(applicationId, file);
    setResult(response);
    setBusy(false);
    if (response.outcome === "accepted") {
      setFile(null);
      onUploaded();
    }
  }

  return (
    <div className="upload">
      <h3>Submit a document</h3>
      <p className="muted">The app server reads the PDF's text and the local model classifies it. Gemini never sees it.</p>

      <label
        className="dropzone"
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          choose(event.dataTransfer.files[0]);
        }}
      >
        <input
          type="file"
          accept="application/pdf"
          onChange={(event) => {
            choose(event.target.files[0]);
            event.target.value = ""; // so the same file can be chosen again
          }}
        />
        {file ? (
          <span>
            📄 <strong>{file.name}</strong> · click to change
          </span>
        ) : (
          <span>Drop a PDF here or click to choose one</span>
        )}
      </label>

      <div className="samples">
        <span className="muted">Sample PDFs</span>
        {SAMPLE_PDFS.map(([name, path]) => (
          <div key={path} className="sample">
            <span>{name}</span>
            <a href={path} target="_blank" rel="noreferrer">
              View
            </a>
            <button className="link" onClick={() => loadSample(path)}>
              Use
            </button>
          </div>
        ))}
      </div>

      <button className="primary" disabled={!file || busy} onClick={submit}>
        {busy ? "Reading the PDF…" : "Submit document"}
      </button>

      {result && <DocumentResult result={result} />}
    </div>
  );
}

function DocumentResult({ result }) {
  return (
    <div className={`result ${result.outcome ?? "failed"}`}>
      {result.outcome === "accepted" && (
        <p>
          Accepted as <strong>{pretty(result.analysis.document_type)}</strong>. Still missing:{" "}
          {result.missing_documents.map(pretty).join(", ") || "nothing"}.
        </p>
      )}
      {result.outcome === "rejected" && <p>Rejected: {result.reason}</p>}
      {result.detail && <p>{String(result.detail)}</p>}
      {/* The two steps of the pipeline: PDF -> text, then text -> the local model's answer. */}
      {result.extracted_text && (
        <details>
          <summary>1. Text read from the PDF</summary>
          <pre>{result.extracted_text}</pre>
        </details>
      )}
      {result.analysis && (
        <details>
          <summary>2. What the local model read</summary>
          <pre>{JSON.stringify(result.analysis, null, 2)}</pre>
        </details>
      )}
    </div>
  );
}
