# Deep Reading And Review Workflow

Use this reference whenever the user expects more than retrieval or short summaries: `精读`, `从头到尾`, `完整分析`, `方法`, `实验`, `工具`, `趋势`, `gap`, `综述`, or `研究路线`.

## Role Split

Treat literature work as four connected but different jobs:

1. Paper search: discover candidates, download open PDFs, deduplicate, and rank.
2. Paper dissection: read one paper end to end and reconstruct problem, method, experiments, artifacts, and limits.
3. Literature review: group many papers by method family, task setting, dataset/tooling, chronology, and unresolved gap.
4. Research workflow support: preserve the library, evidence, reading order, and follow-up questions so the user can judge from original papers.

Do not collapse these into "summarize each paper in one or two sentences." A short summary is only a triage artifact.

## Reading Depth

- `triage`: title/abstract/metadata only. Use for broad discovery or papers without accessible full text. Mark `需要人工复核`.
- `structured-read`: accessible full PDF was text-extracted and read through problem, method, evaluation, artifacts, and limitations. This is the default for selected papers.
- `deep-read`: structured-read plus critical synthesis, related-work positioning, artifact-level evidence, and concrete takeaways. Use for top papers, user-selected papers, or manageable batches.

Default policy:

- Unknown direction or broad keyword: triage all candidates, then structured-read/deep-read the top set.
- User asks "which papers should I read": do not deep-read all papers first; build the candidate pool and reading order.
- User asks "what has this direction done in recent years": write a review map with method groups, trend timeline, and gaps; deep-read representative papers.
- User asks "from beginning to end" or "complete analysis": structured-read every accessible PDF if the batch is small; otherwise explain the batch/depth tradeoff and proceed with the top set.

## Evidence Extraction

Run after PDFs are downloaded or Zotero items have open PDF attachments:

```bash
python <skill-dir>/scripts/extract_pdf_evidence.py \
  --manifest tmp/literature-harvest/<run>/manifest.json \
  --write-text \
  --update
```

If the script reports that `pypdf` is missing, install the lightweight dependency:

```bash
python -m pip install --user pypdf
```

The script writes:

- `pdf-evidence.json`: page count, character count, detected headings, problem/method/evaluation/limitation snippets, and figure/table/algorithm references.
- `full_text/*.txt`: extracted page-marked full text when `--write-text` is set.
- manifest backfill fields such as `full_text_status`, `full_text_chars`, `full_text_path`, and `pdf_evidence_path`.

Use extraction as an evidence index. It does not replace reading. If a snippet seems important, inspect the nearby full text before making a claim.

## Single-Paper Note Requirements

Every `structured-read` or `deep-read` note must include these sections:

- `TL;DR`: 2-4 sentences only after the paper is read.
- `Research Question`: research object, concrete problem, importance, and paper boundary.
- `Motivation And Basic Idea`: why the problem exists, the simplest idea, and how the idea answers the gap.
- `Method`: core mechanism, pipeline/algorithm/system design, assumptions, key definitions, and why the design is not a simpler alternative.
- `Evaluation`: datasets/benchmarks, metrics, baselines, ablations or case studies, and what the results actually support.
- `Key Artifacts`: important figures, tables, equations, algorithms, definitions, and what claim each supports.
- `Tools / Data / Code`: code links, datasets, benchmarks, environments, prompts, models, toolchains, or `TBD`.
- `Strengths`: what is convincing and why.
- `Limitations`: weak assumptions, missing baselines, narrow datasets, reproducibility gaps, or deployment costs.
- `My Takeaways`: reusable ideas, relation to the user's topic, and follow-up questions.
- `Reading Confidence`: `high`, `medium`, or `low`, with reasons such as full-text extraction quality, missing PDF, or abstract-only status.

Keep claims traceable to source URLs, Zotero item keys, PDF paths, page numbers, or evidence snippets. Use `作者声称`, `论文展示`, and `我的判断` to separate attribution.

## Topic Review Map Requirements

A topic map is not a list of paper blurbs. It must include:

- Candidate-pool summary: query, sources, year range, found/unique/imported/extracted/read counts.
- Reading-depth table: each paper's status (`triage`, `structured-read`, `deep-read`) and why it was ranked.
- Method taxonomy: group papers by method family, not only by keyword.
- Tool/data/code matrix: datasets, benchmarks, code availability, models, prompts, systems, and reproducibility notes.
- Trend timeline: what changed over years, including shifts in assumptions, evaluation, and deployment constraints.
- Paper relationships: which papers are baselines, extensions, critiques, benchmarks, or system applications.
- Research gaps: unresolved problems, weak evidence, missing evaluation, or promising follow-up questions.
- Recommended reading order: entry papers, foundation papers, representative methods, and papers to defer.
- Manual verification queue: claims that need the user to return to the original PDF.

## Guardrails

- Do not overstate venue, novelty, citation impact, code availability, dataset usage, or experiment results when the paper does not support it.
- Do not treat arXiv popularity as peer-reviewed quality.
- Do not let the review map hide uncertainty. Mark abstract-only, extraction-failed, and metadata-only papers clearly.
- Do not use "AI says" as evidence. The evidence is the paper, metadata source, Zotero item, PDF, or extracted text.
- The final human judgment still belongs to the user. The skill should accelerate finding, dissecting, comparing, and organizing evidence.
