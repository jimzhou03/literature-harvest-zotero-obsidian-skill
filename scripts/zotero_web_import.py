#!/usr/bin/env python3
"""Import a literature-harvest manifest into Zotero via the Zotero Web API.

This mode avoids manual Zotero Desktop collection selection. It creates or
reuses a collection path, creates/reuses items, adds them to the collection,
adds PDF attachments, and can update the manifest plus Obsidian notes.

Credentials are read only from environment variables:

- ZOTERO_API_KEY: required, with write access to the target library.
- ZOTERO_LIBRARY_ID: optional user/group numeric ID. If omitted for users, the
  script tries to derive userID from the API key metadata.
- ZOTERO_LIBRARY_TYPE: optional, "user" (default) or "group".
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


API_BASE = "https://api.zotero.org"
API_VERSION = "3"
ROOT = Path.cwd()


class ZoteroWebError(RuntimeError):
    pass


def normalize_title(value: str) -> str:
    return re.sub(r"\W+", " ", value or "").strip().lower()


def split_authors(value: str | list[str]) -> list[dict[str, str]]:
    if isinstance(value, list):
        names = value
    else:
        names = [part.strip() for part in re.split(r"\s+and\s+", value or "") if part.strip()]
    creators = []
    for name in names:
        pieces = name.split()
        if len(pieces) >= 2:
            creators.append({"creatorType": "author", "firstName": " ".join(pieces[:-1]), "lastName": pieces[-1]})
        elif name:
            creators.append({"creatorType": "author", "name": name})
    return creators or [{"creatorType": "author", "name": "Unknown"}]


def rel_to_root(path: str | Path) -> Path:
    path_obj = Path(path)
    return path_obj if path_obj.is_absolute() else ROOT / path_obj


def api_headers(api_key: str, extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {
        "Zotero-API-Key": api_key,
        "Zotero-API-Version": API_VERSION,
        "User-Agent": "literature-harvest-zotero-obsidian/0.2",
    }
    if extra:
        headers.update(extra)
    return headers


def request_json(
    method: str,
    url: str,
    api_key: str | None = None,
    payload: Any | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], Any]:
    body = None
    merged_headers = dict(headers or {})
    if api_key:
        merged_headers = api_headers(api_key, merged_headers)
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        merged_headers.setdefault("Content-Type", "application/json")
    for attempt in range(3):
        req = urllib.request.Request(url, data=body, method=method, headers=merged_headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                text = response.read().decode("utf-8", errors="replace")
                parsed = json.loads(text) if text else None
                return response.status, dict(response.headers.items()), parsed
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            if exc.code in {429, 500, 502, 503, 504} and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            raise ZoteroWebError(f"{method} {url} failed: status={exc.code} body={text[:600]}") from exc
        except (TimeoutError, urllib.error.URLError) as exc:
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            raise ZoteroWebError(f"{method} {url} failed after retries: {exc}") from exc
    raise ZoteroWebError(f"{method} {url} failed after retries.")


def request_bytes(
    method: str,
    url: str,
    api_key: str,
    body: bytes,
    headers: dict[str, str],
) -> tuple[int, dict[str, str], str]:
    for attempt in range(3):
        req = urllib.request.Request(url, data=body, method=method, headers=api_headers(api_key, headers))
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                text = response.read().decode("utf-8", errors="replace")
                return response.status, dict(response.headers.items()), text
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            if exc.code in {429, 500, 502, 503, 504} and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            raise ZoteroWebError(f"{method} {url} failed: status={exc.code} body={text[:600]}") from exc
        except (TimeoutError, urllib.error.URLError) as exc:
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            raise ZoteroWebError(f"{method} {url} failed after retries: {exc}") from exc
    raise ZoteroWebError(f"{method} {url} failed after retries.")


def derive_user_id(api_key: str) -> str:
    status, _, payload = request_json("GET", f"{API_BASE}/keys/{urllib.parse.quote(api_key)}")
    if status != 200 or not isinstance(payload, dict):
        raise ZoteroWebError("Could not inspect Zotero API key metadata.")
    user_id = payload.get("userID")
    if not user_id:
        raise ZoteroWebError("ZOTERO_LIBRARY_ID is required because userID was not present in key metadata.")
    return str(user_id)


def library_prefix(api_key: str, library_id: str | None, library_type: str) -> str:
    kind = library_type.lower()
    if kind == "group":
        if not library_id:
            raise ZoteroWebError("ZOTERO_LIBRARY_ID is required for group libraries.")
        return f"/groups/{library_id}"
    if library_id:
        return f"/users/{library_id}"
    return f"/users/{derive_user_id(api_key)}"


def paged_get(api_key: str, prefix: str, path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start = 0
    limit = 100
    while True:
        url = f"{API_BASE}{prefix}{path}?format=json&limit={limit}&start={start}"
        _, _, payload = request_json("GET", url, api_key)
        if not isinstance(payload, list) or not payload:
            break
        rows.extend(payload)
        if len(payload) < limit:
            break
        start += limit
    return rows


def object_key_from_response(response: dict[str, Any], index: str = "0") -> str:
    for field in ("successful", "success"):
        block = response.get(field, {})
        if index in block:
            value = block[index]
            if isinstance(value, dict):
                return value.get("key") or value.get("data", {}).get("key")
            return str(value)
    failed = response.get("failed") or {}
    raise ZoteroWebError(f"Zotero write did not return a key. failed={failed}")


def ensure_collection(api_key: str, prefix: str, collection_path: str) -> str:
    parts = [part.strip() for part in re.split(r"[/\\]+", collection_path) if part.strip()]
    if not parts:
        raise ZoteroWebError("Collection path is empty.")
    collections = paged_get(api_key, prefix, "/collections")
    by_parent_name: dict[tuple[str | bool, str], str] = {}
    for row in collections:
        data = row.get("data", row)
        by_parent_name[(data.get("parentCollection") or False, data.get("name", ""))] = data.get("key") or row.get("key")
    parent: str | bool = False
    key = ""
    for name in parts:
        existing = by_parent_name.get((parent, name))
        if existing:
            key = existing
            parent = key
            continue
        payload = [{"name": name, "parentCollection": parent}]
        _, _, response = request_json("POST", f"{API_BASE}{prefix}/collections", api_key, payload)
        key = object_key_from_response(response)
        by_parent_name[(parent, name)] = key
        parent = key
    return key


def search_existing_item(api_key: str, prefix: str, title: str, arxiv_id: str | None) -> dict[str, Any] | None:
    query = urllib.parse.quote(title[:120])
    _, _, payload = request_json("GET", f"{API_BASE}{prefix}/items?q={query}&format=json&limit=10", api_key)
    needle = normalize_title(title)
    for row in payload or []:
        data = row.get("data", row)
        if normalize_title(data.get("title", "")) == needle:
            return data
        extra = data.get("extra", "")
        if arxiv_id and arxiv_id in extra:
            return data
    return None


def item_payload(paper: dict[str, Any], collection_key: str, item_type: str) -> dict[str, Any]:
    arxiv_id = paper.get("arxiv_id", "")
    extra_lines = [
        f"arXiv: {arxiv_id}" if arxiv_id else "",
        f"BibTeX key: {paper.get('bibtex_key', '')}" if paper.get("bibtex_key") else "",
        f"PDF: {paper.get('pdf_url', '')}" if paper.get("pdf_url") else "",
    ]
    return {
        "itemType": item_type,
        "title": paper["title"],
        "creators": split_authors(paper.get("authors", "")),
        "abstractNote": paper.get("abstract") or paper.get("summary", ""),
        "date": str(paper.get("year", "")),
        "url": paper.get("source_url", ""),
        "language": "en",
        "extra": "\n".join(line for line in extra_lines if line),
        "tags": [{"tag": paper.get("topic", "literature-harvest")}, {"tag": "literature-harvest"}],
        "collections": [collection_key],
        "relations": {},
    }


def add_to_collection(api_key: str, prefix: str, item: dict[str, Any], collection_key: str) -> None:
    collections = list(dict.fromkeys((item.get("collections") or []) + [collection_key]))
    version = item.get("version")
    headers = {"If-Unmodified-Since-Version": str(version)} if version is not None else {}
    request_json("PATCH", f"{API_BASE}{prefix}/items/{item['key']}", api_key, {"collections": collections}, headers=headers)


def create_item(api_key: str, prefix: str, paper: dict[str, Any], collection_key: str, item_type: str) -> str:
    existing = search_existing_item(api_key, prefix, paper["title"], paper.get("arxiv_id"))
    if existing:
        add_to_collection(api_key, prefix, existing, collection_key)
        return existing["key"]
    _, _, response = request_json("POST", f"{API_BASE}{prefix}/items", api_key, [item_payload(paper, collection_key, item_type)])
    return object_key_from_response(response)


def create_pdf_url_attachment(api_key: str, prefix: str, parent_key: str, paper: dict[str, Any]) -> str | None:
    pdf_url = paper.get("pdf_url")
    if not pdf_url:
        return None
    for child in paged_get(api_key, prefix, f"/items/{parent_key}/children"):
        data = child.get("data", child)
        if data.get("itemType") == "attachment" and data.get("url") == pdf_url:
            return data.get("key") or child.get("key")
    filename = f"{paper.get('arxiv_id', parent_key)}.pdf"
    payload = [
        {
            "itemType": "attachment",
            "parentItem": parent_key,
            "linkMode": "imported_url",
            "title": "PDF",
            "accessDate": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "url": pdf_url,
            "note": "",
            "tags": [],
            "relations": {},
            "contentType": "application/pdf",
            "charset": "",
            "filename": filename,
            "md5": None,
            "mtime": None,
        }
    ]
    _, _, response = request_json("POST", f"{API_BASE}{prefix}/items", api_key, payload)
    return object_key_from_response(response)


def create_file_attachment_item(api_key: str, prefix: str, parent_key: str, pdf_path: Path) -> str:
    filename = pdf_path.name
    for child in paged_get(api_key, prefix, f"/items/{parent_key}/children"):
        data = child.get("data", child)
        if data.get("itemType") == "attachment" and data.get("filename") == filename:
            return data.get("key") or child.get("key")
    payload = [
        {
            "itemType": "attachment",
            "parentItem": parent_key,
            "linkMode": "imported_file",
            "title": filename,
            "note": "",
            "tags": [],
            "relations": {},
            "contentType": mimetypes.guess_type(filename)[0] or "application/pdf",
            "charset": "",
            "filename": filename,
        }
    ]
    _, _, response = request_json("POST", f"{API_BASE}{prefix}/items", api_key, payload)
    return object_key_from_response(response)


def upload_file_attachment(api_key: str, prefix: str, attachment_key: str, pdf_path: Path) -> str:
    data = pdf_path.read_bytes()
    md5 = hashlib.md5(data).hexdigest()
    mtime = int(pdf_path.stat().st_mtime * 1000)
    body = urllib.parse.urlencode(
        {"md5": md5, "filename": pdf_path.name, "filesize": len(data), "mtime": mtime}
    ).encode("utf-8")
    headers = {"Content-Type": "application/x-www-form-urlencoded", "If-None-Match": "*"}
    _, _, auth_text = request_bytes(
        "POST",
        f"{API_BASE}{prefix}/items/{attachment_key}/file",
        api_key,
        body,
        headers,
    )
    auth = json.loads(auth_text) if auth_text else {}
    if auth.get("exists"):
        return "exists"
    upload_body = auth["prefix"].encode("utf-8") + data + auth["suffix"].encode("utf-8")
    request = urllib.request.Request(
        auth["url"],
        data=upload_body,
        method="POST",
        headers={"Content-Type": auth["contentType"]},
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        if response.status not in (200, 201, 204):
            raise ZoteroWebError(f"PDF upload failed with status {response.status}")
    register = urllib.parse.urlencode({"upload": auth["uploadKey"]}).encode("utf-8")
    request_bytes(
        "POST",
        f"{API_BASE}{prefix}/items/{attachment_key}/file",
        api_key,
        register,
        {"Content-Type": "application/x-www-form-urlencoded", "If-None-Match": "*"},
    )
    return "uploaded"


def note_path_for(paper: dict[str, Any], note_root: Path) -> Path | None:
    if paper.get("note_path"):
        return rel_to_root(paper["note_path"])
    title_slug = re.sub(r"[^a-zA-Z0-9]+", "-", paper.get("title", "").lower()).strip("-")[:90]
    candidate = note_root / f"{paper.get('year')}-{title_slug}.md"
    return candidate if candidate.exists() else None


def update_note(path: Path, item_key: str, collection_key: str) -> None:
    if not path or not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    text = re.sub(r'zotero_item_key:\s*"TBD"', f'zotero_item_key: "{item_key}"', text)
    text = text.replace("Zotero item key: `TBD`", f"Zotero item key: `{item_key}`")
    text = text.replace("Zotero 状态：`pending_target_confirmation`，当前未导入，等待正确 collection。", f"Zotero 状态：`imported_via_web_api`，item `{item_key}`，collection `{collection_key}`。")
    path.write_text(text, encoding="utf-8")


def upsert_line_after(text: str, anchor: str, lines_to_insert: list[str]) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line == anchor:
            return "\n".join(lines[: index + 1] + lines_to_insert + lines[index + 1 :]) + "\n"
    return text


def update_map(path: Path, manifest: dict[str, Any]) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    collection = manifest.get("zotero_collection", "")
    collection_key = manifest.get("zotero_collection_key", "")
    attached = manifest.get("zotero_pdf_attached_count", 0)
    mode = manifest.get("zotero_pdf_attachment_mode", "unknown")

    text = re.sub(r"Zotero import status: `[^`]+`", "Zotero import status: `imported_via_web_api`", text)
    stale_patterns = (
        "当前 Zotero 选中 collection",
        "本批次未导入",
        "Zotero item key 当前为",
        "Zotero item keys 已回填",
        "Zotero collection:",
        "PDF attachment mode:",
    )
    lines = [line for line in text.splitlines() if not any(pattern in line for pattern in stale_patterns)]
    text = "\n".join(lines) + "\n"

    status_line = "- Zotero import status: `imported_via_web_api`。"
    if status_line in text:
        text = upsert_line_after(
            text,
            status_line,
            [
                f"- Zotero collection: `{collection}` (`{collection_key}`)。",
                f"- PDF attachment mode: `{mode}`，attached={attached}。",
                "- Zotero item keys 已回填到各论文笔记。",
            ],
        )
    path.write_text(text, encoding="utf-8")


def update_log(path: Path, manifest: dict[str, Any]) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    created = manifest.get("created") or time.strftime("%Y-%m-%d", time.gmtime())
    items = manifest.get("items", [])
    imported = manifest.get("zotero_imported_count", 0)
    attached = manifest.get("zotero_pdf_attached_count", 0)
    analysis = manifest.get("analysis_summary", {})
    deep_read = analysis.get("pdf_assisted_deep_read", 0)
    full_text_extracted = manifest.get("pdf_evidence_summary", {}).get("ok", 0)
    structured_read = sum(
        1 for item in items if item.get("analysis_status") in {"structured-read", "deep-read"}
    )
    collection = manifest.get("zotero_collection", "")
    collection_key = manifest.get("zotero_collection_key", "")
    mode = manifest.get("zotero_pdf_attachment_mode", "unknown")
    counts = (
        f"- Counts: found={len(items)}, unique={len(items)}, imported={imported}, "
        f"zotero_pending=0, pdf_attached={attached}, full_text_extracted={full_text_extracted}, "
        f"structured_read={structured_read}, deep_read={deep_read}, notes={len(items)}, "
        f"review_required={len(items)}"
    )
    notes = (
        f"- Notes: Zotero Web API 已导入 collection `{collection}` (`{collection_key}`)；"
        f"PDF 附件模式 `{mode}`；所有细节结论需要人工复核。"
    )
    heading_match = re.search(rf"^## {re.escape(created)} Literature Harvest: .*$", text, flags=re.MULTILINE)
    if not heading_match:
        return
    next_heading = re.search(r"^## \d{4}-\d{2}-\d{2} ", text[heading_match.end() :], flags=re.MULTILINE)
    end = heading_match.end() + next_heading.start() if next_heading else len(text)
    block = text[heading_match.start() : end]
    block = re.sub(r"^- Counts: .*$", counts, block, flags=re.MULTILINE)
    block = re.sub(r"^- Notes: .*$", notes, block, flags=re.MULTILINE)
    text = text[: heading_match.start()] + block + text[end:]
    path.write_text(text, encoding="utf-8")


def update_text_outputs(manifest_path: Path, manifest: dict[str, Any], args: argparse.Namespace) -> None:
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    note_root = rel_to_root(args.note_root) if args.note_root else None
    if note_root:
        for paper in manifest["items"]:
            key = paper.get("zotero_item_key")
            if key:
                path = note_path_for(paper, note_root)
                update_note(path, key, manifest.get("zotero_collection_key", ""))
    if args.map:
        map_path = rel_to_root(args.map)
        update_map(map_path, manifest)
    if args.log:
        update_log(rel_to_root(args.log), manifest)


def main() -> int:
    parser = argparse.ArgumentParser(description="Import a literature-harvest manifest into Zotero Web API.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--collection", required=True, help="Collection path, e.g. Literature Harvest/2026-06-12/topic")
    parser.add_argument("--note-root", default="")
    parser.add_argument("--map", default="")
    parser.add_argument("--item-type", default="preprint")
    parser.add_argument("--pdf-mode", choices=["none", "imported-url", "upload-file"], default="imported-url")
    parser.add_argument("--fallback-url-attachment", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--update", action="store_true", help="Update manifest and Obsidian notes after import.")
    parser.add_argument("--log", default="wiki/log.md", help="Obsidian log path to update when --update is set.")
    args = parser.parse_args()

    api_key = os.environ.get("ZOTERO_API_KEY")
    if not api_key:
        raise SystemExit("ZOTERO_API_KEY is required. Create a Zotero API key with write access and set it as an environment variable.")
    library_type = os.environ.get("ZOTERO_LIBRARY_TYPE", "user")
    library_id = os.environ.get("ZOTERO_LIBRARY_ID")
    prefix = library_prefix(api_key, library_id, library_type)
    manifest_path = rel_to_root(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if args.dry_run:
        print(json.dumps({"prefix": prefix, "collection": args.collection, "items": len(manifest["items"])}, ensure_ascii=False, indent=2))
        return 0

    collection_key = ensure_collection(api_key, prefix, args.collection)
    results = []
    for paper in manifest["items"]:
        item_key = create_item(api_key, prefix, paper, collection_key, args.item_type)
        paper["zotero_item_key"] = item_key
        paper["zotero_collection_key"] = collection_key
        attachment_key = None
        attachment_status = "none"
        if args.pdf_mode == "imported-url":
            attachment_key = create_pdf_url_attachment(api_key, prefix, item_key, paper)
            attachment_status = "imported-url" if attachment_key else "no-pdf-url"
        elif args.pdf_mode == "upload-file" and paper.get("pdf_path"):
            try:
                pdf_path = rel_to_root(paper["pdf_path"])
                attachment_key = create_file_attachment_item(api_key, prefix, item_key, pdf_path)
                attachment_status = upload_file_attachment(api_key, prefix, attachment_key, pdf_path)
            except Exception as exc:  # Preserve progress and optionally fall back.
                attachment_status = f"upload-failed: {exc}"
                if args.fallback_url_attachment:
                    attachment_key = create_pdf_url_attachment(api_key, prefix, item_key, paper)
                    attachment_status += "; fallback-imported-url"
        paper["zotero_attachment_key"] = attachment_key
        paper["zotero_attachment_status"] = attachment_status
        results.append({"title": paper["title"], "item_key": item_key, "attachment_key": attachment_key, "attachment_status": attachment_status})

    manifest["zotero_import_status"] = "imported_via_web_api"
    manifest["zotero_collection"] = args.collection
    manifest["zotero_collection_key"] = collection_key
    manifest["zotero_imported_count"] = len(results)
    manifest["zotero_pdf_attachment_mode"] = args.pdf_mode
    manifest["zotero_pdf_attached_count"] = sum(1 for result in results if result.get("attachment_key"))
    manifest["zotero_imported_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if args.update:
        update_text_outputs(manifest_path, manifest, args)
    print(json.dumps({"collection_key": collection_key, "imported": len(results), "results": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
