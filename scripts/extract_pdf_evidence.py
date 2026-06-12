#!/usr/bin/env python3
"""Extract full-text evidence packs from downloaded literature-harvest PDFs.

This helper does not write final interpretations. It makes later Codex reading
less shallow by extracting full text, section hints, method/evaluation snippets,
and figure/table/algorithm references from each accessible PDF.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path.cwd()

SECTION_HINTS = [
    "abstract",
    "introduction",
    "background",
    "related work",
    "preliminaries",
    "method",
    "methodology",
    "approach",
    "framework",
    "system",
    "model",
    "algorithm",
    "experiment",
    "experimental setup",
    "evaluation",
    "results",
    "analysis",
    "ablation",
    "discussion",
    "limitation",
    "limitations",
    "conclusion",
]

SNIPPET_CATEGORIES = {
    "problem_motivation": [
        "problem",
        "challenge",
        "motivation",
        "gap",
        "limitation",
        "fail",
        "difficult",
        "aim",
        "objective",
        "we study",
        "we address",
    ],
    "method": [
        "method",
        "approach",
        "framework",
        "algorithm",
        "architecture",
        "model",
        "training",
        "inference",
        "pipeline",
        "module",
        "we propose",
    ],
    "evaluation": [
        "experiment",
        "evaluation",
        "dataset",
        "benchmark",
        "metric",
        "baseline",
        "ablation",
        "result",
        "performance",
        "outperform",
    ],
    "limitations": [
        "limitation",
        "future work",
        "fail",
        "error",
        "cannot",
        "does not",
        "assumption",
        "threat",
    ],
}


def load_pdf_reader() -> Any:
    try:
        from pypdf import PdfReader  # type: ignore

        return PdfReader
    except Exception:
        try:
            from PyPDF2 import PdfReader  # type: ignore

            return PdfReader
        except Exception as exc:  # noqa: BLE001 - show install hint.
            raise SystemExit(
                "PDF text extraction requires pypdf. Install with: python -m pip install pypdf"
            ) from exc


def slugify(value: str) -> str:
    lowered = (value or "paper").lower()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    return re.sub(r"-+", "-", lowered).strip("-")[:90] or "paper"


def rel(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_pdf_path(raw_path: str, manifest_path: Path) -> Path | None:
    if not raw_path:
        return None
    candidate = Path(raw_path)
    candidates = [candidate]
    if not candidate.is_absolute():
        candidates = [manifest_path.parent / candidate, ROOT / candidate]
    for path in candidates:
        if path.exists():
            return path
    return None


def clean_text(value: str) -> str:
    value = value.encode("utf-8", "replace").decode("utf-8")
    value = value.replace("\x00", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def split_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[.!?。！？])\s+", normalized)
    return [part.strip() for part in parts if len(part.strip()) > 40]


def extract_pages(pdf_path: Path) -> list[str]:
    reader_cls = load_pdf_reader()
    reader = reader_cls(str(pdf_path))
    pages: list[str] = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception:  # noqa: BLE001 - preserve partial extraction.
            text = ""
        pages.append(clean_text(text))
    return pages


def section_headings(pages: list[str]) -> list[dict[str, Any]]:
    hints = "|".join(re.escape(hint) for hint in SECTION_HINTS)
    pattern = re.compile(rf"^(?:\d+(?:\.\d+)*\s+)?({hints})\b.*$", flags=re.IGNORECASE)
    seen: set[str] = set()
    headings: list[dict[str, Any]] = []
    for page_index, page in enumerate(pages, start=1):
        for line in page.splitlines():
            line = re.sub(r"\s+", " ", line.strip())
            if len(line) > 100:
                continue
            match = pattern.match(line)
            if not match:
                continue
            key = line.lower()
            if key in seen:
                continue
            seen.add(key)
            headings.append({"page": page_index, "heading": line})
            if len(headings) >= 40:
                return headings
    return headings


def snippets_by_category(pages: list[str], limit_per_category: int) -> dict[str, list[dict[str, Any]]]:
    output: dict[str, list[dict[str, Any]]] = {}
    for category, keywords in SNIPPET_CATEGORIES.items():
        found: list[dict[str, Any]] = []
        seen: set[str] = set()
        for page_index, page in enumerate(pages, start=1):
            for sentence in split_sentences(page):
                lower = sentence.lower()
                matched = [keyword for keyword in keywords if keyword in lower]
                if not matched:
                    continue
                snippet = sentence[:700]
                key = re.sub(r"\W+", "", snippet.lower())[:160]
                if key in seen:
                    continue
                seen.add(key)
                found.append({"page": page_index, "matched": matched[:4], "text": snippet})
                if len(found) >= limit_per_category:
                    break
            if len(found) >= limit_per_category:
                break
        output[category] = found
    return output


def artifact_refs(pages: list[str], limit: int) -> list[dict[str, Any]]:
    pattern = re.compile(r"\b(Figure|Fig\.|Table|Algorithm|Equation|Eq\.)\s*\d+", flags=re.IGNORECASE)
    refs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for page_index, page in enumerate(pages, start=1):
        for line in page.splitlines():
            line = re.sub(r"\s+", " ", line.strip())
            if len(line) < 20 or len(line) > 500 or not pattern.search(line):
                continue
            key = line.lower()
            if key in seen:
                continue
            seen.add(key)
            refs.append({"page": page_index, "text": line[:500]})
            if len(refs) >= limit:
                return refs
    return refs


def abstract_like_preview(pages: list[str]) -> str:
    first = "\n".join(pages[:2])
    match = re.search(r"abstract\s*(.+?)(?:\n\s*1\s+|\n\s*introduction\b)", first, flags=re.IGNORECASE | re.DOTALL)
    text = match.group(1) if match else first
    return re.sub(r"\s+", " ", text).strip()[:1200]


def evidence_for_paper(
    paper: dict[str, Any],
    manifest_path: Path,
    text_dir: Path | None,
    text_base: Path,
    limit_per_category: int,
    artifact_limit: int,
) -> dict[str, Any]:
    raw_path = paper.get("pdf_path") or paper.get("local_pdf_path") or ""
    pdf_path = resolve_pdf_path(raw_path, manifest_path)
    identity = paper.get("arxiv_id") or paper.get("doi") or paper.get("bibtex_key") or paper.get("title", "paper")
    record: dict[str, Any] = {
        "title": paper.get("title", ""),
        "year": paper.get("year"),
        "arxiv_id": paper.get("arxiv_id", ""),
        "bibtex_key": paper.get("bibtex_key", ""),
        "pdf_path": raw_path,
        "status": "not_started",
    }
    if not pdf_path:
        record["status"] = "missing_pdf"
        return record
    try:
        pages = extract_pages(pdf_path)
    except Exception as exc:  # noqa: BLE001 - preserve per-paper failure.
        record["status"] = f"extract_failed: {exc}"
        return record

    full_text = clean_text("\n\n".join(f"[Page {i}]\n{text}" for i, text in enumerate(pages, start=1)))
    record.update(
        {
            "status": "ok",
            "page_count": len(pages),
            "char_count": len(full_text),
            "abstract_preview": abstract_like_preview(pages),
            "section_headings": section_headings(pages),
            "snippets": snippets_by_category(pages, limit_per_category),
            "artifact_refs": artifact_refs(pages, artifact_limit),
        }
    )
    if text_dir:
        text_dir.mkdir(parents=True, exist_ok=True)
        text_path = text_dir / f"{slugify(str(identity))}.txt"
        text_path.write_text(full_text + "\n", encoding="utf-8")
        record["full_text_path"] = rel(text_path, text_base)
    return record


def update_log(path: Path, manifest: dict[str, Any], extracted_count: int) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    created = manifest.get("created") or dt.date.today().isoformat()
    items = manifest.get("items", [])
    imported = manifest.get("zotero_imported_count", 0)
    attached = manifest.get("zotero_pdf_attached_count") or sum(
        1 for item in items if item.get("zotero_attachment_key") or item.get("pdf_path")
    )
    analysis = manifest.get("analysis_summary", {})
    deep_read = analysis.get("pdf_assisted_deep_read", 0)
    structured_read = sum(
        1 for item in items if item.get("analysis_status") in {"structured-read", "deep-read"}
    )
    low_confidence = sum(
        1
        for item in items
        if item.get("analysis_confidence") == "low"
        or item.get("evidence_level") in {"abstract_only", "metadata_only", "failed_extraction"}
        or item.get("full_text_status") not in {None, "ok"}
    )
    counts = (
        f"- Counts: found={len(items)}, unique={len(items)}, imported={imported}, "
        f"zotero_pending=0, pdf_attached={attached}, full_text_extracted={extracted_count}, "
        f"structured_read={structured_read}, deep_read={deep_read}, notes={len(items)}, "
        f"low_confidence={low_confidence}"
    )
    heading_match = re.search(rf"^## {re.escape(created)} Literature Harvest: .*$", text, flags=re.MULTILINE)
    if not heading_match:
        return
    next_heading = re.search(r"^## \d{4}-\d{2}-\d{2} ", text[heading_match.end() :], flags=re.MULTILINE)
    end = heading_match.end() + next_heading.start() if next_heading else len(text)
    block = text[heading_match.start() : end]
    block = re.sub(r"^- Counts: .*$", counts, block, flags=re.MULTILINE)
    text = text[: heading_match.start()] + block + text[end:]
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract PDF evidence packs from a literature-harvest manifest.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", default="", help="Output JSON path. Defaults to <manifest-dir>/pdf-evidence.json.")
    parser.add_argument("--write-text", action="store_true", help="Write extracted full text files next to the evidence JSON.")
    parser.add_argument("--text-dir", default="", help="Directory for extracted full text when --write-text is set.")
    parser.add_argument("--limit-per-category", type=int, default=8)
    parser.add_argument("--artifact-limit", type=int, default=12)
    parser.add_argument("--update", action="store_true", help="Backfill extraction status and paths into manifest.json.")
    parser.add_argument("--log", default="wiki/log.md", help="Obsidian log path to update when --update is set.")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = ROOT / manifest_path
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    out_path = Path(args.out) if args.out else manifest_path.parent / "pdf-evidence.json"
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    text_dir = None
    if args.write_text:
        text_dir = Path(args.text_dir) if args.text_dir else out_path.parent / "full_text"
        if not text_dir.is_absolute():
            text_dir = ROOT / text_dir

    records = [
        evidence_for_paper(
            paper,
            manifest_path,
            text_dir,
            manifest_path.parent,
            args.limit_per_category,
            args.artifact_limit,
        )
        for paper in manifest.get("items", [])
    ]
    evidence = {
        "created": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "manifest": rel(manifest_path, ROOT),
        "items": records,
        "summary": {
            "items": len(records),
            "ok": sum(1 for item in records if item.get("status") == "ok"),
            "missing_or_failed": sum(1 for item in records if item.get("status") != "ok"),
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.update:
        by_key = {
            (record.get("arxiv_id") or record.get("bibtex_key") or record.get("title")): record for record in records
        }
        for paper in manifest.get("items", []):
            key = paper.get("arxiv_id") or paper.get("bibtex_key") or paper.get("title")
            record = by_key.get(key)
            if not record:
                continue
            status = record.get("status")
            paper["full_text_status"] = status
            paper["full_text_chars"] = record.get("char_count", 0)
            if record.get("full_text_path"):
                paper["full_text_path"] = record["full_text_path"]
            if status == "ok":
                paper.setdefault("evidence_level", "full_text")
                paper.setdefault("analysis_confidence", "medium")
            elif status == "missing_pdf":
                paper["evidence_level"] = "metadata_only"
                paper["analysis_confidence"] = "low"
            else:
                paper["evidence_level"] = "failed_extraction"
                paper["analysis_confidence"] = "low"
            paper["review_gate"] = "none"
        manifest["pdf_evidence_status"] = "extracted"
        manifest["pdf_evidence_path"] = rel(out_path, manifest_path.parent)
        manifest["pdf_evidence_summary"] = evidence["summary"]
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        log_path = Path(args.log)
        if not log_path.is_absolute():
            log_path = ROOT / log_path
        update_log(log_path, manifest, evidence["summary"]["ok"])

    print(json.dumps({"out": str(out_path), **evidence["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
