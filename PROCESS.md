# Small Group — Invoicing Process

## Step-by-Step Workflow

### Step 1: Business Details
Maintain firm details in `data/business.json`. Update when anything changes (bank, address, LUT, etc).

**What's needed:**
- Firm name, address, GSTIN, PAN
- Bank details (for invoices)
- LUT number (for export invoices — filed on GST portal)
- Invoice prefix and financial year
- Branding assets: logo image, authorized signatory image

### Step 2: Client Registry
Maintain all clients in `data/clients.json`. Each client needs:
- Company name and full address
- Country, currency
- Type: `domestic` (with GSTIN, state) or `export`
- Contact person, email
- Bank keywords (how payments appear in HDFC/Payoneer statements)
- Work type: Software Dev (SAC 998314) or AI Dev (SAC 998315)

### Step 3: Import Payments
When new bank statements/Payoneer reports arrive:
1. Parse the CSV files
2. Match each credit to a known client using bank keywords + Payoneer descriptions
3. Flag unmatched payments for manual identification
4. Record all matched payments in `data/transactions.json`

### Step 4: Invoice Registry
Before generating any invoices, create/update `data/invoice-registry.md`:
- List ALL invoices to be created, in chronological order
- Show: invoice number, date, client, amount, currency, line item description
- **Get user verification** before proceeding
- This ensures correct sequencing (SG/2025-26/001, 002, 003...)

### Step 5: Generate Invoice Markdown
For each approved invoice:
1. Create markdown in `invoices/md/{filename}.md` using the template
2. User reviews the markdown for correctness

### Step 6: Convert to PDF
Only after markdown is approved:
1. Convert to PDF: `invoices/pdf/{filename}.pdf`
2. Uses weasyprint with branded CSS template

### Step 7: Update Records
- Save invoices to `data/invoices.json`
- Update `nextInvoiceNumber` in `data/business.json`
- Match payments to invoices in `data/transactions.json`

---

## Branding & Template Improvements

To improve the invoice template, the user should provide:

1. **Logo** — PNG/SVG image file → save as `assets/logo.png`
2. **Authorized Signatory** — Signature image → save as `assets/signature.png`
3. **Color scheme** — Primary color for headers/accents (default: dark blue)
4. **Font preference** — (default: clean sans-serif like Inter or Helvetica)

The PDF generator will use an HTML/CSS template in `assets/invoice-template.css` for consistent branding.

---

## For Future Use

When you have new payments to invoice:
1. Drop the CSV in `statements/`
2. Ask Claude to "process new statements"
3. Review the registry, approve, generate

When adding a new client:
1. Provide: company name, address, country, currency, contact, work type
2. Claude adds to `data/clients.json`
3. Future payments auto-match via bank keywords
