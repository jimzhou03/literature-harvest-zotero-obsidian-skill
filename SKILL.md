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

## Workflow

1. Parse scope.
   - Extract topic keywords, synonyms, venues, year range, language preference, max paper count, and whether the user explicitly asked to write Zotero/Obsidian.
   - Treat `EINLP` as likely `EMNLP`, but mention the correction if it affects source selection.
   - Default to `max-papers=20`, `deep-read=5`, and year range `current year - 3` through current year when the user gives no limits.

2. Build a source plan.
   - Run `scripts/build_literature_plan.py` for a deterministic query plan.
   - Read `references/source-policy.md` before fetching from venues or journals.
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
   - Use the Zotero skill when available. Start with the helper `status --json`.
   - If the prompt explicitly says to import/write Zotero, proceed with imports after candidate criteria are concrete. Otherwise show the candidate table and ask for confirmation before library writes.
   - Prefer BibTeX/RIS import for metadata. Attach open PDFs only when the source is open and the file was successfully downloaded.
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

## References

- `references/source-policy.md`: source routing, venue handling, and legal/safety boundaries.
- `references/obsidian-output.md`: note schema, map schema, and log update format.
