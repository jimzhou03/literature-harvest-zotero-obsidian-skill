---
name: literature-harvest-zotero-obsidian
description: Harvest academic papers from open sources into Zotero and Obsidian, then read PDFs into structured research notes and topic-level synthesis. Use when the user asks to 抓取, 爬取, 检索, 监控, 批量导入, 下载 PDF, 写入 Zotero, 写入 Obsidian, 精读, 从头到尾读论文, 拆解方法/实验/工具/趋势, 做文献综述, or analyze literature for keywords/topics such as RAG, KG, knowledge graph, neural network, LLM, ACL, EMNLP/EINLP, CCL, arXiv, top conferences, or top journals.
---

# Literature Harvest to Zotero and Obsidian

## Overview

Use this skill to turn a topic request into a fully automated literature-reading run: find candidate papers from open academic sources, deduplicate them, import metadata and open PDFs into Zotero, extract full-text evidence from accessible PDFs, write structured paper notes, and synthesize methods, tools, trends, and gaps into this Obsidian vault.

Respect the vault rules: preserve sources, avoid unsupported claims, record weak extraction as low confidence, maintain Obsidian links, and update `wiki/log.md` after batch writes.

This is not a "one paragraph summary" skill. Default to making the reading process visible: what problem the paper solves, how the method works, what experiments support it, what artifacts matter, and what remains uncertain. No review gate should block the workflow; finish the automated analysis and express uncertainty with evidence level, confidence, and limitations.

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

For full automation without Zotero Desktop collection selection, prefer Zotero Web API mode when `ZOTERO_API_KEY` is available:

```bash
python <skill-dir>/scripts/zotero_web_import.py --manifest tmp/literature-harvest/rag-kg/manifest.json --collection "Literature Harvest/<date>/rag-kg" --note-root wiki/sources/论文阅读/rag-kg --map "wiki/maps/rag-kg Literature Map.md" --pdf-mode imported-url --update
```

After PDFs are available, extract full-text evidence before writing final notes:

```bash
python <skill-dir>/scripts/extract_pdf_evidence.py --manifest tmp/literature-harvest/rag-kg/manifest.json --write-text --update
```

## Workflow

1. Parse scope.
   - Extract topic keywords, synonyms, venues, year range, language preference, max paper count, requested reading depth, and whether the user explicitly asked to write Zotero/Obsidian.
   - Treat `EINLP` as likely `EMNLP`, but mention the correction if it affects source selection.
   - Default to `max-papers=20`, `deep-read=5`, and year range `current year - 3` through current year when the user gives no limits.
   - If the user says `精读`, `从头到尾`, `完整分析`, or asks what method/experiment/trend proves, treat accessible PDFs as structured-read targets, not abstract-only triage.

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

6. Extract PDF evidence.
   - Read `references/deep-reading-workflow.md` before writing final reading notes.
   - Run `scripts/extract_pdf_evidence.py --manifest <manifest> --write-text --update` for accessible PDFs.
   - Use the generated `pdf-evidence.json` and `full_text/` files as evidence aids, not as final conclusions.
   - If extraction fails, keep the paper in Zotero, mark the note `metadata-only` or `triage`, and explain the failure.

7. Analyze papers.
   - For deep analysis, use the `paper-deep-reading` skill when available.
   - For each structured-read/deep-read paper, do three passes: abstract/introduction/conclusion, method/system/algorithm, then evaluation/artifacts/limitations.
   - Deep-read open PDFs for the top selected papers by default. If the user explicitly asks for complete reading and the batch is manageable, deep-read every accessible PDF; otherwise triage all and deep-read the agreed top set.
   - For the rest, write automated triage notes from metadata/abstract only and label them `evidence_level: abstract_only` plus `analysis_confidence: low`; do not block the run.
   - Separate paper claims from Codex analysis. Do not infer venue, dataset, code, novelty, or results when absent from the source.
   - Each final note must answer: solved problem, core idea, method mechanism, experiment setup/results, key artifacts, strengths, limitations, reusable tools/datasets/code, and your concrete takeaways.

8. Write Obsidian outputs.
   - Read `references/obsidian-output.md` before writing notes.
   - Default note root: `wiki/sources/论文阅读/<topic-slug>/`.
   - Create or update a map page in `wiki/maps/` for the topic.
   - The map must include method taxonomy, tool/dataset/code matrix, trend timeline, paper-to-paper relationships, research gaps, and a recommended reading order.
   - Update `wiki/log.md` with run date, query, source set, counts, and low-confidence analysis queue.

9. Report completion.
   - Return counts for found, deduplicated, imported, PDF-attached, full-text-extracted, structured-read, deep-read, Obsidian-written, skipped, and low-confidence items.
   - Link the created/updated Obsidian files and name any blocked source, missing PDF, Zotero issue, or weak extraction.

## Output Discipline

- Keep every claim tied to a source URL, Zotero item, PDF path, full-text evidence path, page reference, or explicit inference label.
- Do not bulk-download from paywalled publisher sites.
- For broad topics, run an abstract-level triage first; deep-read only the selected top papers unless the user asks for exhaustive processing. Make the triage/deep-read boundary explicit in the map.
- For batch writes, prefer small batches and resumable manifests under `tmp/literature-harvest/`.
- Do not write local absolute paths into Obsidian notes or `manifest.json`; use relative paths there. Keep absolute PDF paths only in local-only BibTeX when needed for Zotero attachment import.
- Do not pause for external verification. Complete the automated analysis, but make evidence limitations explicit with `analysis_confidence`, `evidence_level`, and concrete unsupported-claim notes.

## References

- `references/source-policy.md`: source routing, venue handling, and legal/safety boundaries.
- `references/deep-reading-workflow.md`: reading-depth policy, full-text evidence extraction, single-paper note requirements, and topic synthesis requirements.
- `references/obsidian-output.md`: note schema, map schema, and log update format.
- `references/zotero-workflow.md`: Zotero selected-target preflight, import guardrails, path policy, and resume protocol.
- `references/zotero-web-api.md`: full-auto Zotero Web API import, collection creation, attachment modes, and credential handling.
