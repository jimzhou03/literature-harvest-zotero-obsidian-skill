# Obsidian Output

## Paths

- Paper notes: `wiki/sources/论文阅读/<topic-slug>/`
- Topic map: `wiki/maps/<topic-slug> Literature Map.md`
- Run manifest: `tmp/literature-harvest/<date>-<topic-slug>/manifest.json`
- Batch log: `wiki/log.md`

## Paper Note Schema

Use YAML frontmatter:

```yaml
---
type: paper-note
status: deep-read | structured-read | triage | metadata-only
topic: "<topic>"
title: "<paper title>"
year: 2026
venue: "<venue or Unknown>"
zotero_item_key: "<Zotero item key or TBD>"
bibtex_key: "<BibTeX key or TBD>"
doi: "<DOI or TBD>"
arxiv_id: "<arXiv ID or TBD>"
source_url: "<landing page URL>"
pdf_url: "<open PDF URL or TBD>"
pdf_path: "<local path or TBD>"
full_text_status: "ok | missing_pdf | extract_failed | TBD"
full_text_path: "<relative extracted text path or TBD>"
evidence_level: "full_text | abstract_only | metadata_only | failed_extraction"
analysis_confidence: "high | medium | low"
review_gate: "none"
created: "YYYY-MM-DD"
---
```

Recommended sections:

- `# <Title>`
- `## Source`
- `## TL;DR`
- `## Research Question`
- `## Relevance To Query`
- `## Motivation And Basic Idea`
- `## Background / Gap`
- `## Method`
- `## Evaluation`
- `## Key Artifacts`
- `## Tools / Data / Code`
- `## Strengths`
- `## Limitations`
- `## My Takeaways`
- `## Related Papers`
- `## Open Questions`
- `## Links`

For `structured-read` or `deep-read` notes, fill every section. If a section does not apply, write `N/A` or `TBD` with a reason. The note must answer:

- What problem does the paper solve?
- Why was that problem not already handled by prior practice?
- What is the core idea?
- How does the method actually work?
- What datasets, tools, models, prompts, code, or systems are used?
- What do the experiments prove, and what do they not prove?
- Which figures, tables, algorithms, equations, or definitions carry the main claims?
- What are the limitations and reusable takeaways?

For abstract-only notes, use `status: triage`, `evidence_level: abstract_only`, and `analysis_confidence: low`. Still produce an automated analysis, but state that the evidence base is weaker than full-text reading.

## Topic Map Schema

The map page should include:

- Query and normalized keywords.
- Source scope and date range.
- Ranking table with links to paper notes.
- Imported Zotero collection/key summary.
- Full-text extraction and reading-depth counts.
- Method taxonomy: group papers by method family and problem setting.
- Tool/data/code matrix: datasets, benchmarks, code, models, prompts, systems, and reproducibility notes.
- Trend timeline: how methods, assumptions, datasets, and evaluation changed over time.
- Paper relationship graph in prose: baseline, extension, benchmark, critique, system application, or follow-up.
- Research gaps and unresolved questions.
- Recommended reading order.
- Low-confidence analysis queue: items whose automated analysis is based on abstract-only metadata, failed PDF extraction, or missing key artifacts.

## Log Entry

Append to `wiki/log.md`:

```markdown
## YYYY-MM-DD Literature Harvest: <topic>

- Query: <raw user query>
- Sources: <source list>
- Counts: found=<n>, unique=<n>, imported=<n>, pdf_attached=<n>, full_text_extracted=<n>, structured_read=<n>, deep_read=<n>, notes=<n>, low_confidence=<n>
- Outputs: [[<topic-slug> Literature Map]]
- Notes: <blocked sources, missing PDFs, low-confidence evidence, or uncertainty>
```
