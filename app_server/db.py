"""SQLite storage and loan rules. All data is synthetic."""

import json
import sqlite3

DB_PATH = "los.db"

REQUIRED_FIELDS = ["full_name", "email", "monthly_income", "loan_type", "loan_amount", "tenure_months"]
REQUIRED_DOCUMENTS = ["identity_proof", "salary_slip", "bank_statement"]

SAMPLE_APPLICATIONS = [
    {
        "application_id": "LOS-1001",
        "full_name": "Asha Verma",
        "email": "asha.verma@example.com",
        "monthly_income": 85000,
        "loan_type": "personal",
        "loan_amount": 500000,
        "tenure_months": 36,
        "status": "awaiting_documents",
        "submitted_documents": ["identity_proof"],
    },
    {
        "application_id": "LOS-1002",
        "full_name": "Rahul Nair",
        "email": "rahul.nair@example.com",
        "monthly_income": 140000,
        "loan_type": "home",
        "loan_amount": 4500000,
        "tenure_months": 240,
        "status": "under_review",
        "submitted_documents": ["identity_proof", "salary_slip", "bank_statement"],
    },
]


def connect():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def insert(connection, application):
    # SQLite has no list type, so the document list is stored as JSON text.
    connection.execute(
        """INSERT INTO applications VALUES (
            :application_id, :full_name, :email, :monthly_income, :loan_type,
            :loan_amount, :tenure_months, :status, :submitted_documents
        )""",
        {**application, "submitted_documents": json.dumps(application["submitted_documents"])},
    )


def init_db():
    """Create the table and add the sample applications the first time."""
    with connect() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                application_id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                monthly_income INTEGER NOT NULL,
                loan_type TEXT NOT NULL,
                loan_amount INTEGER NOT NULL,
                tenure_months INTEGER NOT NULL,
                status TEXT NOT NULL,
                submitted_documents TEXT NOT NULL
            )
        """)
        if connection.execute("SELECT COUNT(*) FROM applications").fetchone()[0] == 0:
            for application in SAMPLE_APPLICATIONS:
                insert(connection, application)


def to_dict(row):
    application = dict(row)
    application["submitted_documents"] = json.loads(application["submitted_documents"])
    application["missing_documents"] = [
        document for document in REQUIRED_DOCUMENTS if document not in application["submitted_documents"]
    ]
    return application


def get_application(application_id):
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM applications WHERE application_id = ?", (application_id,)
        ).fetchone()
    return to_dict(row) if row else None


def list_applications(status=None):
    with connect() as connection:
        if status:
            rows = connection.execute(
                "SELECT * FROM applications WHERE status = ? ORDER BY application_id", (status,)
            ).fetchall()
        else:
            rows = connection.execute("SELECT * FROM applications ORDER BY application_id").fetchall()
    return [to_dict(row) for row in rows]


def create_application(applicant):
    """Save a draft, unless facts are missing or this email already has this loan type."""
    missing = [field for field in REQUIRED_FIELDS if not applicant.get(field)]
    if missing:
        return {"outcome": "needs_information", "missing_fields": missing}

    email = applicant["email"].strip().lower()
    with connect() as connection:
        existing = connection.execute(
            "SELECT application_id FROM applications WHERE email = ? AND loan_type = ?",
            (email, applicant["loan_type"]),
        ).fetchone()
        # Same person and loan type means a retry or duplicate request, so do not create another.
        if existing:
            return {"outcome": "already_exists", "application_id": existing["application_id"]}

        count = connection.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        application_id = f"LOS-{1001 + count}"
        insert(connection, {
            **applicant,
            "application_id": application_id,
            "email": email,
            "status": "draft",
            "submitted_documents": [],
        })
    return {"outcome": "created", "application_id": application_id}


def add_document(application_id, analysis):
    """Record a document read by the local model if it is a required type."""
    result = {"application_id": application_id, "analysis": analysis}
    if analysis["document_type"] not in REQUIRED_DOCUMENTS:
        return {**result, "outcome": "rejected", "reason": "This is not a required loan document."}

    submitted = get_application(application_id)["submitted_documents"]
    if analysis["document_type"] not in submitted:
        submitted.append(analysis["document_type"])
        with connect() as connection:
            connection.execute(
                "UPDATE applications SET submitted_documents = ? WHERE application_id = ?",
                (json.dumps(submitted), application_id),
            )
    missing = [document for document in REQUIRED_DOCUMENTS if document not in submitted]
    return {**result, "outcome": "accepted", "missing_documents": missing}
