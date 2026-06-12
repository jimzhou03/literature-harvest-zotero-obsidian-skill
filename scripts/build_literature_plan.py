#!/usr/bin/env python3
"""Build a deterministic literature-harvest query plan.

This script does not fetch papers. It normalizes the user's topic and emits a
small JSON plan that Codex can use before calling official APIs or Zotero.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Iterable


SYNONYMS = {
    "rag": ["retrieval augmented generation", "retrieval-augmented generation", "RAG"],
    "检索增强": ["retrieval augmented generation", "retrieval-augmented generation", "RAG"],
    "kg": ["knowledge graph", "knowledge graphs", "KG"],
    "知识图谱": ["knowledge graph", "knowledge graphs", "KG"],
    "神经网络": ["neural network", "neural networks", "deep learning"],
    "大语言模型": ["large language model", "large language models", "LLM", "LLMs"],
    "llm": ["large language model", "large language models", "LLM", "LLMs"],
    "信息抽取": ["information extraction", "relation extraction", "entity extraction"],
    "问答": ["question answering", "QA"],
    "摘要": ["summarization", "summary generation"],
    "图神经网络": ["graph neural network", "graph neural networks", "GNN"],
}

VENUE_ALIASES = {
    "einlp": "EMNLP",
    "emnlp": "EMNLP",
    "acl": "ACL",
    "ccl": "CCL",
    "naacl": "NAACL",
    "coling": "COLING",
    "iclr": "ICLR",
    "neurips": "NeurIPS",
    "nips": "NeurIPS",
    "icml": "ICML",
    "aaai": "AAAI",
    "ijcai": "IJCAI",
    "sigir": "SIGIR",
    "www": "TheWebConf",
    "thewebconf": "TheWebConf",
    "kdd": "KDD",
}


def split_csv(value: str) -> list[str]:
    parts = re.split(r"[,;，；\n]+", value or "")
    return [part.strip() for part in parts if part.strip()]


def slugify(text: str) -> str:
    lowered = text.strip().lower()
    lowered = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", lowered)
    lowered = re.sub(r"-+", "-", lowered).strip("-")
    return lowered[:80] or "literature"


def normalize_keywords(raw_keywords: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for raw in raw_keywords:
        key = raw.strip()
        if not key:
            continue
        candidates = SYNONYMS.get(key.lower()) or SYNONYMS.get(key) or [key]
        for candidate in candidates:
            canon = candidate.strip()
            marker = canon.lower()
            if marker not in seen:
                seen.add(marker)
                normalized.append(canon)
    return normalized


def normalize_venues(raw_venues: Iterable[str]) -> tuple[list[str], list[str]]:
    venues: list[str] = []
    warnings: list[str] = []
    seen: set[str] = set()
    for raw in raw_venues:
        key = raw.strip()
        if not key:
            continue
        venue = VENUE_ALIASES.get(key.lower(), key.upper())
        if key.lower() == "einlp":
            warnings.append("EINLP was normalized to EMNLP.")
        if venue not in seen:
            seen.add(venue)
            venues.append(venue)
    return venues, warnings


def parse_years(value: str) -> dict[str, int]:
    current = dt.date.today().year
    if not value:
        return {"start": current - 3, "end": current}
    match = re.match(r"^\s*(\d{4})\s*[:\-]\s*(\d{4})\s*$", value)
    if match:
        start, end = int(match.group(1)), int(match.group(2))
        return {"start": min(start, end), "end": max(start, end)}
    year = int(value)
    return {"start": year, "end": year}


def arxiv_query(terms: list[str]) -> str:
    quoted = [f'all:"{term}"' if " " in term else f"all:{term}" for term in terms]
    return " OR ".join(quoted)


def source_plan(venues: list[str], terms: list[str]) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = [
        {
            "name": "arXiv",
            "route": "official API",
            "query": arxiv_query(terms),
            "note": "Use arXiv API metadata and open PDFs; respect conservative pagination and delays.",
        },
        {
            "name": "Semantic Scholar/OpenAlex/Crossref",
            "route": "metadata APIs",
            "query": " OR ".join(terms),
            "note": "Use for discovery, venue validation, DOI lookup, and deduplication.",
        },
    ]
    venue_set = set(venues)
    if venue_set & {"ACL", "EMNLP", "NAACL", "COLING"}:
        sources.append(
            {
                "name": "ACL Anthology",
                "route": "official paper pages",
                "query": " OR ".join(terms),
                "note": "Use for ACL-family metadata and official open PDFs.",
            }
        )
    if "CCL" in venue_set:
        sources.append(
            {
                "name": "CCL official proceedings plus DBLP/Semantic Scholar",
                "route": "metadata-first",
                "query": " OR ".join(terms),
                "note": "Do not assume open PDFs; mark metadata-only when full text is unavailable.",
            }
        )
    if venue_set & {"ICLR", "NeurIPS"}:
        sources.append(
            {
                "name": "OpenReview",
                "route": "official forum pages",
                "query": " OR ".join(terms),
                "note": "Use for ICLR and OpenReview-hosted venues/workshops.",
            }
        )
    if venue_set & {"ICML"}:
        sources.append(
            {
                "name": "PMLR",
                "route": "official proceedings",
                "query": " OR ".join(terms),
                "note": "Use for ICML proceedings and official PDFs.",
            }
        )
    return sources


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    raw_keywords = split_csv(args.keywords)
    raw_venues = split_csv(args.venues)
    terms = normalize_keywords(raw_keywords)
    venues, warnings = normalize_venues(raw_venues)
    years = parse_years(args.years)
    topic_slug = slugify("-".join(raw_keywords[:4]))
    today = dt.date.today().isoformat()
    return {
        "created": today,
        "topic": args.topic or ", ".join(raw_keywords),
        "topic_slug": topic_slug,
        "raw_keywords": raw_keywords,
        "normalized_terms": terms,
        "venues": venues,
        "years": years,
        "limits": {
            "max_papers": args.max_papers,
            "deep_read": args.deep_read,
        },
        "reading": {
            "default_depth": args.reading_depth,
            "automation_mode": "full_auto",
            "review_gate": "none",
            "policy": "triage all candidates, extract PDF evidence for accessible papers, structured-read/deep-read the selected set",
            "pdf_evidence_command": f"python <skill-dir>/scripts/extract_pdf_evidence.py --manifest tmp/literature-harvest/{today}-{topic_slug}/manifest.json --write-text --update",
            "required_outputs": [
                "problem solved",
                "method mechanism",
                "evaluation support",
                "key artifacts",
                "tools/data/code",
                "method taxonomy",
                "trend timeline",
                "research gaps",
            ],
        },
        "warnings": warnings,
        "sources": source_plan(venues, terms),
        "zotero": {
            "collection": f"Literature Harvest/{today}/{topic_slug}",
            "web_api_import_command": f'python <skill-dir>/scripts/zotero_web_import.py --manifest tmp/literature-harvest/{today}-{topic_slug}/manifest.json --collection "Literature Harvest/{today}/{topic_slug}" --note-root wiki/sources/论文阅读/{topic_slug} --map "wiki/maps/{topic_slug} Literature Map.md" --pdf-mode imported-url --update',
            "preflight_command": f'python <skill-dir>/scripts/zotero_preflight.py --expected-name "{topic_slug}" --json',
            "import_status": "not_started",
            "dedupe_keys": ["doi", "arxiv_id", "acl_id", "openreview_forum_id", "normalized_title"],
        },
        "obsidian": {
            "note_root": f"wiki/sources/论文阅读/{topic_slug}",
            "map_page": f"wiki/maps/{topic_slug} Literature Map.md",
            "log": "wiki/log.md",
            "manifest": f"tmp/literature-harvest/{today}-{topic_slug}/manifest.json",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a literature-harvest query plan.")
    parser.add_argument("--keywords", required=True, help="Comma-separated topic keywords.")
    parser.add_argument("--venues", default="ACL,EMNLP,CCL,arXiv", help="Comma-separated venues/sources.")
    parser.add_argument("--years", default="", help="Year or range such as 2023:2026.")
    parser.add_argument("--max-papers", type=int, default=20)
    parser.add_argument("--deep-read", type=int, default=5)
    parser.add_argument(
        "--reading-depth",
        choices=["triage", "structured-read", "deep-read"],
        default="structured-read",
        help="Default depth for selected accessible PDFs.",
    )
    parser.add_argument("--topic", default="")
    parser.add_argument("--out", default="", help="Optional JSON output path.")
    parser.add_argument("--unicode", action="store_true", help="Emit unescaped Unicode in JSON output.")
    args = parser.parse_args()

    plan = build_plan(args)
    text = json.dumps(plan, ensure_ascii=not args.unicode, indent=2)
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
