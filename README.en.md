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
- `scripts/zotero_preflight.py`: read-only Zotero selected-target guard before library writes.
- `references/source-policy.md`: source routing, venue handling, and access/copyright boundaries.
- `references/obsidian-output.md`: Obsidian note, map, and log formats.
- `references/zotero-workflow.md`: Zotero selected-target guardrails, pending-import state, and resume protocol.
- `agents/openai.yaml`: Codex UI metadata.

## Boundaries

- This skill does not bypass paywalls, login walls, CAPTCHA, publisher restrictions, or robots rules.
- It does not mass-download PDFs from restricted publisher sites.
- It does not fabricate missing DOI, venue, BibTeX key, PDF URL, dataset, code link, or novelty claims.
- arXiv has a runnable MVP script. ACL / EMNLP / CCL are currently guided by source policy and can be extended with dedicated scripts later.
- Large batches should be triaged first. Deep-read only selected papers unless the user explicitly asks for exhaustive processing.
- Zotero writes must be preceded by selected-target validation. If the current Zotero collection is wrong, generate import-ready artifacts but do not import.

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

Note: Zotero Connector imports BibTeX/RIS records into the currently selected library or collection. This skill validates that target; it does not create or switch Zotero collections for the user.

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
- Direct arXiv PDF download smoke test produced a valid `%PDF-` file.
- Zotero Desktop local API was reachable after launching Zotero.

Known limitation:

- arXiv API may time out or return HTTP 429 when rate-limited. Use smaller batches, add delays, and retry later.
- Zotero collections still need to be created or selected in the Zotero UI; the skill detects mismatches and blocks wrong imports.

## License

MIT
