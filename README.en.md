# Literature Harvest to Zotero and Obsidian Skill

[中文](README.md) | English

This is a Codex skill for controlled academic literature harvesting. It turns requests like:

> Fetch 2024-2026 RAG and KG papers from arXiv / ACL / EMNLP / CCL, import open PDFs into Zotero, and write analysis notes to Obsidian.

into a repeatable workflow:

1. Normalize keywords, venues, year ranges, and batch limits.
2. Search official/open academic sources.
3. Download only clearly open-access PDFs.
4. Generate `manifest.json` and `references.bib`.
5. Import metadata and open PDFs into Zotero through Codex's Zotero workflow.
6. Analyze selected papers with Codex.
7. Write source-grounded notes and topic maps into an Obsidian vault.

## When To Use

Use this skill when the user asks Codex to:

- fetch or crawl recent papers for a topic,
- search arXiv, ACL, EMNLP, CCL, or top venues,
- download open PDFs,
- import references into Zotero,
- analyze papers and write notes into Obsidian,
- monitor literature around topics such as RAG, KG, knowledge graphs, neural networks, or LLMs.

## Current Capabilities

- `SKILL.md`: Codex skill entrypoint with triggers, workflow, boundaries, and output discipline.
- `scripts/build_literature_plan.py`: deterministic query/source plan builder.
- `scripts/harvest_arxiv.py`: arXiv MVP harvester that can query arXiv, filter candidates, download open PDFs, and generate BibTeX plus a manifest.
- `scripts/zotero_web_import.py`: Zotero Web API importer that creates collections, imports items, adds PDF attachments, and updates the manifest, Obsidian notes, topic map, and `wiki/log.md`.
- `scripts/zotero_preflight.py`: read-only Zotero selected-target guard before library writes.
- `references/source-policy.md`: source routing, venue handling, and access/copyright boundaries.
- `references/obsidian-output.md`: Obsidian note, map, and log formats.
- `references/zotero-web-api.md`: full-auto Zotero Web API import, credential handling, and attachment modes.
- `references/zotero-workflow.md`: Zotero selected-target guardrails, pending-import state, and resume protocol.
- `agents/openai.yaml`: Codex UI metadata.

## Boundaries

- This skill does not bypass paywalls, login walls, CAPTCHA, publisher restrictions, or robots rules.
- It does not mass-download PDFs from restricted publisher sites.
- It does not fabricate missing DOI, venue, BibTeX key, PDF URL, dataset, code link, or novelty claims.
- arXiv has a runnable MVP script. ACL / EMNLP / CCL are currently guided by source policy and can be extended with dedicated scripts later.
- Large batches should be triaged first. Deep-read only selected papers unless the user explicitly asks for exhaustive processing.
- Zotero writes should use Zotero Web API mode when `ZOTERO_API_KEY` is available, so the skill can create collections and import items automatically. Without an API key, use the local Connector selected-target fallback.

## Installation

Clone this repository into your Codex skills directory:

```powershell
git clone https://github.com/jimzhou03/literature-harvest-zotero-obsidian-skill.git C:\Users\<you>\.codex\skills\literature-harvest-zotero-obsidian
```

Restart Codex or start a new thread after installation if the skill is not visible immediately.

## Example Usage

Build a query/source plan:

```powershell
python C:\Users\<you>\.codex\skills\literature-harvest-zotero-obsidian\scripts\build_literature_plan.py `
  --keywords "RAG, KG" `
  --venues "ACL,EMNLP,CCL" `
  --years "2023:2026" `
  --max-papers 20
```

Run an arXiv-only harvest and download open PDFs:

```powershell
python -B C:\Users\<you>\.codex\skills\literature-harvest-zotero-obsidian\scripts\harvest_arxiv.py `
  --keywords "retrieval augmented generation, knowledge graph" `
  --years "2023:2026" `
  --max-results 20 `
  --download `
  --out tmp\literature-harvest\rag-kg
```

Outputs:

- `manifest.json`: normalized metadata, source URLs, PDF URLs, download status, and relevance scores.
- `references.bib`: BibTeX entries for Zotero import.
- `pdfs/`: downloaded open PDFs.

Path policy:

- `manifest.json` uses relative PDF paths by default.
- `references.bib` uses local absolute PDF paths by default so Zotero can attach downloaded files. Do not commit generated `tmp/literature-harvest/` outputs to public repositories.

## Zotero Workflow

### Full Automation: Zotero Web API

One-time setup: create a Zotero API key with write access and expose it to Codex:

Where to get the API key:

1. Sign in to Zotero.
2. Open [https://www.zotero.org/settings/keys](https://www.zotero.org/settings/keys).
3. Click `Create new private key` or the equivalent button.
4. Recommended permissions:
   - Enable personal library access.
   - Enable write access.
   - If you only use your personal library, do not grant group-library access.
5. Copy the generated key after creation.

Do not paste the key into chat. Do not write it into the repository, manifests, Obsidian notes, or logs.

Temporary setup for the current PowerShell window only:

```powershell
$env:ZOTERO_API_KEY = "your-key"
```

Persistent setup for the current Windows user:

```powershell
[Environment]::SetEnvironmentVariable("ZOTERO_API_KEY", "your-key", "User")
```

After setting the persistent variable, restart Codex or open a new Codex thread so the Codex process can read it.

Then run:

```powershell
python C:\Users\<you>\.codex\skills\literature-harvest-zotero-obsidian\scripts\zotero_web_import.py `
  --manifest tmp\literature-harvest\<run>\manifest.json `
  --collection "Literature Harvest\<date>\<topic>" `
  --note-root wiki\sources\论文阅读\<topic> `
  --map "wiki\maps\<topic> Literature Map.md" `
  --pdf-mode imported-url `
  --update
```

This mode creates the collection path, imports/reuses items, adds PDF attachments, and updates the manifest, Obsidian notes, topic map, and `wiki/log.md`. Use `--pdf-mode upload-file --fallback-url-attachment` to try uploading local PDFs to Zotero File Storage, with URL attachment fallback.

### Fallback: Zotero Connector

Ask Codex to use the Zotero skill after candidate generation:

1. Check Zotero readiness with `status --json`.
2. Check the currently selected Zotero collection:

```powershell
python C:\Users\<you>\.codex\skills\literature-harvest-zotero-obsidian\scripts\zotero_preflight.py `
  --expected-name "rag-kg" `
  --json
```

3. If the target does not match, stop before import and keep `references.bib`, PDFs, the manifest, and Obsidian notes as `pending_target_confirmation`.
4. Search Zotero by DOI/title before import to avoid duplicates.
5. Import the generated BibTeX after the selected target is correct.
6. Attach only PDFs downloaded from open sources.
7. Record both Zotero item keys and BibTeX keys in Obsidian notes.

Note: Zotero Connector imports BibTeX/RIS records into the currently selected library or collection. Web API mode is the automated collection-creation path; Connector fallback validates the current selected target and blocks wrong imports.

## Obsidian Workflow

Default output paths:

```text
wiki/sources/论文阅读/<topic-slug>/
wiki/maps/<topic-slug> Literature Map.md
wiki/log.md
tmp/literature-harvest/<date>-<topic-slug>/manifest.json
```

Use `需要人工复核` for metadata-only or weakly extracted notes.

## Suggested Codex Prompts

```text
Use the literature-harvest-zotero-obsidian skill to fetch 2024-2026 RAG and KG papers from arXiv/ACL/EMNLP, up to 20 papers. First produce a candidate list and download status; do not write to Zotero yet.
```

```text
Use the literature-harvest-zotero-obsidian skill to import the confirmed candidates into Zotero, attach open PDFs, and write deep-reading notes for the top 5 papers into Obsidian.
```

## Local Validation

Validated locally:

- `build_literature_plan.py` runs and normalizes `EINLP` to `EMNLP`.
- `harvest_arxiv.py --help` runs from the global Codex skill path.
- `zotero_preflight.py --help` runs and provides a selected-target guard before import.
- `zotero_web_import.py --help` runs; actual writes require `ZOTERO_API_KEY`.
- Direct arXiv PDF download smoke test produced a valid `%PDF-` file.
- Zotero Desktop local API was reachable after launching Zotero.

Known limitation:

- arXiv API may time out or return HTTP 429 when rate-limited. Use smaller batches, add delays, and retry later.
- Without `ZOTERO_API_KEY`, Zotero collections still need to be created or selected in the Zotero UI; the skill detects mismatches and blocks wrong imports.

## License

MIT
