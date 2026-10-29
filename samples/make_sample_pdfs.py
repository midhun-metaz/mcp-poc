"""Create realistic-looking sample PDFs for the demo. All names, companies and numbers are fictional.

Run: .venv/bin/python samples/make_sample_pdfs.py   (writes the PDFs next to this file)
"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

FOLDER = Path(__file__).parent
WIDTH = A4[0] - 30 * mm  # page width inside the margins

TITLE = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=17, leading=21)
SMALL = ParagraphStyle("small", fontName="Helvetica", fontSize=8.5, leading=11, textColor=colors.HexColor("#555555"))
BAND = ParagraphStyle("band", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=colors.white)
BOLD = ParagraphStyle("bold", fontName="Helvetica-Bold", fontSize=11, leading=14)


def inr(amount):
    """85000 -> '85,000.00', with Indian digit grouping."""
    rupees, paise = f"{amount:.2f}".split(".")
    head, tail = rupees[:-3], rupees[-3:]
    while len(head) > 2:
        head, tail = head[:-2], head[-2:] + "," + tail
    return f"{head},{tail}.{paise}" if head else f"{tail}.{paise}"


def watermark(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica-Bold", 44)
    canvas.setFillColor(colors.Color(0.6, 0.6, 0.6, alpha=0.18))
    canvas.translate(A4[0] / 2, A4[1] / 2)
    canvas.rotate(35)
    canvas.drawCentredString(0, 0, "SAMPLE - SYNTHETIC DATA")
    canvas.restoreState()


def band(text, colour):
    """A full-width coloured strip with white text."""
    table = Table([[Paragraph(text, BAND)]], colWidths=[WIDTH])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colour), ("PADDING", (0, 0), (-1, -1), 6)]))
    return table


def grid(rows, col_widths, header_colour=None, bold_last_row=False, right_align_from=None):
    """A bordered table. Optional: coloured header row, bold total row, right-aligned amount columns."""
    table = Table(rows, colWidths=col_widths)
    style = [
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bbbbbb")),
        ("PADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    if header_colour:
        style += [("BACKGROUND", (0, 0), (-1, 0), header_colour), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                  ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9)]
    if bold_last_row:
        style += [("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 9), ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f2f2f2"))]
    if right_align_from is not None:
        style.append(("ALIGN", (right_align_from, 0), (-1, -1), "RIGHT"))
    table.setStyle(TableStyle(style))
    return table


def details(pairs, label_colour):
    """Label/value pairs, two per row: | label | value | label | value |."""
    rows = [pairs[i] + pairs[i + 1] if i + 1 < len(pairs) else pairs[i] + ("", "") for i in range(0, len(pairs), 2)]
    table = grid(rows, [WIDTH * 0.18, WIDTH * 0.32, WIDTH * 0.18, WIDTH * 0.32])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), label_colour), ("BACKGROUND", (2, 0), (2, -1), label_colour),
                               ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 9), ("FONT", (2, 0), (2, -1), "Helvetica-Bold", 9)]))
    return table


def build(file_name, story):
    doc = SimpleDocTemplate(str(FOLDER / file_name), pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=15 * mm, bottomMargin=15 * mm, title=file_name, author="LOS Copilot POC (synthetic)")
    doc.build(story, onFirstPage=watermark, onLaterPages=watermark)
    print("wrote", FOLDER / file_name)


def salary_slip():
    navy, light = colors.HexColor("#1f3a68"), colors.HexColor("#e8edf5")
    earnings = [("Basic Salary", 50000), ("House Rent Allowance", 25000), ("Special Allowance", 20000), ("Conveyance Allowance", 5000)]
    deductions = [("Provident Fund", 6000), ("Professional Tax", 200), ("Income Tax (TDS)", 8800), ("", None)]
    gross, total_deductions = sum(a for _, a in earnings), sum(a for _, a in deductions if a)
    rows = [["Earnings", "Amount (Rs.)", "Deductions", "Amount (Rs.)"]]
    rows += [[e, inr(ea), d, inr(da) if da else ""] for (e, ea), (d, da) in zip(earnings, deductions)]
    rows.append(["Gross Earnings", inr(gross), "Total Deductions", inr(total_deductions)])
    build("salary-slip-asha-verma.pdf", [
        Paragraph("ACME SOFTWARE PVT. LTD.", TITLE),
        Paragraph("4th Floor, Tech Park One, Hinjewadi Phase 1, Pune 411057 | CIN: U72200MH2015PTC000000", SMALL),
        Spacer(1, 6 * mm),
        band("PAYSLIP FOR THE MONTH OF SEPTEMBER 2026", navy),
        Spacer(1, 3 * mm),
        details([("Employee Name", "Asha Verma"), ("Employee ID", "E-2231"), ("Designation", "Senior Analyst"),
                 ("Department", "Finance"), ("Date of Joining", "12-Jul-2021"), ("Pay Period", "01-Sep-2026 to 30-Sep-2026"),
                 ("Bank A/c No.", "XXXXXX4321"), ("PAN", "XXXXX0000X"), ("Days Paid", "30"), ("Location", "Pune")], light),
        Spacer(1, 5 * mm),
        grid(rows, [WIDTH * 0.3, WIDTH * 0.2, WIDTH * 0.3, WIDTH * 0.2], header_colour=navy, bold_last_row=True),
        Spacer(1, 5 * mm),
        band(f"NET PAY (TAKE HOME): Rs. {inr(gross - total_deductions)}", navy),
        Spacer(1, 2 * mm),
        Paragraph("Amount in words: Rupees Eighty-Five Thousand Only", BOLD),
        Spacer(1, 10 * mm),
        Paragraph("This is a computer-generated payslip and does not require a signature.", SMALL),
    ])


def bank_statement():
    teal, light = colors.HexColor("#0f5f5c"), colors.HexColor("#e6f2f1")
    opening = 120000
    transactions = [  # date, description, reference, debit, credit
        ("01-09-2026", "SALARY - ACME SOFTWARE PVT LTD", "NEFT0901234", 0, 85000),
        ("03-09-2026", "UPI/RENT/RAJESH KULKARNI", "UPI60918733", 25000, 0),
        ("07-09-2026", "UPI/GROCERY MART PUNE", "UPI60922144", 3450, 0),
        ("12-09-2026", "ATM CASH WITHDRAWAL - PUNE KP", "ATM09120044", 5000, 0),
        ("15-09-2026", "BILLPAY/CITY POWER DISTRIBUTION", "BPY60915500", 1840, 0),
        ("18-09-2026", "CREDIT CARD PAYMENT - XX8812", "IMPS0918881", 17500, 0),
        ("22-09-2026", "UPI/MOBILE RECHARGE", "UPI60922088", 599, 0),
        ("30-09-2026", "SAVINGS INTEREST CREDIT", "INT26093000", 0, 310),
    ]
    balance, rows = opening, [["Date", "Description", "Ref. No.", "Debit (Rs.)", "Credit (Rs.)", "Balance (Rs.)"],
                              ["01-09-2026", "OPENING BALANCE", "", "", "", inr(opening)]]
    for date, description, reference, debit, credit in transactions:
        balance += credit - debit
        rows.append([date, description, reference, inr(debit) if debit else "", inr(credit) if credit else "", inr(balance)])
    debits, credits = sum(t[3] for t in transactions), sum(t[4] for t in transactions)
    rows.append(["30-09-2026", "CLOSING BALANCE", "", inr(debits), inr(credits), inr(balance)])
    build("bank-statement-asha-verma.pdf", [
        Paragraph("NORTHWIND BANK", TITLE),
        Paragraph("Koregaon Park Branch, North Main Road, Pune 411001 | IFSC: NWBK0001234 | Customer care: 1800-000-0000", SMALL),
        Spacer(1, 6 * mm),
        band("STATEMENT OF ACCOUNT", teal),
        Spacer(1, 3 * mm),
        details([("Account Holder", "Asha Verma"), ("Account Number", "XXXXXX4321"),
                 ("Address", "14, Lakeview Apts, Pune 411001"), ("Account Type", "Savings"),
                 ("Statement Period", "01-09-2026 to 30-09-2026"), ("Currency", "INR")], light),
        Spacer(1, 5 * mm),
        grid(rows, [WIDTH * 0.11, WIDTH * 0.36, WIDTH * 0.15, WIDTH * 0.12, WIDTH * 0.12, WIDTH * 0.14],
             header_colour=teal, bold_last_row=True, right_align_from=3),
        Spacer(1, 10 * mm),
        Paragraph("This is a system-generated statement and does not require a signature. "
                  "Please report any discrepancy within 30 days.", SMALL),
    ])


def electricity_bill():
    orange, light = colors.HexColor("#b4540a"), colors.HexColor("#fbeee3")
    charges = [("Energy Charges (210 units)", 1470), ("Fixed Charges", 150), ("Electricity Duty", 160), ("Meter Rent", 60)]
    total = sum(amount for _, amount in charges)
    build("electricity-bill-asha-verma.pdf", [
        Paragraph("CITY POWER DISTRIBUTION LTD.", TITLE),
        Paragraph("Power House Road, Shivajinagar, Pune 411005 | Helpline: 1912 (fictional)", SMALL),
        Spacer(1, 6 * mm),
        band("ELECTRICITY BILL - SEPTEMBER 2026", orange),
        Spacer(1, 3 * mm),
        details([("Consumer Name", "Asha Verma"), ("Consumer No.", "1100223344"),
                 ("Address", "14, Lakeview Apts, Pune 411001"), ("Bill No.", "CPD/2609/778812"),
                 ("Billing Period", "01-09-2026 to 30-09-2026"), ("Bill Date", "05-10-2026"),
                 ("Tariff", "LT-I Residential"), ("Due Date", "15-10-2026")], light),
        Spacer(1, 5 * mm),
        grid([["Meter No.", "Previous Reading", "Current Reading", "Units Consumed"], ["MTR-558120", "4,520", "4,730", "210"]],
             [WIDTH / 4] * 4, header_colour=orange),
        Spacer(1, 5 * mm),
        grid([["Charges", "Amount (Rs.)"]] + [[name, inr(amount)] for name, amount in charges] + [["Total", inr(total)]],
             [WIDTH * 0.7, WIDTH * 0.3], header_colour=orange, bold_last_row=True, right_align_from=1),
        Spacer(1, 5 * mm),
        band(f"AMOUNT PAYABLE BY 15-10-2026: Rs. {inr(total)}", orange),
        Spacer(1, 10 * mm),
        Paragraph("Pay online or at any collection centre. A late payment charge applies after the due date.", SMALL),
    ])


def id_card():
    """A fictional identity card. It deliberately copies no real ID design, issuer or number format."""
    purple, light = colors.HexColor("#4b2e83"), colors.HexColor("#efeaf7")
    card_width = 125 * mm
    photo = Table([["PHOTO"]], colWidths=[30 * mm], rowHeights=[38 * mm])
    photo.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#d9d9d9")), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                               ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#777777")),
                               ("FONT", (0, 0), (-1, -1), "Helvetica-Bold", 9)]))
    fields = Table([["Name", "Priya Das"], ["Date of Birth", "18-03-1994"], ["Gender", "Female"],
                    ["ID Number", "EXA-4821-0937"], ["Address", "22, Riverside Colony,\nPune 411014"]],
                   colWidths=[24 * mm, 63 * mm])
    fields.setStyle(TableStyle([("FONT", (0, 0), (0, -1), "Helvetica-Bold", 8.5), ("FONT", (1, 0), (1, -1), "Helvetica", 9),
                                ("TEXTCOLOR", (0, 0), (0, -1), purple), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    card = Table([
        [Paragraph("EXAMPLE IDENTITY AUTHORITY", BAND), ""],
        [Paragraph("Photo Identity Card", ParagraphStyle("sub", fontName="Helvetica", fontSize=8.5, textColor=colors.white)), ""],
        [photo, fields],
        [Paragraph("Issued: 10-01-2024 &nbsp;&nbsp; Valid till: 09-01-2034", SMALL), ""],
    ], colWidths=[36 * mm, card_width - 36 * mm])
    card.setStyle(TableStyle([
        ("SPAN", (0, 0), (1, 0)), ("SPAN", (0, 1), (1, 1)), ("SPAN", (0, 3), (1, 3)),
        ("BACKGROUND", (0, 0), (1, 1), purple), ("BACKGROUND", (0, 2), (1, 3), light),
        ("BOX", (0, 0), (-1, -1), 1, purple), ("VALIGN", (0, 2), (-1, 2), "TOP"), ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    card.hAlign = "LEFT"
    build("id-card-priya-das.pdf", [
        Paragraph("COPY OF IDENTITY CARD", TITLE),
        Paragraph("Submitted by the applicant as identity proof", SMALL),
        Spacer(1, 8 * mm),
        card,
        Spacer(1, 6 * mm),
        Paragraph("SPECIMEN - not a valid identity document. The issuer, number and person are fictional.", BOLD),
    ])


if __name__ == "__main__":
    salary_slip()
    bank_statement()
    electricity_bill()
    id_card()
