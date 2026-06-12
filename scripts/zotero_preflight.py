#!/usr/bin/env python3
"""Check Zotero Desktop readiness and selected import target.

This helper is read-only from the user's perspective: it probes Zotero's local
Connector server and reports whether the currently selected collection matches
the literature-harvest run before Codex imports BibTeX/RIS records.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from typing import Any


DEFAULT_BASE_URL = os.environ.get("ZOTERO_LOCAL_BASE_URL", "http://localhost:23119")
CONNECTOR_HEADERS = {"X-Zotero-Connector-API-Version": "3"}


def connector_post(path: str, payload: Any, timeout: float = 5.0) -> tuple[int | None, Any, str | None]:
    body = json.dumps(payload).encode("utf-8")
    headers = {
        **CONNECTOR_HEADERS,
        "Content-Type": "application/json",
    }
    request = urllib.request.Request(
        DEFAULT_BASE_URL.rstrip("/") + path,
        data=body,
        method="POST",
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            text = response.read().decode("utf-8", errors="replace")
            content_type = response.headers.get("Content-Type", "")
            if "json" in content_type.lower():
                return response.status, json.loads(text or "null"), None
            return response.status, text, None
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        return exc.code, text, str(exc)
    except Exception as exc:  # Zotero closed, connector disabled, bad host, etc.
        return None, None, str(exc)


def normalize(value: str) -> str:
    return " ".join(value.lower().split())


def target_matches(selected: dict[str, Any], expected_name: str, exact: bool) -> bool:
    if not expected_name:
        return True
    selected_name = normalize(str(selected.get("name") or selected.get("libraryName") or ""))
    expected = normalize(expected_name)
    if exact:
        return selected_name == expected
    return expected in selected_name


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight Zotero selected collection before import.")
    parser.add_argument("--expected-name", default="", help="Expected Zotero collection name or substring.")
    parser.add_argument("--exact", action="store_true", help="Require exact collection name match.")
    parser.add_argument(
        "--allow-library",
        action="store_true",
        help="Allow importing into the top-level library when no collection is selected.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    status, payload, error = connector_post("/connector/getSelectedCollection", {})
    result: dict[str, Any] = {
        "ok": False,
        "base_url": DEFAULT_BASE_URL,
        "status": status,
        "expected_name": args.expected_name,
        "exact": args.exact,
        "selected": payload if isinstance(payload, dict) else None,
        "error": error,
        "reason": "",
    }
    if status != 200 or not isinstance(payload, dict):
        result["reason"] = "zotero_connector_unavailable"
    else:
        selected_id = str(payload.get("id") or "")
        selected_name = str(payload.get("name") or payload.get("libraryName") or "")
        is_library = selected_id == "" or selected_id.upper().startswith("L")
        if is_library and not args.allow_library and args.expected_name:
            result["reason"] = "selected_target_is_library"
        elif not target_matches(payload, args.expected_name, args.exact):
            result["reason"] = "selected_target_mismatch"
        else:
            result["ok"] = True
            result["reason"] = "ok"
        result["selected_name"] = selected_name
        result["selected_id"] = selected_id

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        selected = result.get("selected_name") or "Unknown"
        verdict = "OK" if result["ok"] else "BLOCKED"
        print(f"{verdict}: selected Zotero target = {selected}; reason = {result['reason']}")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
