import re
import unicodedata

import httpx

from app_server import slm


def normalize_name(value):
    if not isinstance(value, str):
        return ""
    return " ".join(re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", value).casefold()))


def validate_document(application, analysis, filename=None):
    checks = []

    def check(label, passed, message):
        checks.append({"label": label, "status": "passed" if passed else "failed", "message": message})

    expected = normalize_name(application["full_name"])
    actual = normalize_name(analysis.get("person_name"))
    name_match = bool(expected and actual and expected == actual)
    comparison = {"method": "exact", "verdict": "match" if name_match else "mismatch"}
    message = f"Application: {application['full_name']}. Document: {analysis.get('person_name') or 'Not found'}."
    if expected and actual and not name_match:
        try:
            assessment = slm.match_names(application["full_name"], analysis["person_name"])
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            assessment = {"verdict": "uncertain", "reason": "Name comparison unavailable. Retry or request manual review."}
        comparison = {"method": "slm", **assessment}
        name_match = assessment["verdict"] == "match"
        message += f" Name review: {assessment['verdict']}. {assessment['reason']}"
        if assessment["verdict"] == "uncertain":
            message += " Manual review required; document has not been counted."
    elif not expected or not actual:
        message += " Both names are required."
    check("Applicant name", name_match, message)
    checks[-1]["comparison"] = comparison

    if analysis.get("document_type") == "salary_slip":
        income = analysis.get("monthly_income")
        check("Monthly net income", type(income) is int and income > 0 and income == application["monthly_income"],
              f"Declared: INR {application['monthly_income']:,}. Document: "
              + (f"INR {income:,}." if type(income) is int else "Not found."))

    if filename:
        words = normalize_name(filename.rsplit(".", 1)[0])
        hints = {
            "salary_slip": ("salary slip", "payslip", "pay slip"),
            "bank_statement": ("bank statement", "account statement", "passbook"),
            "identity_proof": ("identity proof", "id card", "aadhaar", "aadhar", "pan card", "passport", "driving licence", "voter id"),
        }
        types = {kind for kind, phrases in hints.items()
                 if any(f" {phrase} " in f" {words} " for phrase in phrases)}
        if types:
            check("Filename and contents", types == {analysis.get("document_type")},
                  f"Filename suggests: {', '.join(sorted(types))}. Contents: {analysis.get('document_type')}.")
        else:
            checks.append({"label": "Filename and contents", "status": "not_checked",
                           "message": "No recognizable document type in the filename; classified from contents."})
    return checks
