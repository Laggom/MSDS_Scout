# Sigma-Aldrich SDS Downloader

This repository bundles a Playwright MCP-based helper for collecting Sigma-Aldrich Safety Data Sheets (SDS). Once Playwright MCP is installed (`npm install`, `npm run playwright:install`), the Python script can reuse the same configuration used for the TCI workflow.

## Requirements
- Python 3.11+
- Node.js 18+
- Playwright MCP dependencies (`npm install` in the repo root)
- Playwright browser binaries (`npm run playwright:install`)

## Script
- Path: `scripts/aldrich_mcp.py`
- Purpose: Uses the Node helper `scripts/download_sds_with_playwright.js` to fetch SDS PDFs for the requested languages.

### Usage
```bash
python scripts/aldrich_mcp.py --product-url https://www.sigmaaldrich.com/KR/ko/product/sigald/34873 --languages ko en --output-dir data/sds_aldrich
```

### Options
| Option | Description | Default |
| --- | --- | --- |
| `--product-url` | Product detail URL (e.g. `https://www.sigmaaldrich.com/KR/ko/product/sigald/34873`) | required |
| `-l`, `--languages` | Language codes to download (e.g. `ko en`). If omitted, the language encoded in the product URL is used. | URL language |
| `-o`, `--output-dir` | Directory for downloaded PDFs | `data/sds_aldrich` |

### Example output
```
=== SDS Download Summary ===
{
  "provider": "aldrich",
  "product": "34873",
  "downloads": [
    {
      "path": "C:\\...\\34873_KR_EN.pdf",
      "languages": ["en"],
      "sourceUrl": "https://www.sigmaaldrich.com/KR/en/sds/sigald/34873"
    },
    {
      "path": "C:\\...\\34873_KR_KO.pdf",
      "languages": ["ko"],
      "sourceUrl": "https://www.sigmaaldrich.com/KR/ko/sds/sigald/34873"
    }
  ],
  "productUrl": "https://www.sigmaaldrich.com/KR/ko/product/sigald/34873"
}
```

> If the requested language does not exist, the helper prints the HTTP status and skips the file. The script exits with status code `1` when no SDS files are downloaded.

## Batch test helper
`scripts/test_aldrich_multiple.py` iterates over a preset list of product URLs and reuses `aldrich_mcp.py` to verify availability after updates.

## How it works
1. Parse the product URL (country/language/brand/product number).
2. Refresh cookies and headers through Playwright MCP (`scripts/fetchHeaders.js`).
3. Use the Node helper to download each SDS PDF via Playwright''s `APIRequestContext`.
4. Save PDFs as `{product}_{country}_{language}.pdf` in the configured output directory.

## Troubleshooting
| Symptom | Cause | Resolution |
| --- | --- | --- |
| HTTP 404 | SDS not offered for the language/product | Confirm in the browser or try a different language |
| Timeout | Upstream site is slow | Retry later or inspect network connectivity |
| `Helper failed` | Node helper exited abnormally | Inspect the printed stdout/stderr for details |

---
Last updated: 2025-10-18
