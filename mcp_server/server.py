"""MCP server: wraps the app server's REST API as MCP tools. It has no database of its own.

Run: .venv/bin/python -m mcp_server.server   (start the app server first)
"""

from typing import Any, Literal

import httpx
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

APP_SERVER_URL = "http://127.0.0.1:8001"
PORT = 8000

mcp = MCPServer("LOS Copilot")


def call_app_server(method, path, **kwargs):
    """Call the app server and return its JSON. Errors such as "not found" go back to the model as results."""
    response = httpx.request(method, APP_SERVER_URL + path, timeout=120, **kwargs)  # documents can take a while
    if response.is_server_error:
        # ToolError passes its message to the model; other exceptions are hidden by the MCP SDK.
        raise ToolError(f"App server error: {response.text}")
    return response.json()


@mcp.tool()
def list_applications(status: Literal["draft", "awaiting_documents", "under_review"] | None = None) -> dict[str, Any]:
    """List loan applications, optionally filtered by status."""
    params = {"status": status} if status else {}
    return {"applications": call_app_server("GET", "/applications", params=params)}


@mcp.tool()
def get_application(application_id: str) -> dict[str, Any]:
    """Return one loan application: its details, status, submitted documents and missing documents.
    Missing documents shows presence only, not validity or loan eligibility."""
    return call_app_server("GET", f"/applications/{application_id}")


@mcp.tool()
def create_application(
    full_name: str | None = None,
    email: str | None = None,
    monthly_income: int | None = None,
    loan_type: Literal["personal", "home", "auto"] | None = None,
    loan_amount: int | None = None,
    tenure_months: int | None = None,
) -> dict[str, Any]:
    """Create a DRAFT loan application for ONE person (call once per person). A draft is not submitted or approved.
    Amounts are in INR. Pass only facts the user gave and leave the rest empty; never guess.
    Returns outcome: created, already_exists (same email and loan type), or
    needs_information (ask the user for missing_fields)."""
    return call_app_server("POST", "/applications", json={
        "full_name": full_name,
        "email": email,
        "monthly_income": monthly_income,
        "loan_type": loan_type,
        "loan_amount": loan_amount,
        "tenure_months": tenure_months,
    })


@mcp.tool()
def submit_document(application_id: str, document_text: str) -> dict[str, Any]:
    """Submit a document for an application. Pass the document text exactly as the user gave it.
    A local model identifies the document type and owner. Returns outcome accepted (with the
    remaining missing_documents) or rejected (with a reason). This checks the type only,
    not authenticity."""
    return call_app_server("POST", f"/applications/{application_id}/documents", json={"document_text": document_text})


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=PORT)
