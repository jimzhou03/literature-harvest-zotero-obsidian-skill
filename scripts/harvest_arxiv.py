#!/usr/bin/env python3
"""Fetch arXiv candidates, optionally download PDFs, and emit BibTeX.

This is a conservative MVP helper for the literature-harvest skill. It uses
only the official arXiv API and stdlib modules.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from build_literature_plan import normalize_keywords, parse_years, slugify, split_csv


ATOM = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
USER_AGENT = "Codex literature-harvest-zotero-obsidian/0.1 (mailto:research@example.local)"


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def bib_escape(value: str) -> str:
    return clean_text(value).replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def safe_key(title: str, year: int, arxiv_id: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", title.lower())
    stem = "_".join(words[:4]) or "arxiv"
    suffix = re.sub(r"[^0-9A-Za-z]+", "", arxiv_id.split("v", 1)[0])[-6:]
    return f"{stem}_{year}_{suffix}"


def arxiv_query(terms: list[str]) -> str:
    pieces: list[str] = []
    for term in terms:
        if " " in term:
            pieces.append(f'ti:"{term}" OR abs:"{term}"')
        else:
            pieces.append(f"ti:{term} OR abs:{term}")
    return " OR ".join(f"({piece})" for piece in pieces)


def request_text(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8")


def download_file(url: str, destination: Path, timeout: int = 60) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = response.read()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return len(data)


def text_of(entry: ET.Element, path: str) -> str:
    node = entry.find(path, ATOM)
    return clean_text(node.text if node is not None else "")


def parse_entry(entry: ET.Element) -> dict[str, Any]:
    entry_id = text_of(entry, "a:id")
    arxiv_id = entry_id.rstrip("/").split("/")[-1]
    title = text_of(entry, "a:title")
    abstract = text_of(entry, "a:summary")
    published_raw = text_of(entry, "a:published")
    published_year = int(published_raw[:4]) if published_raw[:4].isdigit() else 0
    authors = [clean_text(node.findtext("a:name", default="", namespaces=ATOM)) for node in entry.findall("a:author", ATOM)]
    categories = [node.attrib.get("term", "") for node in entry.findall("a:category", ATOM) if node.attrib.get("term")]
    pdf_url = ""
    landing_url = entry_id
    for link in entry.findall("a:link", ATOM):
        if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
            pdf_url = link.attrib.get("href", "")
        elif link.attrib.get("rel") == "alternate":
            landing_url = link.attrib.get("href", landing_url)
    if not pdf_url and arxiv_id:
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    return {
        "source": "arXiv",
        "arxiv_id": arxiv_id,
        "title": title,
        "authors": authors,
        "year": published_year,
        "published": published_raw,
        "categories": categories,
        "abstract": abstract,
        "source_url": landing_url,
        "pdf_url": pdf_url,
    }


def relevance_score(item: dict[str, Any], terms: list[str]) -> int:
    haystack_title = item["title"].lower()
    haystack_abs = item["abstract"].lower()
    score = 0
    for term in terms:
        needle = term.lower()
        if needle in haystack_title:
            score += 4
        if needle in haystack_abs:
            score += 2
    if item.get("pdf_url"):
        score += 1
    return score


def bib_entry(item: dict[str, Any]) -> str:
    year = item.get("year") or dt.date.today().year
    key = item.get("bibtex_key") or safe_key(item["title"], year, item["arxiv_id"])
    authors = " and ".join(item.get("authors") or ["Unknown"])
    fields = {
        "title": item["title"],
        "author": authors,
        "year": str(year),
        "eprint": item["arxiv_id"].split("v", 1)[0],
        "archivePrefix": "arXiv",
        "primaryClass": (item.get("categories") or [""])[0],
        "url": item["source_url"],
    }
    if item.get("pdf_path"):
        fields["file"] = item["pdf_path"]
    lines = [f"@misc{{{key},"]
    for name, value in fields.items():
        if value:
            lines.append(f"  {name} = {{{bib_escape(str(value))}}},")
    lines.append("}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch arXiv candidates and optionally download PDFs.")
    parser.add_argument("--keywords", required=True, help="Comma-separated topic keywords.")
    parser.add_argument("--years", default="", help="Year or range such as 2023:2026.")
    parser.add_argument("--max-results", type=int, default=20)
    parser.add_argument("--download", action="store_true", help="Download PDFs for retained candidates.")
    parser.add_argument("--out", required=True, help="Output directory for manifest, BibTeX, and PDFs.")
    parser.add_argument("--delay", type=float, default=3.0, help="Delay before each PDF download.")
    parser.add_argument("--unicode", action="store_true", help="Emit unescaped Unicode in JSON output.")
    args = parser.parse_args()

    raw_keywords = split_csv(args.keywords)
    terms = normalize_keywords(raw_keywords)
    years = parse_years(args.years)
    query = arxiv_query(terms)
    params = urllib.parse.urlencode(
        {
            "search_query": query,
            "start": 0,
            "max_results": max(1, args.max_results * 3),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
    )
    url = f"https://export.arxiv.org/api/query?{params}"
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    feed = request_text(url)
    root = ET.fromstring(feed)
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in root.findall("a:entry", ATOM):
        item = parse_entry(entry)
        year = item.get("year") or 0
        if year and not (years["start"] <= year <= years["end"]):
            continue
        score = relevance_score(item, terms)
        if score <= 0:
            continue
        stable_id = item["arxiv_id"].split("v", 1)[0]
        if stable_id in seen:
            continue
        seen.add(stable_id)
        item["relevance_score"] = score
        item["bibtex_key"] = safe_key(item["title"], item.get("year") or years["end"], item["arxiv_id"])
        candidates.append(item)

    candidates.sort(key=lambda item: (item["relevance_score"], item.get("year") or 0), reverse=True)
    candidates = candidates[: args.max_results]

    if args.download:
        pdf_dir = out_dir / "pdfs"
        for index, item in enumerate(candidates):
            if index > 0:
                time.sleep(max(0.0, args.delay))
            pdf_name = f"{slugify(item['arxiv_id'])}.pdf"
            pdf_path = pdf_dir / pdf_name
            try:
                bytes_written = download_file(item["pdf_url"], pdf_path)
                item["pdf_path"] = str(pdf_path)
                item["pdf_bytes"] = bytes_written
                item["pdf_download_status"] = "ok"
            except Exception as exc:  # noqa: BLE001 - preserve concrete failure in manifest.
                item["pdf_path"] = ""
                item["pdf_bytes"] = 0
                item["pdf_download_status"] = f"failed: {exc}"

    manifest = {
        "created": dt.date.today().isoformat(),
        "query_url": url,
        "raw_keywords": raw_keywords,
        "normalized_terms": terms,
        "years": years,
        "count": len(candidates),
        "items": candidates,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=not args.unicode, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "references.bib").write_text("\n\n".join(bib_entry(item) for item in candidates) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out_dir), "count": len(candidates)}, ensure_ascii=not args.unicode))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
