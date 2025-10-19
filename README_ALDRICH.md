# Sigma-Aldrich SDS Downloader

Helper script for collecting Sigma-Aldrich Safety Data Sheets (SDS) without Playwright. The downloader now relies on [`curl-cffi`](https://github.com/yifeikong/curl_cffi) to impersonate a recent Chrome TLS fingerprint so that the public SDS endpoints accept the requests.

## Requirements
- Python 3.11+
- `requests`
- `curl-cffi` (provides the browser-style HTTP client)

Install the dependencies with:

```bash
python -m pip install -r requirements.txt
```

## Script
- Path: `scripts/aldrich_mcp.py`
- Purpose: Fetch SDS PDFs for the requested languages using direct HTTPS calls (no Playwright MCP, no Node helper).

### Usage
```bash
python scripts/aldrich_mcp.py \
  --product-url https://www.sigmaaldrich.com/KR/ko/product/sigald/34873 \
  --languages ko en \
  --output-dir data/sds_aldrich
```

### Options
| Option | Description | Default |
| --- | --- | --- |
| `--product-url` | Product detail URL (e.g. `https://www.sigmaaldrich.com/KR/ko/product/sigald/34873`) | required |
| `-l`, `--languages` | Language codes to download (e.g. `ko en`). If omitted, the language encoded in the URL is used. | URL language |
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

When a language is unavailable the script reports the HTTP status and skips the file. It exits with status code `1` if no SDS files are downloaded.

## Batch test helper
`scripts/test_aldrich_multiple.py` still iterates over a preset list of product URLs and reuses `aldrich_mcp.py` to verify availability after updates.

## How it works
1. Parse the product URL (country/language/brand/product number).
2. Issue a priming request with `curl-cffi` (Chrome 120 impersonation) to obtain the necessary Akamai cookies.
3. Request each SDS PDF directly over HTTPS with the prepared session.
4. Save PDFs as `{product}_{country}_{language}.pdf` in the configured output directory and emit a JSON summary.

## Troubleshooting
| Symptom | Cause | Resolution |
| --- | --- | --- |
| HTTP 404 | SDS not offered for the language/product | Confirm in the browser or try a different language |
| Timeout | Upstream site is slow or blocking traffic | Retry later; ensure outbound HTTPS is allowed |
| `RequestsError` | Akamai rejected the TLS/client fingerprint | Upgrade `curl-cffi` and rerun; try a different impersonation profile |

---
Last updated: 2025-10-19
