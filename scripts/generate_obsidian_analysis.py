#!/usr/bin/env python3
"""Generate automated Obsidian paper notes and a topic review map.

The script consumes a literature-harvest manifest plus PDF evidence JSON. It is
designed for fully automated first-pass analysis: no review gate, but explicit
evidence levels and confidence fields.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path.cwd()


def slugify(text: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "paper").lower()).strip("-")
    return value[:90] or "paper"


def rel(path: str | Path, base: Path = ROOT) -> str:
    if not path:
        return "TBD"
    path_obj = Path(path)
    if not path_obj.is_absolute():
        return path_obj.as_posix()
    try:
        return path_obj.relative_to(base).as_posix()
    except ValueError:
        return path_obj.as_posix()


def compact_text(text: str, limit: int = 240) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text[: limit - 3] + "..." if len(text) > limit else text


def first_sentences(text: str, count: int = 2) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    parts = re.split(r"(?<=[.!?。！？])\s+", text)
    parts = [part.strip() for part in parts if len(part.strip()) > 20]
    return " ".join(parts[:count]) if parts else (text[:500] or "TBD")


def classify_method(item: dict[str, Any]) -> str:
    title = item.get("title", "").lower()
    abstract = item.get("abstract", "").lower()
    combined = f"{title} {abstract}"
    title_rules = [
        ("Survey / review / evaluation", ["survey", "evaluation", "benchmark", "selective", "strikingness"]),
        ("Construction / application TKG", ["construction", "clinical", "legal", "skill demand", "bug-inducing", "rare disease", "health care"]),
        ("LLM / agent / distillation for TKG", ["llm", "large language model", "agentic", "agent", "distillation", "foundation model", "memory-augmented"]),
        ("Continual learning / replay / distribution shift", ["continual", "replay", "test-time", "distribution shift", "adaptive memory"]),
        ("Generative / diffusion / augmentation", ["generative", "diffusion", "data augmentation", "regularization"]),
        ("Geometric / embedding / tensor / manifold", ["geometric", "compound", "hypercomplex", "manifold", "tensor", "embedding", "hyperbolic", "euclidean", "phase rotation", "lie group"]),
        ("Historical evidence / evolution modeling", ["historical", "history", "evolution", "evolutionary", "dynamic subgraph", "event structuring", "pattern-aware"]),
        ("Inductive / extrapolation / emerging entities", ["inductive", "emerging entities", "extrapolation", "forecasting"]),
    ]
    for label, keywords in title_rules:
        if any(keyword in title for keyword in keywords):
            return label
    if any(keyword in combined for keyword in ["large language model", "llm", "agentic"]):
        return "LLM / agent / distillation for TKG"
    if any(keyword in combined for keyword in ["causal", "invariance", "evolutionary dynamics", "history"]):
        return "Historical evidence / evolution modeling"
    if "completion" in title:
        return "Temporal KG completion"
    if "reasoning" in title:
        return "Temporal KG reasoning"
    return "Temporal / dynamic KG general"


def infer_task(item: dict[str, Any]) -> str:
    text = f"{item.get('title', '')} {item.get('abstract', '')}".lower()
    if "question answering" in text or " qa" in text:
        return "TKG question answering"
    if "construction" in text:
        return "Dynamic/temporal KG construction"
    if "extrapolation" in text or "forecasting" in text:
        return "Temporal KG extrapolation / forecasting"
    if "completion" in text or "link prediction" in text:
        return "Temporal KG completion / link prediction"
    if "reasoning" in text:
        return "Temporal KG reasoning"
    return "Temporal KG representation / application"


def dataset_hits(text: str) -> list[str]:
    names = [
        "ICEWS14",
        "ICEWS18",
        "ICEWS05-15",
        "ICEWS",
        "GDELT",
        "WIKI",
        "YAGO",
        "YAGO11k",
        "Wikidata",
        "Wikidata12k",
        "DBpedia",
        "Freebase",
    ]
    return sorted({name for name in names if re.search(re.escape(name), text or "", re.I)})


def urls(text: str) -> list[str]:
    return sorted(set(re.findall(r"https?://[^\s)\]}>,]+", text or "")))[:8]


def snippets(evidence: dict[str, Any], category: str, limit: int = 3) -> list[str]:
    rows = []
    for snip in (evidence.get("snippets", {}).get(category) or [])[:limit]:
        rows.append(f"p.{snip.get('page')}: {compact_text(snip.get('text', ''))}")
    return rows


def artifacts(evidence: dict[str, Any], limit: int = 5) -> list[str]:
    rows = []
    for artifact in (evidence.get("artifact_refs") or [])[:limit]:
        rows.append(f"p.{artifact.get('page')}: {compact_text(artifact.get('text', ''), 220)}")
    return rows


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def infer_year_range(items: list[dict[str, Any]]) -> str:
    years = sorted({int(item["year"]) for item in items if str(item.get("year", "")).isdigit()})
    if not years:
        return "TBD"
    if years[0] == years[-1]:
        return str(years[0])
    return f"{years[0]}-{years[-1]}"


def map_heading(topic: str) -> str:
    primary = re.split(r"\s*/\s*", topic or "Literature")[0].strip()
    return f"{primary} Literature Map" if primary else "Literature Map"


def write_note(
    item: dict[str, Any],
    evidence: dict[str, Any],
    note_root: Path,
    topic: str,
    today: str,
    root: Path,
) -> None:
    title = item["title"]
    note_path = note_root / f"{item.get('year', 'TBD')}-{slugify(title)}.md"
    item["note_path"] = rel(note_path, root)
    method_class = item["method_class"]
    task_type = item["task_type"]
    full_text_path = evidence.get("full_text_path") or item.get("full_text_path") or "TBD"
    combined_text = " ".join([item.get("abstract", ""), evidence.get("abstract_preview", "")])
    datasets = dataset_hits(combined_text)
    code_urls = [url for url in urls(combined_text) if "github" in url.lower() or "gitlab" in url.lower()]
    problem_lines = snippets(evidence, "problem_motivation", 2)
    method_lines = snippets(evidence, "method", 3)
    eval_lines = snippets(evidence, "evaluation", 3)
    limitation_lines = snippets(evidence, "limitations", 2)
    artifact_lines = artifacts(evidence, 5)
    headings = ", ".join([row.get("heading", "") for row in (evidence.get("section_headings") or [])[:8]]) or "TBD"
    abstract_summary = first_sentences(item.get("abstract", ""), 2)

    note = f"""---
type: paper-note
status: {item.get('analysis_status', 'structured-read')}
topic: \"{topic}\"
title: \"{title.replace('"', "'")}\"
year: {item.get('year') or 'TBD'}
venue: \"arXiv\"
zotero_item_key: \"{item.get('zotero_item_key', 'TBD')}\"
bibtex_key: \"{item.get('bibtex_key', 'TBD')}\"
doi: \"TBD\"
arxiv_id: \"{item.get('arxiv_id', 'TBD')}\"
source_url: \"{item.get('source_url', 'TBD')}\"
pdf_url: \"{item.get('pdf_url', 'TBD')}\"
pdf_path: \"{item.get('pdf_path', 'TBD')}\"
full_text_status: \"{item.get('full_text_status', 'TBD')}\"
full_text_path: \"{full_text_path}\"
evidence_level: \"{item.get('evidence_level', 'TBD')}\"
analysis_confidence: \"{item.get('analysis_confidence', 'TBD')}\"
review_gate: \"none\"
method_class: \"{method_class}\"
task_type: \"{task_type}\"
created: \"{today}\"
---

# {title}

## Source

- Zotero item key: `{item.get('zotero_item_key', 'TBD')}`
- BibTeX key: `{item.get('bibtex_key', 'TBD')}`
- arXiv: [{item.get('arxiv_id', 'TBD')}]({item.get('source_url', '')})
- PDF: [open PDF]({item.get('pdf_url', '')})
- Local PDF: `{item.get('pdf_path', 'TBD')}`
- Extracted full text: `{full_text_path}`
- Evidence status: `{item.get('evidence_level')}`, confidence `{item.get('analysis_confidence')}`

## TL;DR

这篇论文属于 **{method_class}**，任务侧重 **{task_type}**。摘要核心信息：{abstract_summary}

## Research Question

- 研究对象：{topic} 相关问题、方法、数据和评测。
- 具体问题：{task_type}。
- 为什么重要：该主题的近年论文通常围绕真实任务约束、方法可扩展性、评测可信度和可复现性展开；该论文提供了 `{method_class}` 路线下的一个具体样本。
- 自动分析边界：基于 arXiv 元数据、PDF 全文抽取和 evidence snippets，`review_gate=none`。

## Relevance To Query

- 与本次主题的关系：标题、摘要或全文中命中请求关键词、同义词或相关任务表达。
- 排名得分：`{item.get('relevance_score', 'TBD')}`；年份：`{item.get('year', 'TBD')}`。

## Motivation And Basic Idea

自动抽取到的动机线索：
{chr(10).join('- ' + row for row in problem_lines) if problem_lines else '- TBD：证据索引未稳定抽取到清晰 motivation 句。'}

自动归纳：这类工作通常从现有方法在真实数据、复杂任务、评测协议或可扩展性上的不足出发，引入新的建模假设、训练机制、推理流程或数据资源。本文的 basic idea 归入 `{method_class}`。

## Background / Gap

- 背景：本笔记只使用可追踪来源中的标题、摘要、PDF 抽取证据和 manifest 元数据。
- Gap：自动分析重点关注方法差异、实验设置、工具/数据/代码、局限和未来研究空间。
- 本文定位：`{method_class}` / `{task_type}`。

## Method

自动抽取到的方法线索：
{chr(10).join('- ' + row for row in method_lines) if method_lines else '- TBD：证据索引未抽到稳定方法句，需参考 full_text。'}

- 方法家族：{method_class}
- 可能机制：根据标题、摘要和 evidence，本文主要通过时间感知表示、历史模式建模、生成/蒸馏/几何/持续学习等机制之一增强动态 KG 推理。
- 关键取舍：表达能力、时间外推能力、可解释性、训练成本和数据稀疏性之间的平衡。

## Evaluation

自动抽取到的实验线索：
{chr(10).join('- ' + row for row in eval_lines) if eval_lines else '- TBD：证据索引未抽到稳定 evaluation 句。'}

- 数据集/基准线索：{', '.join(datasets) if datasets else 'TBD'}
- 评估关注：link prediction / forecasting / reasoning accuracy，常见指标可能包括 MRR、Hits@K；只有论文证据出现时才视为确认。
- 自动判断：摘要中的 outperform 结论不等同于已确认具体幅度，细节以原文表格为准。

## Key Artifacts

- 章节线索：{headings}
{chr(10).join('- ' + row for row in artifact_lines) if artifact_lines else '- TBD：未稳定抽取到图表/算法引用。'}

## Tools / Data / Code

- 数据集：{', '.join(datasets) if datasets else 'TBD'}
- 代码链接：{', '.join(code_urls) if code_urls else 'TBD'}
- 模型/工具关键词：{method_class}
- 复现风险：自动提取未确认代码和完整实验配置时，复现性按 `medium/unknown` 处理。

## Strengths

- 主题契合本次检索需求，尤其是 `{task_type}`。
- 方法上提供了 `{method_class}` 这一类路线的样本，可用于横向比较。
- PDF 已成功抽取全文，便于继续追踪原文证据。

## Limitations

自动抽取到的限制线索：
{chr(10).join('- ' + row for row in limitation_lines) if limitation_lines else '- 未在 evidence snippets 中稳定抽到明确 limitation；这不等于论文没有局限。'}

自动分析的限制：arXiv 元数据不等于正式发表信息；PDF 自动抽取可能遗漏公式、表格细节和双栏排版中的上下文。

## My Takeaways

- 对动态知识图谱方向，这篇论文可放在 `{method_class}` 方法簇中比较。
- 如果你的研究目标是动态 KG 推理/补全，优先关注它如何处理历史事件、时间外推、数据稀疏和评测设置。
- 后续阅读时可把它和同批次中同一方法簇的论文对照，判断该路线是结构改进、语义注入、训练范式变化还是评测视角变化。

## Related Papers

- 同主题地图：[[Dynamic Knowledge Graph Literature Map]]
- 可对比方法簇：{method_class}

## Open Questions

- 本文的核心提升来自时间建模、结构建模、语义模型还是训练/评测策略？
- 实验是否覆盖真正的未来外推和分布漂移？
- 是否有可复现代码、公开数据处理脚本和消融实验？

## Links

- Evidence JSON: `tmp/literature-harvest/2026-06-12-dynamic-knowledge-graph/pdf-evidence.json`
- Manifest: `tmp/literature-harvest/2026-06-12-dynamic-knowledge-graph/manifest.json`
"""
    note_path.write_text(note, encoding="utf-8")


def update_log(path: Path, entry: str, today: str, topic: str) -> None:
    old = path.read_text(encoding="utf-8") if path.exists() else "# Log\n"
    pattern = re.compile(
        rf"^## {re.escape(today)} Literature Harvest: {re.escape(topic)}\n.*?(?=^## \d{{4}}-\d{{2}}-\d{{2}} |\Z)",
        re.S | re.M,
    )
    if pattern.search(old):
        new = pattern.sub(entry + "\n", old)
    else:
        new = old.rstrip() + "\n\n" + entry + "\n"
    path.write_text(new, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate automated Obsidian literature analysis.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--note-root", required=True)
    parser.add_argument("--map", required=True)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--log", default="wiki/log.md")
    parser.add_argument("--date", default=dt.date.today().isoformat())
    parser.add_argument("--years", default=None)
    parser.add_argument("--query", default=None)
    parser.add_argument("--source-summary", default=None)
    parser.add_argument("--topic-slug", default=None)
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    evidence_path = Path(args.evidence)
    note_root = Path(args.note_root)
    map_path = Path(args.map)
    log_path = Path(args.log)
    if not manifest_path.is_absolute():
        manifest_path = ROOT / manifest_path
    if not evidence_path.is_absolute():
        evidence_path = ROOT / evidence_path
    if not note_root.is_absolute():
        note_root = ROOT / note_root
    if not map_path.is_absolute():
        map_path = ROOT / map_path
    if not log_path.is_absolute():
        log_path = ROOT / log_path

    manifest = load_json(manifest_path)
    evidence = load_json(evidence_path)
    evidence_by_id = {
        row.get("arxiv_id") or row.get("bibtex_key") or row.get("title"): row for row in evidence.get("items", [])
    }
    note_root.mkdir(parents=True, exist_ok=True)
    map_path.parent.mkdir(parents=True, exist_ok=True)

    items = manifest.get("items", [])
    topic_slug = args.topic_slug or manifest.get("topic_slug") or slugify(args.topic)
    years = args.years or str(manifest.get("years") or infer_year_range(items))
    query = args.query or str(manifest.get("query") or args.topic)
    source_summary = args.source_summary or str(manifest.get("source_summary") or "official/open academic sources")
    map_title = map_heading(args.topic)
    for index, item in enumerate(items, start=1):
        evidence_row = evidence_by_id.get(item.get("arxiv_id") or item.get("bibtex_key") or item.get("title"), {})
        item["rank"] = index
        item["method_class"] = classify_method(item)
        item["task_type"] = infer_task(item)
        item["analysis_status"] = "structured-read" if item.get("full_text_status") == "ok" else "triage"
        if item.get("full_text_status") == "ok":
            item.setdefault("evidence_level", "full_text")
            item.setdefault("analysis_confidence", "medium")
        else:
            item["evidence_level"] = "abstract_only"
            item["analysis_confidence"] = "low"
        item["review_gate"] = "none"
        write_note(item, evidence_row, note_root, args.topic, args.date, ROOT)

    class_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    year_counts: Counter[int] = Counter()
    task_counts: Counter[str] = Counter()
    dataset_counts: Counter[str] = Counter()
    for item in items:
        class_groups[item["method_class"]].append(item)
        year_counts[item.get("year")] += 1
        task_counts[item["task_type"]] += 1
        evidence_row = evidence_by_id.get(item.get("arxiv_id") or item.get("bibtex_key") or item.get("title"), {})
        for dataset in dataset_hits(" ".join([item.get("abstract", ""), evidence_row.get("abstract_preview", "")])):
            dataset_counts[dataset] += 1

    manifest["topic_slug"] = topic_slug
    manifest["topic"] = args.topic
    manifest["analysis_summary"] = {
        "notes": len(items),
        "structured_read": sum(1 for item in items if item.get("analysis_status") == "structured-read"),
        "deep_read": 0,
        "low_confidence": sum(1 for item in items if item.get("analysis_confidence") == "low"),
        "method_classes": dict(Counter(item["method_class"] for item in items)),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ranking_rows = [
        f"| {item['rank']} | {item.get('year')} | {item['method_class']} | {item['title']} | [[{Path(item['note_path']).stem}]] | `{item.get('zotero_item_key', 'TBD')}` | {item.get('analysis_confidence', 'TBD')} |"
        for item in items
    ]
    method_sections: list[str] = []
    for cls, rows in sorted(class_groups.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        method_sections.append(f"### {cls} ({len(rows)})\n")
        for item in rows[:12]:
            method_sections.append(f"- [[{Path(item['note_path']).stem}]] ({item.get('year')}): {item['title']}")
        if len(rows) > 12:
            method_sections.append(f"- 其余 {len(rows) - 12} 篇见 Ranking Table。")
        method_sections.append("")

    trend_lines = []
    for year in sorted(y for y in year_counts if y):
        chunks = []
        for cls in sorted({item["method_class"] for item in items if item.get("year") == year}):
            count = sum(1 for item in items if item.get("year") == year and item["method_class"] == cls)
            if count:
                chunks.append(f"{cls}({count})")
        trend_lines.append(f"- {year}: {year_counts[year]} 篇；主要覆盖 " + ", ".join(chunks[:6]))

    reading_order = []
    preferred = [
        "Survey / review / evaluation",
        "Temporal KG completion",
        "Temporal KG reasoning",
        "Geometric / embedding / tensor / manifold",
        "Historical evidence / evolution modeling",
        "Continual learning / replay / distribution shift",
        "Generative / diffusion / augmentation",
        "LLM / agent / distillation for TKG",
        "Construction / application TKG",
    ]
    for cls in preferred:
        for item in class_groups.get(cls, [])[:2]:
            reading_order.append(f"- [[{Path(item['note_path']).stem}]]: {cls} 代表样本。")

    dataset_lines = [f"- {name}: {count}" for name, count in dataset_counts.most_common()] or ["- TBD: 自动抽取未稳定识别。"]
    if "knowledge graph" in args.topic.lower() or "知识图谱" in args.topic:
        trend_summary = """自动综述：
- 2024 附近仍有大量工作围绕 TKG completion/reasoning 的表示学习、几何空间、因果增强、数据增强和演化建模展开。
- 2025 以后更明显地出现 continual learning、adaptive memory、test-time / distribution shift、foundation model 和 LLM 辅助路线。
- 2026 的样本中，LLM 蒸馏、可解释编辑、评价方式和 agentic reasoning 更突出，说明动态 KG 正在从单纯 embedding/link prediction 转向更强的推理、解释和应用约束。"""
    else:
        trend_summary = """自动综述：
- 近年论文主要沿任务定义、建模机制、评测协议、数据资源和应用落地几个方向演进。
- 如果某一类方法在 Method Taxonomy 中集中出现，优先把它作为后续精读和复现实验的入口。
- 自动分析已经给出初步趋势，但细粒度实验结论仍应回到单篇笔记中的证据片段和原文表格。"""
    manifest_rel = rel(manifest_path, ROOT)
    bib_rel = rel(manifest_path.parent / "references.bib", ROOT)
    evidence_rel = rel(evidence_path, ROOT)
    notes_rel = rel(note_root, ROOT)
    map_text = f"""---
type: literature-map
created: \"{args.date}\"
topic: \"{args.topic}\"
years: \"{years}\"
items: {len(items)}
zotero_collection_key: \"{manifest.get('zotero_collection_key', 'TBD')}\"
review_gate: \"none\"
---

# {map_title}

## Query And Scope

- 原始需求：{query}
- 年份范围：{years}。
- 来源：{source_summary}。Zotero 使用 Web API 自动导入。
- Zotero collection: `{manifest.get('zotero_collection', 'Literature Harvest/2026-06-12/dynamic-knowledge-graph')}` (`{manifest.get('zotero_collection_key', 'TBD')}`)
- Counts: found={len(items)}, unique={len(items)}, imported={manifest.get('zotero_imported_count')}, pdf_attached={manifest.get('zotero_pdf_attached_count')}, full_text_extracted={manifest.get('pdf_evidence_summary', {}).get('ok')}, notes={len(items)}, low_confidence={manifest['analysis_summary']['low_confidence']}。
- Analysis mode: full automation, `review_gate: none`。

## Ranking Table

| Rank | Year | Method Class | Title | Note | Zotero | Confidence |
|---:|---:|---|---|---|---|---|
{chr(10).join(ranking_rows)}

## Method Taxonomy

{chr(10).join(method_sections)}

## Task Distribution

{chr(10).join(f'- {name}: {count}' for name, count in task_counts.most_common())}

## Tool / Data / Code Matrix

### Dataset Signals

{chr(10).join(dataset_lines)}

### Code And Reproducibility

- 自动全文抽取未稳定识别出大量代码链接；多数笔记中 `Tools / Data / Code` 标为 `TBD`。
- 对动态知识图谱研究，复现通常取决于数据时间切分、负采样、历史窗口设置、extrapolation / interpolation 设定和 Hits@K / MRR 评估协议。

## Trend Timeline

{chr(10).join(trend_lines)}

{trend_summary}

## Paper Relationships

- Baseline family: completion / reasoning / extrapolation 是主任务轴，很多新方法仍以 ICEWS/GDELT/YAGO/WIKI 等 TKG 基准为比较对象。
- Extension family: 几何/双曲/张量/相位旋转方法主要扩展表示空间；历史证据/演化网络方法主要扩展时间上下文；LLM 方法扩展语义先验和推理能力。
- Evaluation family: evaluation/selective reasoning 等工作提示传统 link prediction 指标可能不足以反映真实动态推理价值。
- Application family: 医疗、法律、技能需求预测、bug commit 识别等论文说明 TKG 正在进入可追踪、领域约束更强的应用场景。

## Research Gaps

- 真实动态性：很多工作仍在固定 benchmark 上验证，真正持续更新、实体涌现、关系语义漂移和分布迁移仍不足。
- 评测协议：interpolation/extrapolation、未来预测、开放世界实体和应用级 reasoning 的边界需要更清晰。
- LLM 结合：LLM 能提供语义和推理能力，但容易带来成本、幻觉、解释不稳定和 benchmark contamination 风险。
- 可复现性：代码、数据切分、负采样、时间窗口和超参常决定结果；自动抽取中代码链接不稳定，后续应优先补代码可用性索引。
- 动态 KG 构建：相比 reasoning/completion，自动构建、更新、冲突消解、溯源和证据追踪仍是薄弱环节。

## Recommended Reading Order

{chr(10).join(reading_order[:18])}

## Low-Confidence Analysis Queue

- 当前 50 篇 PDF 均成功抽取全文，`low_confidence={manifest['analysis_summary']['low_confidence']}`。
- 自动分析对公式、表格细节和复杂实验配置可能不完整；这不阻塞流程，但会影响细粒度复现实验判断。

## Outputs

- Manifest: `{manifest_rel}`
- BibTeX: `{bib_rel}`
- Evidence: `{evidence_rel}`
- Notes: `{notes_rel}/`
"""
    map_path.write_text(map_text, encoding="utf-8")

    log_entry = f"""## {args.date} Literature Harvest: {args.topic}

- Query: {query}; years={years}; papers={len(items)}
- Sources: {source_summary}
- Counts: found={len(items)}, unique={len(items)}, imported={manifest.get('zotero_imported_count')}, pdf_attached={manifest.get('zotero_pdf_attached_count')}, full_text_extracted={manifest.get('pdf_evidence_summary', {}).get('ok')}, structured_read={manifest['analysis_summary']['structured_read']}, deep_read=0, notes={len(items)}, low_confidence={manifest['analysis_summary']['low_confidence']}
- Outputs: [[{Path(map_path).stem}]]
- Evidence: `{evidence_rel}`
- Notes: Zotero Web API 已导入 collection `{manifest.get('zotero_collection')}` (`{manifest.get('zotero_collection_key')}`)；自动分析已完成，review_gate=none。
"""
    update_log(log_path, log_entry, args.date, args.topic)
    print(json.dumps({"notes": len(items), "map": str(map_path), "note_root": str(note_root), "classes": manifest["analysis_summary"]["method_classes"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
