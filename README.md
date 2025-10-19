# Project Overview

This repository hosts a small toolbox for fetching Safety Data Sheets (SDS) from three vendors (Sigma-Aldrich, TCI, Thermo Fisher). The Python scripts now talk to each site directly over HTTPS using [`curl-cffi`](https://github.com/yifeikong/curl_cffi) where browser-grade TLS fingerprints are required. Playwright MCP remains in the tree only for manual inspection/debugging; the production scripts no longer depend on it.

## Quick start

```bash
python -m pip install -r requirements.txt
```

The requirements include `requests` and `curl-cffi`. No Node.js or Playwright setup is needed to run the downloaders.

## SDS scripts

| Script | Purpose | Notes |
| --- | --- | --- |
| `scripts/aldrich_mcp.py` | Download Sigma-Aldrich SDS PDFs for one product and language list. | Uses `curl-cffi` Chrome impersonation to obtain Akamai cookies, then fetches PDFs directly. |
| `scripts/tci_get.py` | Save a TCI product page (HTML) and optionally download SDS PDFs. | Same browser-style session as above; emits a JSON summary. |
| `scripts/thermofisher_sds.py` | Crawl Thermo Fisher category/product APIs and download SDS PDFs. | Continues to use the public JSON APIs with plain `requests`. |

Each script prints a JSON summary so the caller can capture output paths and metadata.

## Optional: Playwright MCP server

If you still need a Playwright MCP server for interactive debugging:

```bash
npm install
npm run playwright:install
```

- `npm run mcp` – launch the MCP server with a visible browser.
- `npm run mcp:headless` – launch in headless mode.

Add the server to your MCP client configuration as:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npm",
      "args": ["run", "mcp"]
    }
  }
}
```

The configuration file `mcp.config.json` is untouched from the original setup and remains available if you need a Playwright-backed session for analysis.

## Repository layout

- `scripts/` – Python helpers for each provider plus shared utilities.
- `data/` – Default output directory for PDFs and cached sessions.
- `README_*` – Provider-specific documentation (English and Korean).
- `.playwright-mcp-output/` – Default log location when the MCP server runs (ignored by Git).

---
Last updated: 2025-10-19
