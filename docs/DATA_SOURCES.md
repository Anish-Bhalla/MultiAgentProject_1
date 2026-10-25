# Adding real public company documents

The bundled Markdown files and sales database are explicitly synthetic, so the project starts with a safe reproducible demo. To turn it into a real company research corpus, download documents yourself from sources whose terms permit your intended use and place them in `data/documents/`.

Good sources for Indian listed-company research:

- [NSE financial results filings](https://www.nseindia.com/companies-listing/corporate-filings-financial-results) — quarterly/annual financial results filed by listed companies.
- [NSE annual reports](https://www.nseindia.com/companies-listing/corporate-filings-annual-reports) — annual-report filings.
- [NSE corporate announcements](https://www.nseindia.com/companies-listing/corporate-filings-announcements) — company announcements and event filings.
- Investor-relations pages of the company — often best for investor presentations, results decks, and earnings-call audio/transcripts.
- [BSE India](https://www.bseindia.com/) — an alternative exchange source for announcements and results.

NSE filings are company-submitted information; the exchange may not independently verify each statement. Preserve the source URL, publication date and company/quarter in filenames or metadata. Do not treat every management forecast as a fact. Note that the included SQL database is fictional sales data: it is not the financial statement database for any company whose PDFs you add. Do not cross-compare those numbers until you build a matching structured data import.

## Suggested corpus for the portfolio project

Start with a single company and 6–9 documents so you can inspect answer quality:

1. Three consecutive quarterly results.
2. Three matching investor presentations.
3. Two or three earnings-call transcripts, if publicly available.

Use names such as `INFY_Q1_FY27_results.pdf` and `INFY_Q1_FY27_presentation.pdf`. The ingestion pipeline supports `.pdf`, `.md`, `.markdown` and `.txt`, then the citation metadata preserves the filename and PDF page number.

## Ingest the files

```bash
# Copy public PDFs into data/documents/ first
python -m scripts.ingest_documents
```

or use the **Re-index documents** button / `POST /api/documents/ingest` endpoint. The project intentionally does not bulk-download third-party company filings automatically: websites change, documents may be revised, and data-use terms vary.
