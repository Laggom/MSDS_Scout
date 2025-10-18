#!/usr/bin/env python3
"""Shared helpers for SDS download scripts."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional


@dataclass
class DownloadRecord:
    """Represents a single SDS download outcome."""

    path: Path
    languages: List[str] = field(default_factory=list)
    source_url: str = ""
    metadata: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "path": str(self.path),
            "languages": sorted(set(self.languages)),
            "sourceUrl": self.source_url,
            "metadata": self.metadata,
        }


def normalize_languages(languages: Optional[Iterable[str]]) -> List[str]:
    if not languages:
        return []
    return sorted({lang.strip().lower() for lang in languages if lang.strip()})


def build_summary(
    provider: str,
    product_identifier: str,
    *,
    product_url: Optional[str] = None,
    html_path: Optional[Path] = None,
    downloads: Iterable[DownloadRecord] = (),
    notes: Optional[Dict[str, str]] = None,
) -> Dict[str, object]:
    summary: Dict[str, object] = {
        "provider": provider,
        "product": product_identifier,
        "downloads": [record.to_dict() for record in downloads],
    }
    if product_url:
        summary["productUrl"] = product_url
    if html_path:
        summary["htmlPath"] = str(html_path)
    if notes:
        summary["notes"] = notes
    return summary


def print_summary(summary: Dict[str, object]) -> None:
    """Emit a unified JSON summary to stdout."""
    print("\n=== SDS Download Summary ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
