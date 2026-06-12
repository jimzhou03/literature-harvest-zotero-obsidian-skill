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
status: deep-read | triage | metadata-only
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
review_required: true
created: "YYYY-MM-DD"
---
```

Recommended sections:

- `# <Title>`
- `## Source`
- `## TL;DR`
- `## Relevance To Query`
- `## Motivation And Basic Idea`
- `## Method`
- `## Evaluation`
- `## Strengths`
- `## Limitations`
- `## My Takeaways`
- `## Links`

For abstract-only notes, use `status: triage` and write `需要人工复核` near the top.

## Topic Map Schema

The map page should include:

- Query and normalized keywords.
- Source scope and date range.
- Ranking table with links to paper notes.
- Imported Zotero collection/key summary.
- Open questions and manual-review queue.

## Log Entry

Append to `wiki/log.md`:

```markdown
## YYYY-MM-DD Literature Harvest: <topic>

- Query: <raw user query>
- Sources: <source list>
- Counts: found=<n>, unique=<n>, imported=<n>, pdf_attached=<n>, notes=<n>, review_required=<n>
- Outputs: [[<topic-slug> Literature Map]]
- Notes: <blocked sources, missing PDFs, or uncertainty>
```
