import time

from app_server import slm

SAMPLE_DOCUMENTS = [
    {
        "name": "payslip, simple",
        "text": """ACME SOFTWARE PVT LTD - PAYSLIP FOR SEPTEMBER 2026
Employee: Asha Verma   Employee ID: E-2231
Basic: 50,000  HRA: 25,000  Special allowance: 25,000
Gross earnings: 1,00,000  Deductions (PF, tax): 15,000
Net pay: Rs 85,000""",
        "expected": {"document_type": "salary_slip", "person_name": "Asha Verma", "monthly_income": 85000},
    },
    {
        "name": "payslip, table layout",
        "text": """PAY STATEMENT - GLOBEX RETAIL LTD
Name of employee: KARAN SHAH        Month: Aug 2026
Earnings                 Amount (INR)
Basic pay                40,000
Allowances               38,500
Total earnings           78,500
Professional tax            200
Income tax                8,300
Take-home salary         70,000""",
        "expected": {"document_type": "salary_slip", "person_name": "Karan Shah", "monthly_income": 70000},
    },
    {
        "name": "payslip with CTC and gross",
        "text": """Initech Solutions | Salary slip | October 2026
Employee name: Meera Iyer | Designation: Analyst
Annual CTC: 13,50,000
Gross monthly salary: 1,12,500
Total deductions: 22,500
Net salary credited to bank: 90,000""",
        "expected": {"document_type": "salary_slip", "person_name": "Meera Iyer", "monthly_income": 90000},
    },
    {
        "name": "bank statement with salary",
        "text": """STATE BANK OF EXAMPLE - ACCOUNT STATEMENT
Account holder: Asha Verma   Account no: XXXXXX4321
Period: 01-Sep-2026 to 30-Sep-2026
Date     Description              Debit     Credit    Balance
01-Sep   Opening balance                              1,20,000
01-Sep   SALARY ACME SOFTWARE               85,000    2,05,000
05-Sep   RENT PAYMENT             25,000              1,80,000
18-Sep   CARD PAYMENT             17,500              1,62,500
Closing balance: 1,62,500""",
        "expected": {"document_type": "bank_statement", "person_name": "Asha Verma", "monthly_income": None},
    },
    {
        "name": "bank passbook",
        "text": """EXAMPLE CO-OPERATIVE BANK - SAVINGS PASSBOOK
Customer: Mr. Rahul Nair     A/c: XXXXXXX9876     Branch: Kochi Main
12/08/2026  NEFT IN - NAIR CONSULTING      +1,40,000   bal 3,10,000
20/08/2026  EMI HOME LOAN                    -42,000   bal 2,68,000
29/08/2026  ATM WITHDRAWAL                    -5,000   bal 2,63,000""",
        "expected": {"document_type": "bank_statement", "person_name": "Rahul Nair", "monthly_income": None},
    },
    {
        "name": "PAN card with father's name",
        "text": """INCOME TAX DEPARTMENT        GOVT. OF INDIA
Permanent Account Number Card
Name: RAHUL NAIR
Father's Name: SURESH NAIR
Date of Birth: 14/02/1988
PAN: XXXXX0000X (sample)""",
        "expected": {"document_type": "identity_proof", "person_name": "Rahul Nair", "monthly_income": None},
    },
    {
        "name": "driving licence",
        "text": """DRIVING LICENCE - TRANSPORT DEPARTMENT (SAMPLE)
DL No: XX00 0000000000
Name: Meera Iyer
S/D/W of: Ramesh Iyer
Valid till: 2041-03-09
Vehicle class: LMV""",
        "expected": {"document_type": "identity_proof", "person_name": "Meera Iyer", "monthly_income": None},
    },
    {
        "name": "electricity bill",
        "text": """CITY POWER DISTRIBUTION LTD - ELECTRICITY BILL
Consumer name: Asha Verma    Consumer no: 1100223344
Billing month: September 2026
Units consumed: 210
Amount payable: Rs 1,840   Due date: 15-Oct-2026""",
        "expected": {"document_type": "other", "person_name": "Asha Verma", "monthly_income": None},
    },
    {
        "name": "gym membership invoice",
        "text": """FITZONE GYM - MEMBERSHIP INVOICE #F-5521
Member: Karan Shah
Plan: Annual membership
Amount paid: Rs 18,000 (incl. GST)
Valid from 01-Oct-2026 to 30-Sep-2027""",
        "expected": {"document_type": "other", "person_name": "Karan Shah", "monthly_income": None},
    },
]


def main():
    print(f"Model: {slm.OLLAMA_MODEL}\n")
    correct = {"document_type": 0, "person_name": 0, "monthly_income": 0}
    seconds = []
    for sample in SAMPLE_DOCUMENTS:
        start = time.monotonic()
        result = slm.read_document(sample["text"])
        seconds.append(time.monotonic() - start)

        expected = sample["expected"]
        checks = {
            "document_type": result["document_type"] == expected["document_type"],
            # Allow titles such as "Mr." and any capitalisation.
            "person_name": expected["person_name"].lower() in result["person_name"].lower(),
            "monthly_income": result["monthly_income"] == expected["monthly_income"],
        }
        wrong = [field for field, ok in checks.items() if not ok]
        for field, ok in checks.items():
            correct[field] += ok
        print(f"{sample['name']:<28} {seconds[-1]:5.1f}s  {'ok' if not wrong else 'WRONG: ' + ', '.join(wrong)}  {result}")

    total = len(SAMPLE_DOCUMENTS)
    print()
    for field, count in correct.items():
        print(f"{field:<15} {count}/{total} correct")
    print(f"Latency: average {sum(seconds) / total:.1f}s, slowest {max(seconds):.1f}s (the first call also loads the model)")


if __name__ == "__main__":
    main()
