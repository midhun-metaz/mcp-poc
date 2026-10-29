"""Small language model (SLM) running locally in Ollama: reads document text and returns its type, owner and income."""

import json
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma4:e2b")

# Ollama forces the model's answer to match this JSON schema.
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "document_type": {"type": "string", "enum": ["identity_proof", "salary_slip", "bank_statement", "other"]},
        "person_name": {"type": "string"},
        "monthly_income": {"type": ["integer", "null"]},
    },
    "required": ["document_type", "person_name", "monthly_income"],
}

PROMPT = """You classify documents for a loan application.

Document types:
- identity_proof: a government ID card, such as a PAN card, Aadhaar card, passport, driving licence or voter ID
- salary_slip: a payslip from an employer listing earnings, deductions and net pay
- bank_statement: a bank account statement or passbook listing transactions and balances
- other: anything else, for example electricity or phone bills, invoices, receipts or agreements

Fields:
- person_name: the person the document is about, not a parent, employer or company
- monthly_income: only for a salary_slip, the net (take-home) monthly pay in INR as a number,
  not gross pay or annual CTC; null for every other document type

Document:
{text}"""


def read_document(text):
    response = httpx.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": [{"role": "user", "content": PROMPT.format(text=text)}],
            "format": OUTPUT_SCHEMA,
            "think": False,  # a short extraction needs no reasoning; thinking only adds latency
            "stream": False,
            "options": {"temperature": 0},  # same document, same answer
        },
        timeout=120,
    )
    response.raise_for_status()
    return json.loads(response.json()["message"]["content"])
