---
name: literature-harvest-zotero-obsidian
description: Harvest academic papers from open sources into Zotero and Obsidian. Use when the user asks to 抓取, 爬取, 检索, 监控, 批量导入, 下载 PDF, 写入 Zotero, 写入 Obsidian, or analyze literature for keywords/topics such as RAG, KG, knowledge graph, neural network, LLM, ACL, EMNLP/EINLP, CCL, arXiv, top conferences, or top journals.
---

# Literature Harvest to Zotero and Obsidian

## Overview

Use this skill to turn a topic request into a controlled literature-ingestion run: find candidate papers from open academic sources, deduplicate them, import metadata and open PDFs into Zotero, analyze selected papers, and write source-grounded notes into this Obsidian vault.

Respect the vault rules: preserve sources, avoid unsupported claims, mark weak extraction as `需要人工复核`, maintain Obsidian links, and update `wiki/log.md` after batch writes.

## Quick Start

When the user gives keywords such as "抓取 RAG + KG 最近 ACL/EMNLP 论文", first normalize the request:

```bash
python <skill-dir>/scripts/build_literature_plan.py --keywords "RAG, KG" --venues "ACL,EMNLP" --years "2023:2026" --max-papers 20
```

Resolve `<skill-dir>` to this skill's folder, such as `%USERPROFILE%\.codex\skills\literature-harvest-zotero-obsidian` on Windows. Use the generated plan as a checklist, not as final evidence. Then fetch real metadata from the official/open sources listed in the plan.

For an arXiv-only first pass with PDF download and BibTeX generation:

```bash
python <skill-dir>/scripts/harvest_arxiv.py --keywords "RAG, KG" --years "2023:2026" --max-results 20 --download --out tmp/literature-harvest/rag-kg
```

Before any Zotero import, check the current Zotero target:

```bash
python <skill-dir>/scripts/zotero_preflight.py --expected-name "rag-kg" --json
```

If the selected Zotero collection does not match the intended run, stop before import, preserve the generated BibTeX/PDF/Obsidian artifacts, and ask the user to select or create the correct collection.

For full automation without manual Zotero Desktop collection selection, prefer Zotero Web API mode when `ZOTERO_API_KEY` is available:

```bash
python <skill-dir>/scripts/zotero_web_import.py --manifest tmp/literature-harvest/rag-kg/manifest.json --collection "Literature Harvest/<date>/rag-kg" --note-root wiki/sources/论文阅读/rag-kg --map "wiki/maps/rag-kg Literature Map.md" --pdf-mode imported-url --update
```

## Workflow

1. Parse scope.
   - Extract topic keywords, synonyms, venues, year range, language preference, max paper count, and whether the user explicitly asked to write Zotero/Obsidian.
   - Treat `EINLP` as likely `EMNLP`, but mention the correction if it affects source selection.
   - Default to `max-papers=20`, `deep-read=5`, and year range `current year - 3` through current year when the user gives no limits.

2. Build a source plan.
   - Run `scripts/build_literature_plan.py` for a deterministic query plan.
   - Read `references/source-policy.md` before fetching from venues or journals.
   - If the user requested Zotero writes and `ZOTERO_API_KEY` is available, read `references/zotero-web-api.md` and use Web API mode for automatic collection creation/import.
   - If no `ZOTERO_API_KEY` is available, read `references/zotero-workflow.md` and plan the local Connector selected-target fallback.
   - Prefer official/open routes: arXiv API, ACL Anthology, OpenReview, PMLR, CVF OpenAccess, DBLP, Crossref/OpenAlex/Semantic Scholar metadata, publisher pages, and author/project pages.
   - Do not bypass paywalls, login gates, robots restrictions, or publisher terms. Only download PDFs from clearly open sources.

3. Fetch and rank candidates.
   - For arXiv, prefer `scripts/harvest_arxiv.py`; it writes `manifest.json`, `references.bib`, and optional PDFs under the requested output directory.
   - Keep title, authors, year, venue, DOI/arXiv/OpenReview/ACL ID, abstract, landing URL, PDF URL, source name, and access date.
   - Require keyword evidence in title, abstract, author keywords, or official metadata. Do not rely only on filename.
   - Rank by exact phrase matches, synonym matches, venue/year fit, abstract relevance, open-PDF availability, and duplicate confidence.

4. Deduplicate before writing.
   - Merge by DOI, arXiv ID, ACL Anthology ID, OpenReview forum ID, normalized title, then high-confidence title-author-year match.
   - Search Zotero for DOI/title before import.
   - If a duplicate exists, update the run manifest and Obsidian links rather than creating another Zotero item.

5. Import into Zotero.
   - Preferred full-auto path: use `scripts/zotero_web_import.py` with `ZOTERO_API_KEY`. This creates/reuses the collection path, creates/reuses items, adds collection membership, adds PDF attachments, and updates Obsidian outputs.
   - Fallback local path: use the Zotero skill when available. Start with `status --json`, then run `scripts/zotero_preflight.py --expected-name "<intended collection or topic>" --json` before `import-bibtex` or `import-ris`.
   - If the fallback selected Zotero target is wrong, do not import. Mark the run as `pending_target_confirmation`, keep the BibTeX/PDF artifacts, write Obsidian notes with `zotero_item_key: "TBD"`, and tell the user how to resume after switching Zotero collections.
   - Attach open PDFs only when the source is open and the file was successfully downloaded. In Web API mode, use `--pdf-mode imported-url` by default or `--pdf-mode upload-file --fallback-url-attachment` when the user wants Zotero File Storage upload.
   - Record both Zotero item key and exported BibTeX key; they are not the same identifier.

6. Analyze papers.
   - For deep analysis, use the `paper-deep-reading` skill when available.
   - Deep-read open PDFs for the top selected papers. For the rest, write triage notes from metadata/abstract only and label them `需要人工复核`.
   - Separate paper claims from Codex analysis. Do not infer venue, dataset, code, novelty, or results when absent from the source.

7. Write Obsidian outputs.
   - Read `references/obsidian-output.md` before writing notes.
   - Default note root: `wiki/sources/论文阅读/<topic-slug>/`.
   - Create or update a map page in `wiki/maps/` for the topic.
   - Update `wiki/log.md` with run date, query, source set, counts, and manual-review queue.

8. Report completion.
   - Return counts for found, deduplicated, imported, PDF-attached, analyzed, Obsidian-written, skipped, and `需要人工复核`.
   - Link the created/updated Obsidian files and name any blocked source, missing PDF, Zotero issue, or weak extraction.

## Output Discipline

- Keep every claim tied to a source URL, Zotero item, PDF path, or explicit inference label.
- Do not bulk-download from paywalled publisher sites.
- For broad topics, run an abstract-level triage first; deep-read only the selected top papers unless the user asks for exhaustive processing.
- For batch writes, prefer small batches and resumable manifests under `tmp/literature-harvest/`.
- Do not write local absolute paths into Obsidian notes or `manifest.json`; use relative paths there. Keep absolute PDF paths only in local-only BibTeX when needed for Zotero attachment import.

## References

- `references/source-policy.md`: source routing, venue handling, and legal/safety boundaries.
- `references/obsidian-output.md`: note schema, map schema, and log update format.
- `references/zotero-workflow.md`: Zotero selected-target preflight, import guardrails, path policy, and resume protocol.
- `references/zotero-web-api.md`: full-auto Zotero Web API import, collection creation, attachment modes, and credential handling.
