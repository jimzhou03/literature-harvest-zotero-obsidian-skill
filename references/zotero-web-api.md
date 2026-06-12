# Zotero Web API Full Automation

Use this path when the user wants end-to-end automation without Zotero Desktop collection selection.

## One-Time Setup

Create a Zotero API key with write access to the target library, then expose it to Codex as an environment variable:

Where to get the key:

1. Sign in to Zotero.
2. Open [https://www.zotero.org/settings/keys](https://www.zotero.org/settings/keys).
3. Click `Create new private key` or the equivalent button.
4. Recommended permissions:
   - Enable personal library access.
   - Enable write access.
   - If only the personal library is needed, do not grant group-library access.
5. Copy the generated key after creation.

Do not paste the key into chat or write it into repository files, manifests, notes, or logs.

Temporary current-window setup:

```powershell
$env:ZOTERO_API_KEY = "your-key"
```

Persistent Windows user setup:

```powershell
[Environment]::SetEnvironmentVariable("ZOTERO_API_KEY", "your-key", "User")
```

Optional variables:

```powershell
$env:ZOTERO_LIBRARY_TYPE = "user"  # user or group
$env:ZOTERO_LIBRARY_ID = "<numeric userID or groupID>"
```

For personal libraries, `scripts/zotero_web_import.py` can usually derive the numeric `userID` from the API key metadata. Do not write API keys into repository files, manifests, notes, logs, or chat transcripts.

## Import Command

```bash
python <skill-dir>/scripts/zotero_web_import.py \
  --manifest tmp/literature-harvest/<run>/manifest.json \
  --collection "Literature Harvest/<date>/<topic>" \
  --note-root wiki/sources/论文阅读/<topic> \
  --map "wiki/maps/<topic> Literature Map.md" \
  --pdf-mode imported-url \
  --update
```

`--pdf-mode imported-url` creates a Zotero child attachment pointing at the open PDF URL. `--pdf-mode upload-file --fallback-url-attachment` attempts to upload the local PDF to Zotero File Storage and falls back to a PDF URL attachment if upload fails.

## Behavior

- Creates missing collection path segments.
- Reuses matching existing items by exact normalized title or arXiv ID in `extra`.
- Adds or keeps the target collection membership.
- Adds PDF attachments idempotently.
- Updates `manifest.json`, Obsidian notes, the topic map, and `wiki/log.md` when `--update` is set.

## Fallback

If no `ZOTERO_API_KEY` is available, use `references/zotero-workflow.md` and the local Connector selected-target guard. That fallback still requires the user to create/select the destination collection in Zotero Desktop.
