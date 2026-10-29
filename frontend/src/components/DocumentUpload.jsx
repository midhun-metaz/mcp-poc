import { useState } from "react";
import * as api from "../api.js";
import { SAMPLE_PDFS } from "../samples.js";
import { pretty } from "../shared.jsx";

export default function DocumentUpload({ applicationId, onUploaded }) {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  const [loading, setLoading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const locked = busy || loading;

  function choose(newFile) {
    if (!newFile || locked) return;
    if (!newFile.name.toLowerCase().endsWith(".pdf")) {
      setError("Choose a PDF document to continue.");
      return;
    }
    setFile(newFile);
    setResult(null);
    setError("");
  }

  async function loadSample(path) {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(path);
      if (!response.ok) throw new Error("This sample couldn't be loaded. Please try again.");
      const blob = await response.blob();
      choose(new File([blob], path.slice(1), { type: "application/pdf" }));
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  }

  async function submit() {
    if (!file || locked) return;
    setBusy(true);
    setError("");
    try {
      const response = await api.submitPdf(applicationId, file);
      setResult(response);
      if (response.outcome === "accepted") {
        setFile(null);
        onUploaded();
      }
    } catch {
      setError("Couldn't submit the document. Check your connection and try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="upload">
      <div className="upload-heading">
        <div><h3>Add a document</h3><p className="muted">Upload a PDF or try one of the sample documents below.</p></div>
        <span className="document-tag">PDF only</span>
      </div>
      <label className={`dropzone ${dragging ? "dragging" : ""} ${file ? "has-file" : ""} ${locked ? "locked" : ""}`}
        onDragOver={(event) => { event.preventDefault(); if (!locked) setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => { event.preventDefault(); setDragging(false); choose(event.dataTransfer.files[0]); }}>
        <input type="file" accept="application/pdf,.pdf" disabled={locked} aria-label="Choose a PDF document"
          onChange={(event) => { choose(event.target.files[0]); event.target.value = ""; }} />
        <span className="pdf-icon" aria-hidden="true">{file ? "PDF" : "↑"}</span>
        <span className="dropzone-copy"><strong>{file ? file.name : "Drop your PDF here"}</strong>
          <span>{file ? `${Math.max(1, Math.round(file.size / 1024))} KB · Ready to submit` : "or browse files on your computer"}</span>
          <small>Text-based PDFs supported · Scanned documents aren't supported yet</small>
        </span>
        <span className="browse-label">{file ? "Change file" : "Browse files"}</span>
      </label>
      <div className="samples">
        <div className="sample-heading"><h4>Try a sample</h4><span className="muted">4 synthetic documents</span></div>
        <div className="sample-grid">
          {SAMPLE_PDFS.map(([name, path], index) => {
            const selected = file?.name === path.slice(1);
            const descriptions = ["Asha Verma · Net income extraction", "Asha Verma · Account statement", "Priya Das · Identity proof", "Asha Verma · Unsupported document type"];
            return <article key={path} className={`sample-card ${selected ? "selected" : ""}`}>
              <div className="sample-info"><span className="pdf-icon" aria-hidden="true">PDF</span>
                <div><strong>{name.replace(" (not a loan document)", "")}</strong><p>{descriptions[index]}</p></div>
              </div>
              <div className="sample-footer"><span className={`document-tag ${index === 3 ? "warning" : ""}`}>{index === 3 ? "Rejection example" : "Sample PDF"}</span>
                <div className="sample-actions"><a href={path} target="_blank" rel="noreferrer" aria-label={`Preview ${name} (opens in a new tab)`}>Preview ↗</a>
                  <button disabled={locked} aria-pressed={selected} aria-label={`Select ${name}`} onClick={() => loadSample(path)}>{selected ? "✓ Selected" : "Select"}</button>
                </div>
              </div>
            </article>;
          })}
        </div>
      </div>
      <div className="upload-footer"><p className="muted" role="status">{busy ? "Reading and verifying your document…" : loading ? "Loading sample…" : file ? "Your document is ready. Submit it to this application." : "Select a document to continue."}</p>
        <button className="primary" disabled={!file || locked} onClick={submit}>{busy ? "Processing…" : "Submit document →"}</button>
      </div>
      {error && <p className="upload-error" role="alert">{error}</p>}
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
      {result.validation_checks?.length > 0 && (
        <section className="validation-panel" aria-label="Document verification" aria-live="polite">
          <h4>Document verification</h4>
          <ul className="validation-checks">
            {result.validation_checks.map((check) => (
              <li key={check.label} className={`validation-check ${check.status}`}>
                <span className="validation-mark" aria-hidden="true">{check.status === "passed" ? "✓" : check.status === "failed" ? "!" : "—"}</span>
                <div><strong>{check.label} <span className="validation-status">{check.status === "passed" ? "Matched" : check.status === "failed" ? "Needs attention" : "Not checked"}</span></strong><p>{check.message}</p></div>
              </li>
            ))}
          </ul>
        </section>
      )}
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
