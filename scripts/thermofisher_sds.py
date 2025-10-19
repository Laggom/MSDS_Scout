#!/usr/bin/env python3
"""Download Thermo Fisher SDS PDFs via the public documents API."""

from __future__ import annotations

import argparse
import uuid
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple
from urllib.parse import quote_plus, urlparse

import requests

from sds_common import DownloadRecord, build_summary, normalize_languages, print_summary

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_HOST = "https://chemicals.thermofisher.kr"
APAC_BASE = f"{BASE_HOST}/apac"
CATEGORY_ENDPOINT = f"{APAC_BASE}/api/search/category"
SEARCH_ENDPOINT = f"{APAC_BASE}/api/search/catalog/keyword"
CHILD_ENDPOINT = f"{APAC_BASE}/api/search/catalog/child"
SDS_ENDPOINT = f"{APAC_BASE}/api/document/search/sds"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class ThermoFisherClient:
    """Minimal client for Thermo Fisher APAC APIs."""

    def __init__(self, country: str = "kr") -> None:
        self.country = country
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
            }
        )
        self._prefetched: set[str] = set()

    def _random_dye(self) -> str:
        return str(uuid.uuid4())

    def _headers(
        self,
        *,
        referer: str,
        accept: str = "application/json",
        content_type: Optional[str] = None,
    ) -> Dict[str, str]:
        headers: Dict[str, str] = {
            "Accept": accept,
            "Origin": BASE_HOST,
            "Referer": referer,
            "country": self.country,
            "com-tf-dye": self._random_dye(),
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        referer: str,
        timeout: int = 60,
        accept: str = "application/json",
        content_type: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, object]:
        headers = self._headers(
            referer=referer, accept=accept, content_type=content_type
        )
        response = self.session.request(
            method, url, headers=headers, timeout=timeout, **kwargs
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != "200":
            raise ValueError(f"API responded with error: {payload}")
        data = payload.get("data")
        if data is None:
            raise ValueError(f"API returned no data: {payload}")
        return data  # type: ignore[return-value]

    def ensure_page_loaded(self, url: str) -> None:
        """Load page once to establish cookies expected by API."""
        if url in self._prefetched:
            return
        response = self.session.get(url, headers={"User-Agent": USER_AGENT}, timeout=60)
        response.raise_for_status()
        self._prefetched.add(url)

    def fetch_category_page(
        self,
        category_id: str,
        *,
        page: int,
        page_size: int,
        language: str,
        referer: str,
    ) -> Dict[str, object]:
        payload = {
            "categoryId": category_id,
            "pageNo": page,
            "pageSize": page_size,
            "filter": "",
            "countryCode": self.country,
            "language": language,
        }
        return self._request_json(
            "POST",
            CATEGORY_ENDPOINT,
            referer=referer,
            content_type="application/json",
            json=payload,
        )

    def search_catalog(
        self,
        query: str,
        *,
        language: str,
        referer: str,
        page: int = 1,
        page_size: int = 10,
    ) -> Dict[str, object]:
        payload = {
            "countryCode": self.country,
            "language": language,
            "filter": "",
            "pageNo": page,
            "pageSize": page_size,
            "persona": "",
            "query": query,
        }
        return self._request_json(
            "POST",
            SEARCH_ENDPOINT,
            referer=referer,
            content_type="application/json",
            json=payload,
        )

    def fetch_child_skus(
        self, catalog_number: str, *, product_referer: str
    ) -> List[str]:
        data = self._request_json(
            "POST",
            CHILD_ENDPOINT,
            referer=product_referer,
            content_type="application/json",
            json={"catalogNumber": catalog_number},
        )
        children: List[Dict[str, str]] = data  # type: ignore[assignment]
        return [
            child["childCatalogNumber"]
            for child in children
            if child.get("childCatalogNumber")
            and (child.get("skuStatus") or "").upper() == "RELEASED"
        ]

    def resolve_product_from_search(
        self,
        query: str,
        *,
        language: str,
    ) -> Optional[str]:
        self.ensure_page_loaded(BASE_HOST)
        referer = f"{BASE_HOST}/"
        data = self.search_catalog(query, language=language, referer=referer)
        items: List[Dict[str, object]] = data.get("catalogResultDTOs", [])  # type: ignore[assignment]
        if not items:
            return None
        first = items[0]
        child_sku = first.get("childCatalogNumber")
        if not isinstance(child_sku, str) or not child_sku.strip():
            return None
        return f"{BASE_HOST}/apac/product/{child_sku.strip()}"

    def fetch_sds_url(
        self,
        child_skus: Sequence[str],
        *,
        language: str,
        product_referer: str,
    ) -> str:
        params = {
            "childSkus": ",".join(child_skus),
            "language": language,
        }
        data = self._request_json(
            "GET",
            SDS_ENDPOINT,
            referer=product_referer,
            params=params,
        )
        url = data if isinstance(data, str) else data.get("data")  # type: ignore[arg-type]
        if not isinstance(url, str) or not url.startswith("http"):
            raise ValueError(f"No SDS URL returned for {child_skus}")
        return url

    def download_pdf(
        self,
        pdf_url: str,
        *,
        product_referer: str,
        timeout: int = 120,
    ) -> requests.Response:
        headers = self._headers(
            referer=product_referer,
            accept="application/pdf,application/octet-stream,*/*",
        )
        response = self.session.get(pdf_url, headers=headers, timeout=timeout)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").lower()
        if "pdf" not in content_type:
            raise ValueError(f"Unexpected content type: {content_type}")
        return response


def extract_last_segment(url: str, keyword: str) -> str:
    parsed = urlparse(url)
    parts = [segment for segment in parsed.path.split("/") if segment]
    if keyword in parts:
        idx = parts.index(keyword)
        if idx + 1 < len(parts):
            return parts[idx + 1]
    if parts:
        return parts[-1]
    raise ValueError(f"Could not extract segment from {url}")


def resolve_languages(languages: Iterable[str]) -> List[str]:
    normalized = normalize_languages(languages)
    if not normalized:
        return ["ko"]
    resolved = {lang.split("-")[0] for lang in normalized}
    return sorted(resolved)


def iter_category_products(
    client: ThermoFisherClient,
    category_id: str,
    *,
    language: str,
    page_size: int,
    max_products: Optional[int],
) -> Iterator[Dict[str, str]]:
    category_url = f"{APAC_BASE}/search/category/{category_id}"
    client.ensure_page_loaded(category_url)
    fetched = 0
    page = 1

    while True:
        data = client.fetch_category_page(
            category_id,
            page=page,
            page_size=page_size,
            language=language,
            referer=category_url,
        )
        results: List[Dict[str, str]] = data.get("catalogResultDTOs", [])  # type: ignore[assignment]
        if not results:
            break
        for product in results:
            yield product
            fetched += 1
            if max_products is not None and fetched >= max_products:
                return
        count = data.get("count", fetched)
        if fetched >= count:
            break
        page += 1


def collect_child_skus(
    client: ThermoFisherClient,
    root_sku: str,
    seed_child_sku: str,
) -> List[str]:
    product_url = f"{APAC_BASE}/product/{root_sku}"
    client.ensure_page_loaded(product_url)
    child_skus = client.fetch_child_skus(
        seed_child_sku,
        product_referer=product_url,
    )
    if not child_skus:
        # fallback to single known child
        child_skus = [seed_child_sku]
    return sorted(set(child_skus))


def download_for_product(
    client: ThermoFisherClient,
    *,
    root_sku: str,
    child_skus: Sequence[str],
    languages: Sequence[str],
    output_dir: Path,
) -> List[DownloadRecord]:
    product_url = f"{APAC_BASE}/product/{root_sku}"
    records: List[DownloadRecord] = []
    for language in languages:
        try:
            pdf_url = client.fetch_sds_url(
                child_skus,
                language=language,
                product_referer=product_url,
            )
            response = client.download_pdf(
                pdf_url,
                product_referer=product_url,
            )
            file_name = f"{root_sku}_{language.upper()}.pdf"
            destination = output_dir / file_name
            destination.write_bytes(response.content)
            records.append(
                DownloadRecord(
                    path=destination,
                    languages=[language],
                    source_url=pdf_url,
                    metadata={"rootSku": root_sku},
                )
            )
            print(f"[OK] {root_sku} ({language}) -> {destination}")
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] {root_sku} ({language}): {exc}")
    return records


def handle_category_mode(
    client: ThermoFisherClient,
    *,
    category_url: str,
    languages: Sequence[str],
    page_size: int,
    max_products: Optional[int],
    output_dir: Path,
) -> Tuple[List[DownloadRecord], Dict[str, object]]:
    category_id = extract_last_segment(category_url, "category")
    records: List[DownloadRecord] = []
    processed: List[str] = []
    for product in iter_category_products(
        client,
        category_id,
        language=languages[0],
        page_size=page_size,
        max_products=max_products,
    ):
        root = product.get("rootCatalogNumber")
        child = product.get("childCatalogNumber")
        if not root or not child:
            print(f"[WARN] Skipping product entry without SKUs: {product}")
            continue
        child_skus = collect_child_skus(client, root, child)
        product_records = download_for_product(
            client,
            root_sku=root,
            child_skus=child_skus,
            languages=languages,
            output_dir=output_dir,
        )
        if product_records:
            processed.append(root)
            records.extend(product_records)
    notes: Dict[str, object] = {
        "mode": "category",
        "categoryId": category_id,
        "totalProducts": len(processed),
        "products": processed,
    }
    return records, notes


def handle_product_mode(
    client: ThermoFisherClient,
    *,
    product_urls: Sequence[str],
    languages: Sequence[str],
    output_dir: Path,
) -> Tuple[List[DownloadRecord], Dict[str, object]]:
    records: List[DownloadRecord] = []
    processed: List[str] = []
    for url in product_urls:
        root = extract_last_segment(url, "product")
        client.ensure_page_loaded(url)
        search_referer = url
        try:
            data = client.search_catalog(
                root,
                language=languages[0],
                referer=search_referer,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] Search failed for {root}: {exc}")
            continue
        results: List[Dict[str, str]] = data.get("catalogResultDTOs", [])  # type: ignore[assignment]
        if not results:
            print(f"[WARN] No catalog results for {root}")
            continue
        child = results[0].get("childCatalogNumber", root)
        child_skus = collect_child_skus(client, root, child)
        product_records = download_for_product(
            client,
            root_sku=root,
            child_skus=child_skus,
            languages=languages,
            output_dir=output_dir,
        )
        if product_records:
            processed.append(root)
            records.extend(product_records)
    notes: Dict[str, object] = {"mode": "product", "products": processed}
    return records, notes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--product-url",
        action="append",
        dest="product_urls",
        help="Product page URL (can be provided multiple times).",
    )
    target.add_argument(
        "--search-term",
        help="Search by material name or CAS number and download SDS for the first product result.",
    )
    target.add_argument(
        "--category-url",
        help="Category listing URL on chemicals.thermofisher.kr.",
    )
    parser.add_argument(
        "-l",
        "--languages",
        nargs="+",
        default=["ko", "en"],
        help="Preferred languages (e.g. ko en). Defaults to ko en.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default="data/sds_thermofisher",
        help="Directory for downloaded PDFs (default: data/sds_thermofisher).",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=30,
        help="Category page size (default: 30).",
    )
    parser.add_argument(
        "--max-products",
        type=int,
        default=None,
        help="Limit number of products processed from a category.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = (REPO_ROOT / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    languages = resolve_languages(args.languages)
    client = ThermoFisherClient()
    all_records: List[DownloadRecord] = []
    notes: Dict[str, object] = {}
    product_url = None

    try:
        if args.category_url:
            all_records, notes = handle_category_mode(
                client,
                category_url=args.category_url,
                languages=languages,
                page_size=args.page_size,
                max_products=args.max_products,
                output_dir=output_dir,
            )
            product_url = args.category_url
        else:
            product_urls: List[str] = list(args.product_urls or [])
            if args.search_term:
                resolved = client.resolve_product_from_search(
                    args.search_term,
                    language=languages[0],
                )
                if not resolved:
                    print(f"No Thermo Fisher product found for search term '{args.search_term}'.")
                    raise SystemExit(1)
                print(f"Resolved search term '{args.search_term}' to: {resolved}")
                if resolved not in product_urls:
                    product_urls.insert(0, resolved)
                notes["searchTerm"] = args.search_term
            if not product_urls:
                print("Please provide at least one --product-url or a --search-term.")
                raise SystemExit(1)
            all_records, notes = handle_product_mode(
                client,
                product_urls=product_urls,
                languages=languages,
                output_dir=output_dir,
            )
            product_url = product_urls[0]

    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {exc}")
        all_records = []
        notes["error"] = str(exc)

    summary = build_summary(
        provider="thermofisher",
        product_identifier=notes.get("mode", "thermofisher"),
        product_url=product_url,
        downloads=all_records,
        notes=notes if notes else None,
    )
    print_summary(summary)


if __name__ == "__main__":
    main()
