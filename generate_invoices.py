#!/usr/bin/env python3
"""
Invoice Generator for Small Group
Generates markdown invoices from invoice data, then converts to PDF.
Usage:
  python3 generate_invoices.py md       # Generate markdown only
  python3 generate_invoices.py pdf      # Generate PDF from existing markdown
  python3 generate_invoices.py all      # Generate both
  python3 generate_invoices.py md 001   # Generate specific invoice markdown
"""

import json, os, sys
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
MD_DIR = BASE_DIR / "invoices" / "md"
PDF_DIR = BASE_DIR / "invoices" / "pdf"
ASSETS_DIR = BASE_DIR / "assets"

def load_json(filename):
    with open(DATA_DIR / filename) as f:
        return json.load(f)

def indian_format(amount):
    """Format number in Indian style: 1,23,456.78"""
    if amount < 0:
        return "-" + indian_format(-amount)
    s = f"{amount:.2f}"
    parts = s.split(".")
    integer = parts[0]
    decimal = parts[1]
    if len(integer) <= 3:
        return f"{integer}.{decimal}"
    last3 = integer[-3:]
    rest = integer[:-3]
    groups = []
    while rest:
        groups.insert(0, rest[-2:])
        rest = rest[:-2]
    return ",".join(groups) + "," + last3 + "." + decimal

def comma_format(amount):
    """Standard comma formatting: 1,234,567.89"""
    return f"{amount:,.2f}"

def format_amount(amount, currency):
    if currency == "INR":
        return indian_format(amount)
    return comma_format(amount)

def number_to_words(amount, currency):
    """Convert number to words for invoice."""
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven",
            "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen",
            "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty",
            "Sixty", "Seventy", "Eighty", "Ninety"]

    def _words(n):
        if n == 0:
            return ""
        if n < 20:
            return ones[n]
        if n < 100:
            return tens[n // 10] + (" " + ones[n % 10] if n % 10 else "")
        if n < 1000:
            return ones[n // 100] + " Hundred" + (" and " + _words(n % 100) if n % 100 else "")
        if n < 100000:
            return _words(n // 1000) + " Thousand" + (" " + _words(n % 1000) if n % 1000 else "")
        if n < 10000000:
            return _words(n // 100000) + " Lakh" + (" " + _words(n % 100000) if n % 100000 else "")
        return _words(n // 10000000) + " Crore" + (" " + _words(n % 10000000) if n % 10000000 else "")

    integer_part = int(amount)
    decimal_part = round((amount - integer_part) * 100)

    currency_names = {
        "USD": "US Dollars",
        "CAD": "Canadian Dollars",
        "INR": "Indian Rupees",
        "EUR": "Euros",
        "GBP": "British Pounds",
        "AUD": "Australian Dollars",
    }
    cname = currency_names.get(currency, currency)

    words = _words(integer_part)
    if decimal_part:
        words += f" and {decimal_part}/100"
    return f"{cname} {words} Only"

def format_date(date_str):
    """Convert 2025-07-29 to 29 Jul 2025"""
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return d.strftime("%d %b %Y")

def due_date(date_str):
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return (d + timedelta(days=30)).strftime("%d %b %Y")

def generate_markdown(inv, business, clients):
    client = next(c for c in clients if c["id"] == inv["clientId"])
    is_export = client["type"] == "export"
    curr = inv["currency"]
    amount = inv["total"]
    rate = inv.get("exchangeRate")
    inr_total = inv.get("totalINR", amount)

    # Header
    if is_export:
        title = "TAX INVOICE — EXPORT OF SERVICES"
    elif client.get("stateCode") == business.get("stateCode"):
        title = "TAX INVOICE"
    else:
        title = "TAX INVOICE"

    # Build client address block
    client_addr = f"**{client['name']}**\n"
    client_addr += f"{client['address']}\n"
    if client.get("city"):
        client_addr += f"{client['city']}\n"
    client_addr += f"{client['country']}"
    if client.get("vat"):
        client_addr += f"\nVAT: {client['vat']}"
    if client.get("businessNumber"):
        client_addr += f"\nBN: {client['businessNumber']}"
    if client.get("gstin") and client["gstin"]:
        client_addr += f"\nGSTIN: {client['gstin']}"

    # Line items table
    items = inv["lineItems"]
    items_header = f"| # | Description | SAC | Qty | Rate ({curr}) | Amount ({curr}) |"
    items_sep = "|---|-------------|-----|-----|------------|--------------|"
    items_rows = []
    for i, item in enumerate(items, 1):
        items_rows.append(
            f"| {i} | {item['description']} | {item['sac']} | {item['quantity']} | {format_amount(item['rate'], curr)} | {format_amount(item['amount'], curr)} |"
        )

    # Tax section
    subtotal_line = f"| **Subtotal** | {curr} {format_amount(amount, curr)} |"
    tax_lines = []
    tax = inv.get("tax", {})
    if is_export:
        lut = business.get("lutNumber", "")
        if lut:
            tax_lines.append(f"| GST | NIL (Export under LUT — {lut}) |")
        else:
            tax_lines.append("| GST | NIL (Export of Services) |")
    elif tax.get("type") == "igst":
        igst_amt = tax.get("igst", 0)
        tax_lines.append(f"| IGST @ 18% | INR {indian_format(igst_amt)} |")
    elif tax.get("type") == "cgst_sgst":
        cgst = tax.get("cgst", 0)
        sgst = tax.get("sgst", 0)
        tax_lines.append(f"| CGST @ 9% | INR {indian_format(cgst)} |")
        tax_lines.append(f"| SGST @ 9% | INR {indian_format(sgst)} |")

    if curr != "INR" and rate:
        tax_lines.append(f"| Exchange Rate | 1 {curr} = INR {rate:.2f} |")

    total_line = f"| **Total** | **{curr} {format_amount(amount, curr)}** |"

    if curr != "INR" and inr_total:
        tax_lines.append(f"| Total in INR | INR {indian_format(inr_total)} |")

    amount_words = number_to_words(amount, curr)

    # Bank details
    bank = business["bank"]

    # LUT line
    lut_line = ""
    if is_export and business.get("lutNumber"):
        lut_line = f"**LUT No:** {business['lutNumber']}\n"

    md = f"""# {title}

---

**Invoice No:** {inv['id']}
**Date:** {format_date(inv['date'])}
**Due Date:** {due_date(inv['date'])}
{lut_line}
---

### From

**{business['firmName']}**
{business['address']}
{business['city']}, {business['state']} — {business['pincode']}
GSTIN: {business['gstin']}
PAN: {business['pan']}

### Bill To

{client_addr}

---

{items_header}
{items_sep}
{chr(10).join(items_rows)}

---

|  | |
|---|---|
{subtotal_line}
{chr(10).join(f"| {line.split('|')[1].strip()} | {line.split('|')[2].strip()} |" if line.startswith("|") else line for line in tax_lines)}
{total_line}

**Amount in words:** {amount_words}

---

### Bank Details

| | |
|---|---|
| Account Name | {bank['accountName']} |
| Account Number | {bank['accountNumber']} |
| IFSC | {bank['ifsc']} |
| Bank | {bank['name']}, {bank['branch']} |

---

**Notes:** Thank you for your business.

**Terms & Conditions:**
Payment is due within 30 days of invoice date.
Late payments may attract interest at 18% per annum.

---

For **{business['firmName']}**

_Authorized Signatory_
"""
    return md.strip() + "\n"

def generate_pdf(md_path, pdf_path):
    """Convert markdown to branded PDF using weasyprint."""
    import markdown as md_lib

    os.environ.setdefault("DYLD_FALLBACK_LIBRARY_PATH", "/opt/homebrew/lib")

    from weasyprint import HTML

    logo_path = ASSETS_DIR / "Logo.png"
    sig_path = ASSETS_DIR / "Chandan signature.png"

    css = f"""
    @page {{
        size: A4;
        margin: 20mm 18mm 20mm 18mm;
        @bottom-center {{
            content: "Small Group | GSTIN: 09AFPFS6465K1Z1 | UDYAM-UP-28-0161239";
            font-size: 7px;
            color: #999;
        }}
    }}
    body {{
        font-family: Helvetica, Arial, sans-serif;
        font-size: 10.5px;
        color: #333;
        line-height: 1.5;
    }}
    h1 {{
        text-align: center;
        font-size: 16px;
        color: #000;
        letter-spacing: 3px;
        margin-bottom: 0;
        padding: 12px 0;
        border-top: 3px solid #000;
        border-bottom: 1px solid #000;
    }}
    h3 {{
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #000;
        margin-top: 14px;
        margin-bottom: 4px;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        margin: 6px 0;
        font-size: 10px;
    }}
    table th, table td {{
        border: 1px solid #ddd;
        padding: 5px 7px;
        text-align: left;
    }}
    table th {{
        background-color: #000;
        color: #fff;
        font-weight: bold;
        font-size: 9px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    hr {{
        border: none;
        border-top: 1px solid #ddd;
        margin: 10px 0;
    }}
    strong {{ color: #000; }}
    p {{ margin: 3px 0; }}
    em {{ font-style: italic; color: #555; }}
    """

    with open(md_path, "r") as f:
        md_content = f.read()

    html_content = md_lib.markdown(md_content, extensions=["tables"])

    # Add logo at top and signature at bottom
    logo_html = ""
    if logo_path.exists():
        logo_html = f'<div style="text-align:right;margin-bottom:5px;"><img src="file://{logo_path}" style="height:50px;" /></div>'

    sig_html = ""
    if sig_path.exists():
        sig_html = f'<div style="margin-top:-10px;"><img src="file://{sig_path}" style="height:50px;" /></div>'

    # Replace "Authorized Signatory" text with image
    html_content = html_content.replace(
        "<em>Authorized Signatory</em>",
        f'{sig_html}<em>Authorized Signatory</em>'
    )

    full_html = f"""<html><head><style>{css}</style></head>
    <body>{logo_html}{html_content}</body></html>"""

    HTML(string=full_html, base_url=str(BASE_DIR)).write_pdf(str(pdf_path))

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "md"
    specific = sys.argv[2] if len(sys.argv) > 2 else None

    business = load_json("business.json")
    clients = load_json("clients.json")
    invoices = load_json("invoices.json")

    MD_DIR.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    for inv in invoices:
        inv_num = inv["id"].split("/")[-1]
        filename = f"SG-2025-26-{inv_num}"

        if specific and inv_num != specific:
            continue

        if mode in ("md", "all"):
            md_content = generate_markdown(inv, business, clients)
            md_path = MD_DIR / f"{filename}.md"
            with open(md_path, "w") as f:
                f.write(md_content)
            print(f"MD: {filename}.md")

        if mode in ("pdf", "all"):
            md_path = MD_DIR / f"{filename}.md"
            pdf_path = PDF_DIR / f"{filename}.pdf"
            if md_path.exists():
                generate_pdf(md_path, pdf_path)
                print(f"PDF: {filename}.pdf")
            else:
                print(f"SKIP (no md): {filename}")

if __name__ == "__main__":
    main()
