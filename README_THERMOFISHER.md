# Thermo Fisher SDS Downloader

Utility script for downloading Safety Data Sheets (SDS) from Thermo Fisher by calling the public documents API. No authentication is required; PDFs are pulled from the CDN once the API response lists the available assets.

## Requirements
- Python 3.11+
- `requests` (already listed in `requirements.txt`)

## Script
- Path: `scripts/thermofisher_sds.py`
- Purpose: Crawl Thermo Fisher Chemicals product/category pages, resolve all released child SKUs, and download SDS PDFs for the requested languages.

### Usage
- Download every product in a category (first 100 results shown here):
  ```bash
  python scripts/thermofisher_sds.py \
    --category-url https://chemicals.thermofisher.kr/apac/search/category/80013495 \
    --max-products 100 \
    --languages ko en \
    --output-dir data/sds_thermofisher
  ```
- Download a specific product (command can be repeated for multiple URLs):
  ```bash
  python scripts/thermofisher_sds.py \
    --product-url https://chemicals.thermofisher.kr/apac/product/B21525 \
    --languages ko \
    --output-dir data/sds_thermofisher
  ```

### Options
| Option | Description | Default |
| --- | --- | --- |
| `--category-url` | Category listing URL to crawl | required (or `--product-url`) |
| `--product-url` | Product page URL (repeatable) | required (or `--category-url`) |
| `-l`, `--languages` | Preferred languages, e.g. `ko en`. The script automatically maps `ko-kr` → `ko`, etc. | `ko en` |
| `-o`, `--output-dir` | Directory for PDFs | `data/sds_thermofisher` |
| `--page-size` | Category page size (controls API pagination) | `30` |
| `--max-products` | Limit the number of category items processed | all products |

### Example output
```
=== SDS Download Summary ===
{
  "provider": "thermofisher",
  "product": "category",
  "downloads": [
    {
      "path": "C:\\...\\B21525_KO.pdf",
      "languages": ["ko"],
      "sourceUrl": "https://assets.thermofisher.com/directwebviewer/private/results.aspx?page=NewSearch&LANGUAGE=d__KO&SUBFORMAT=d__KOSD&SKU=ALFAAB21525&PLANT=d__ALF",
      "metadata": {
        "rootSku": "B21525"
      }
    },
    {
      "path": "C:\\...\\B21525_EN.pdf",
      "languages": ["en"],
      "sourceUrl": "https://assets.thermofisher.com/directwebviewer/private/results.aspx?page=NewSearch&LANGUAGE=d__EN&SUBFORMAT=d__ENSD&SKU=ALFAAB21525&PLANT=d__ALF",
      "metadata": {
        "rootSku": "B21525"
      }
    }
  ],
  "productUrl": "https://chemicals.thermofisher.kr/apac/search/category/80013495",
  "notes": {
    "mode": "category",
    "categoryId": "80013495",
    "totalProducts": 100,
    "products": ["B21525", "..."]
  }
}
```

## How it works
1. Resolve products either by crawling a category or by searching for the provided product URLs.
2. Call `/apac/api/search/catalog/child` to enumerate all released child SKUs.
3. Request `/apac/api/document/search/sds` with the child SKUs and target language to obtain the viewer URL.
4. Download the returned PDF and store it as `{rootSku}_{LANG}.pdf`.

## Notes
- The SDS API currently returns a viewer URL that still serves a binary PDF; the script validates the content type before saving.
- Category mode can produce a large number of PDFs—use `--max-products` to throttle if needed.
- The Thermo Fisher APIs expect the `country` header to be set to `kr` and a random `com-tf-dye` value; the client handles this automatically.

---
Last updated: 2025-10-19
