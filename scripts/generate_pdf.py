#!/usr/bin/env python3
"""Generate professional PDF invoices from invoice JSON data."""

import json
import sys
import os
from pathlib import Path

# Project root
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PDF_DIR = ROOT / "invoices" / "pdf"

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def fmt_indian(n):
    """Format number in Indian style: 1,23,456.78"""
    s = f"{n:,.2f}"
    parts = s.split(".")
    whole = parts[0].replace(",", "")
    decimal = parts[1]
    if len(whole) <= 3:
        return whole + "." + decimal
    last3 = whole[-3:]
    rest = whole[:-3]
    groups = []
    while rest:
        groups.insert(0, rest[-2:])
        rest = rest[:-2]
    return ",".join(groups) + "," + last3 + "." + decimal

def fmt_amount(n, currency):
    """Format amount with currency symbol."""
    if currency == "INR":
        return f"INR {fmt_indian(n)}"
    return f"{currency} {n:,.2f}"

def number_to_words(n):
    """Convert a number to words (simplified)."""
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven",
            "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen",
            "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty",
            "Sixty", "Seventy", "Eighty", "Ninety"]

    if n == 0:
        return "Zero"

    def _convert(num):
        if num < 20:
            return ones[num]
        elif num < 100:
            return tens[num // 10] + (" " + ones[num % 10] if num % 10 else "")
        elif num < 1000:
            return ones[num // 100] + " Hundred" + (" and " + _convert(num % 100) if num % 100 else "")
        elif num < 100000:
            return _convert(num // 1000) + " Thousand" + (" " + _convert(num % 1000) if num % 1000 else "")
        elif num < 10000000:
            return _convert(num // 100000) + " Lakh" + (" " + _convert(num % 100000) if num % 100000 else "")
        else:
            return _convert(num // 10000000) + " Crore" + (" " + _convert(num % 10000000) if num % 10000000 else "")

    whole = int(n)
    frac = round((n - whole) * 100)
    result = _convert(whole)
    if frac:
        result += f" and {frac}/100"
    return result

def amount_in_words(amount, currency):
    """Full amount in words with currency name."""
    currency_names = {
        "USD": "US Dollars",
        "CAD": "Canadian Dollars",
        "GBP": "British Pounds",
        "EUR": "Euros",
        "AED": "UAE Dirhams",
        "INR": "Indian Rupees",
    }
    name = currency_names.get(currency, currency)
    return f"{name} {number_to_words(amount)} Only"


INVOICE_CSS = """
@page {
    size: A4;
    margin: 20mm 18mm 20mm 18mm;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 10pt;
    color: #1a1a1a;
    line-height: 1.5;
}
.invoice-container {
    max-width: 100%;
}
.header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 3px solid #2c3e50;
}
.header h1 {
    font-size: 22pt;
    font-weight: 700;
    color: #2c3e50;
    letter-spacing: 1px;
}
.invoice-meta {
    text-align: right;
    font-size: 9.5pt;
}
.invoice-meta p {
    margin-bottom: 3px;
}
.invoice-meta strong {
    color: #2c3e50;
}
.parties {
    display: flex;
    justify-content: space-between;
    margin-bottom: 28px;
    gap: 40px;
}
.party {
    flex: 1;
}
.party-label {
    font-size: 8pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #7f8c8d;
    margin-bottom: 6px;
}
.party-name {
    font-size: 12pt;
    font-weight: 700;
    color: #2c3e50;
    margin-bottom: 4px;
}
.party p {
    font-size: 9.5pt;
    margin-bottom: 1px;
    color: #444;
}
table.items {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 20px;
}
table.items thead th {
    background: #2c3e50;
    color: white;
    padding: 10px 12px;
    font-size: 8.5pt;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    text-align: left;
}
table.items thead th:nth-child(4),
table.items thead th:nth-child(5),
table.items thead th:nth-child(6) {
    text-align: right;
}
table.items tbody td {
    padding: 10px 12px;
    font-size: 9.5pt;
    border-bottom: 1px solid #e8e8e8;
}
table.items tbody td:nth-child(4),
table.items tbody td:nth-child(5),
table.items tbody td:nth-child(6) {
    text-align: right;
}
table.items tbody tr:last-child td {
    border-bottom: 2px solid #2c3e50;
}
.totals-section {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 20px;
}
table.totals {
    width: 320px;
    border-collapse: collapse;
}
table.totals td {
    padding: 6px 12px;
    font-size: 9.5pt;
}
table.totals td:first-child {
    text-align: left;
    color: #555;
}
table.totals td:last-child {
    text-align: right;
    font-weight: 500;
}
table.totals tr.total-row td {
    border-top: 2px solid #2c3e50;
    font-size: 11pt;
    font-weight: 700;
    color: #2c3e50;
    padding-top: 10px;
}
table.totals tr.secondary td {
    font-size: 9pt;
    color: #666;
}
.amount-words {
    font-size: 9pt;
    color: #555;
    margin-bottom: 24px;
    text-align: right;
    font-style: italic;
}
.bank-details {
    background: #f8f9fa;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 16px 20px;
    margin-bottom: 20px;
}
.bank-details h3 {
    font-size: 9pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #2c3e50;
    margin-bottom: 10px;
}
table.bank {
    border-collapse: collapse;
}
table.bank td {
    padding: 3px 0;
    font-size: 9pt;
}
table.bank td:first-child {
    color: #777;
    padding-right: 20px;
    white-space: nowrap;
}
table.bank td:last-child {
    font-weight: 500;
}
.footer {
    margin-top: 30px;
    padding-top: 16px;
    border-top: 1px solid #ddd;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
}
.notes {
    font-size: 8.5pt;
    color: #777;
    max-width: 55%;
}
.notes p {
    margin-bottom: 4px;
}
.signatory {
    text-align: right;
    font-size: 9.5pt;
}
.signatory .firm-name {
    font-weight: 700;
    color: #2c3e50;
    margin-bottom: 30px;
}
.signatory .sig-line {
    border-top: 1px solid #999;
    padding-top: 4px;
    font-size: 8.5pt;
    color: #777;
}
"""


def build_html(invoice, client, business):
    """Build the full HTML for an invoice."""
    currency = invoice["currency"]
    is_export = invoice["tax"]["type"] == "export"
    is_domestic = not is_export

    # Title
    if is_export:
        title = "TAX INVOICE &mdash; EXPORT OF SERVICES"
    else:
        title = "TAX INVOICE"

    # Invoice meta
    from datetime import datetime
    inv_date = datetime.strptime(invoice["date"], "%Y-%m-%d").strftime("%d %b %Y")
    due_date = ""
    if invoice.get("dueDate"):
        due_date = datetime.strptime(invoice["dueDate"], "%Y-%m-%d").strftime("%d %b %Y")

    meta_html = f"""
        <p><strong>Invoice No:</strong> {invoice["id"]}</p>
        <p><strong>Date:</strong> {inv_date}</p>
    """
    if due_date:
        meta_html += f'<p><strong>Due Date:</strong> {due_date}</p>'
    if is_export and business.get("lutNumber"):
        meta_html += f'<p><strong>LUT No:</strong> {business["lutNumber"]}</p>'

    # From section
    from_html = f"""
        <div class="party-label">From</div>
        <div class="party-name">{business["firmName"]}</div>
        <p>{business["address"]}</p>
        <p>{business["city"]}, {business["state"]} &mdash; {business["pincode"]}</p>
        <p>GSTIN: {business["gstin"]}</p>
        <p>PAN: {business["pan"]}</p>
    """

    # Bill To section
    billto_html = f"""
        <div class="party-label">Bill To</div>
        <div class="party-name">{client["name"]}</div>
        <p>{client["address"]}</p>
    """
    if client.get("city"):
        billto_html += f'<p>{client["city"]}, {client["country"]}</p>'
    else:
        billto_html += f'<p>{client["country"]}</p>'

    if client.get("gstin") and client["gstin"]:
        billto_html += f'<p>GSTIN: {client["gstin"]}</p>'
    if client.get("businessNumber"):
        billto_html += f'<p>BN: {client["businessNumber"]}</p>'
    if client.get("companyNumber"):
        billto_html += f'<p>Company No: {client["companyNumber"]}</p>'
    if client.get("vat"):
        billto_html += f'<p>VAT: {client["vat"]}</p>'

    # Line items table
    rows_html = ""
    for i, item in enumerate(invoice["lineItems"], 1):
        amt_str = f"{item['amount']:,.2f}"
        rate_str = f"{item['rate']:,.2f}"
        rows_html += f"""
        <tr>
            <td>{i}</td>
            <td>{item["description"]}</td>
            <td>{item["sac"]}</td>
            <td>{item["quantity"]}</td>
            <td>{rate_str}</td>
            <td>{amt_str}</td>
        </tr>
        """

    items_html = f"""
    <table class="items">
        <thead>
            <tr>
                <th style="width:30px">#</th>
                <th>Description</th>
                <th style="width:70px">SAC</th>
                <th style="width:40px">Qty</th>
                <th style="width:110px">Rate ({currency})</th>
                <th style="width:110px">Amount ({currency})</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    """

    # Totals
    subtotal = invoice["subtotal"]
    total = invoice["total"]

    totals_rows = f"""
        <tr>
            <td>Subtotal</td>
            <td>{fmt_amount(subtotal, currency)}</td>
        </tr>
    """

    tax = invoice.get("tax", {})
    if is_export:
        totals_rows += """
        <tr class="secondary">
            <td>GST</td>
            <td>NIL (Export of Services)</td>
        </tr>
        """
    elif tax.get("cgst"):
        totals_rows += f"""
        <tr class="secondary">
            <td>CGST @ 9%</td>
            <td>{fmt_amount(tax["cgst"], "INR")}</td>
        </tr>
        <tr class="secondary">
            <td>SGST @ 9%</td>
            <td>{fmt_amount(tax["sgst"], "INR")}</td>
        </tr>
        """
    elif tax.get("igst"):
        totals_rows += f"""
        <tr class="secondary">
            <td>IGST @ 18%</td>
            <td>{fmt_amount(tax["igst"], "INR")}</td>
        </tr>
        """

    if currency != "INR" and invoice.get("exchangeRate"):
        totals_rows += f"""
        <tr class="secondary">
            <td>Exchange Rate</td>
            <td>1 {currency} = INR {invoice["exchangeRate"]:.2f}</td>
        </tr>
        """

    totals_rows += f"""
        <tr class="total-row">
            <td>Total</td>
            <td>{fmt_amount(total, currency)}</td>
        </tr>
    """

    if currency != "INR" and invoice.get("totalINR"):
        totals_rows += f"""
        <tr class="secondary">
            <td>Total in INR</td>
            <td>{fmt_indian(invoice["totalINR"])}</td>
        </tr>
        """

    words = amount_in_words(total, currency)

    # Bank details
    bank = business.get("bank", {})
    bank_rows = f"""
        <tr><td>Account Name</td><td>{bank.get("accountName", "")}</td></tr>
        <tr><td>Account Number</td><td>{bank.get("accountNumber", "")}</td></tr>
        <tr><td>IFSC</td><td>{bank.get("ifsc", "")}</td></tr>
        <tr><td>Bank</td><td>{bank.get("name", "")}, {bank.get("branch", "")}</td></tr>
    """
    if bank.get("upi"):
        bank_rows += f'<tr><td>UPI</td><td>{bank["upi"]}</td></tr>'

    # Full HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <style>{INVOICE_CSS}</style>
</head>
<body>
<div class="invoice-container">
    <div class="header">
        <h1>{title}</h1>
        <div class="invoice-meta">
            {meta_html}
        </div>
    </div>

    <div class="parties">
        <div class="party">
            {from_html}
        </div>
        <div class="party">
            {billto_html}
        </div>
    </div>

    {items_html}

    <div class="totals-section">
        <table class="totals">
            {totals_rows}
        </table>
    </div>

    <div class="amount-words">
        Amount in words: {words}
    </div>

    <div class="bank-details">
        <h3>Bank Details</h3>
        <table class="bank">
            {bank_rows}
        </table>
    </div>

    <div class="footer">
        <div class="notes">
            <p><strong>Notes:</strong> Thank you for your business.</p>
            <p><strong>Terms &amp; Conditions:</strong></p>
            <p>Payment is due within 30 days of invoice date.</p>
            <p>Late payments may attract interest at 18% per annum.</p>
        </div>
        <div class="signatory">
            <div class="firm-name">For {business["firmName"]}</div>
            <div class="sig-line">Authorized Signatory</div>
        </div>
    </div>
</div>
</body>
</html>"""
    return html


def generate_pdf(invoice_id):
    """Generate a PDF for the given invoice ID."""
    try:
        from weasyprint import HTML
    except ImportError:
        print("Error: weasyprint not installed. Run: pip install weasyprint")
        sys.exit(1)

    business = load_json(DATA / "business.json")
    clients = load_json(DATA / "clients.json")
    invoices = load_json(DATA / "invoices.json")

    # Find the invoice
    invoice = None
    for inv in invoices:
        if inv["id"] == invoice_id:
            invoice = inv
            break
    if not invoice:
        print(f"Error: Invoice '{invoice_id}' not found")
        sys.exit(1)

    # Find the client
    client = None
    for c in clients:
        if c["id"] == invoice["clientId"]:
            client = c
            break
    if not client:
        print(f"Error: Client '{invoice['clientId']}' not found")
        sys.exit(1)

    # Generate HTML and PDF
    html = build_html(invoice, client, business)

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    safe_id = invoice_id.replace("/", "-")
    pdf_path = PDF_DIR / f"{safe_id}.pdf"

    HTML(string=html).write_pdf(str(pdf_path))
    print(f"PDF generated: {pdf_path}")
    return str(pdf_path)


def generate_all():
    """Generate PDFs for all invoices."""
    invoices = load_json(DATA / "invoices.json")
    for inv in invoices:
        generate_pdf(inv["id"])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_pdf.py <invoice_id>")
        print("       python generate_pdf.py --all")
        sys.exit(1)

    if sys.argv[1] == "--all":
        generate_all()
    else:
        invoice_id = sys.argv[1]
        generate_pdf(invoice_id)
