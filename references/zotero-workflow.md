# Zotero Workflow Guardrails

## Why This Exists

Zotero Connector imports BibTeX/RIS records into the currently selected Zotero library or collection. In this workflow, Codex should not assume the selected collection is correct.

## Required Preflight

Before any Zotero write:

1. Check Zotero readiness with the Zotero skill helper when available:

```bash
python <zotero-helper> status --json
python <zotero-helper> selected-target --json
```

2. Run this skill's target guard:

```bash
python <skill-dir>/scripts/zotero_preflight.py --expected-name "<topic or collection name>" --json
```

3. Continue with `import-bibtex` only when the selected target is clearly the intended target.

## If The Target Is Wrong

Do not import into Zotero.

Instead:

- Finish or preserve `manifest.json`, `references.bib`, PDFs, and Obsidian notes.
- Set manifest/log status to `pending_target_confirmation` or equivalent.
- Tell the user the currently selected Zotero target and the expected target.
- Ask the user to select or create the target collection in Zotero, then resume import.

## Path Policy

- Obsidian notes and `manifest.json` should use relative paths where possible.
- `references.bib` may use absolute local PDF paths when the next step is Zotero import, because Zotero needs to resolve files for attachments.
- Do not commit generated run outputs under `tmp/literature-harvest/`.

## Resume Protocol

After the user switches Zotero to the correct collection:

1. Run `zotero_preflight.py` again.
2. Import the existing `references.bib`.
3. Search/export from Zotero to collect item keys when needed.
4. Update Obsidian notes and the topic map from `TBD` to the imported status.
5. Update `wiki/log.md` counts.
