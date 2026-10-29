"""App server: the loan system's REST API. Only this server touches the database and the document model.

Run: .venv/bin/python -m app_server.main   then open http://127.0.0.1:8001/docs to try the API
"""

from typing import Literal

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile
from pydantic import BaseModel
from pypdf import PdfReader

from app_server import db, slm

PORT = 8001

app = FastAPI(title="LOS App Server")


class NewApplication(BaseModel):
    # All optional, so a missing fact gets the needs_information outcome instead of an error.
    full_name: str | None = None
    email: str | None = None
    monthly_income: int | None = None
    loan_type: Literal["personal", "home", "auto"] | None = None
    loan_amount: int | None = None
    tenure_months: int | None = None


class Document(BaseModel):
    document_text: str


@app.get("/applications")
def list_applications(status: Literal["draft", "awaiting_documents", "under_review"] | None = None):
    return db.list_applications(status)


@app.get("/applications/{application_id}")
def get_application(application_id: str):
    application = db.get_application(application_id)
    if application is None:
        raise HTTPException(404, f"Application {application_id} not found.")
    return application


@app.post("/applications")
def create_application(applicant: NewApplication):
    return db.create_application(applicant.model_dump())


def read_and_save_document(application_id, text):
    """Let the local model read the document text, then record it if it is a required document."""
    if db.get_application(application_id) is None:
        raise HTTPException(404, f"Application {application_id} not found.")
    try:
        analysis = slm.read_document(text)
    except httpx.HTTPStatusError as error:
        # Ollama is running but failed, for example because the configured model has not been pulled.
        raise HTTPException(503, f"The local document model failed: {error.response.text}")
    except httpx.HTTPError:
        raise HTTPException(503, "The local document model is not reachable. Is `ollama serve` running?")
    return db.add_document(application_id, analysis)


@app.post("/applications/{application_id}/documents")
def submit_document(application_id: str, document: Document):
    """Document as plain text (used by the MCP tool when a user pastes text in the chat)."""
    return read_and_save_document(application_id, document.document_text)


@app.post("/applications/{application_id}/documents/pdf")
def submit_pdf(application_id: str, file: UploadFile):
    """Document as a PDF upload (used by the UI). The text is read from the PDF, then handled like pasted text."""
    # Layout mode keeps table rows on one line, so the model can tell which amount belongs to which label.
    text = "\n".join(page.extract_text(extraction_mode="layout") for page in PdfReader(file.file).pages)
    if not text.strip():
        # Scanned PDFs are images with no text layer; reading them would need OCR or a vision model.
        raise HTTPException(422, "No text found in this PDF. Scanned PDFs are not supported in this POC.")
    return {**read_and_save_document(application_id, text), "extracted_text": text}


if __name__ == "__main__":
    db.init_db()
    uvicorn.run(app, host="127.0.0.1", port=PORT)
