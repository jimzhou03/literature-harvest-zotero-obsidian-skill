# Literature Harvest to Zotero and Obsidian Skill

中文 | [English](README.en.md)

这是一个面向 Codex 的文献抓取与整理 skill。它的目标是把你类似下面这种自然语言需求：

> 抓取 2024-2026 年 RAG 和 KG 相关的 arXiv / ACL / EMNLP / CCL 论文，能下载 PDF 的导入 Zotero，并把分析结果写进 Obsidian。

转成一套可复用、可审计的流程：

1. 识别和归一化关键词、会议/期刊、年份范围和数量限制。
2. 从 arXiv、ACL Anthology、OpenReview、PMLR、CVF、DBLP、OpenAlex、Semantic Scholar 等公开/官方来源检索候选论文。
3. 只下载明确开放访问的 PDF。
4. 生成 `manifest.json` 和 `references.bib`，用于追踪来源和导入 Zotero。
5. 通过 Codex 的 Zotero 工作流把元数据和开放 PDF 写入 Zotero。
6. 通过 Codex 分析选中的论文内容。
7. 把来源明确、带复核标记的中文文献笔记写入 Obsidian vault。

## 适用场景

当你对 Codex 说下面这些话时，这个 skill 应该被触发：

- “抓取 RAG 最近的 arXiv 论文”
- “爬取 KG / 知识图谱相关 ACL、EMNLP、CCL 论文”
- “下载神经网络相关论文 PDF 并导入 Zotero”
- “检索顶会顶刊文献，分析后写进 Obsidian”
- “监控某个关键词的新论文，先给我候选清单”

它特别适合长期维护一个“Zotero 负责引用管理 + Obsidian 负责研究笔记”的文献工作流。

## 当前能力

- `SKILL.md`：Codex skill 入口，包含触发词、工作流、边界和输出纪律。
- `scripts/build_literature_plan.py`：根据关键词、会议、年份生成检索计划。
- `scripts/harvest_arxiv.py`：arXiv MVP 抓取器，可以查询 arXiv、过滤候选、下载开放 PDF、生成 BibTeX 和 manifest。
- `references/source-policy.md`：定义各类来源的优先级、会议处理策略和版权/访问边界。
- `references/obsidian-output.md`：定义 Obsidian 笔记、topic map 和日志格式。
- `agents/openai.yaml`：Codex UI 元数据。

## 当前边界

- 不绕过付费墙、登录墙、验证码、出版社限制或 robots 规则。
- 不从 ACM、IEEE、Springer、Elsevier 等页面批量强行下载 PDF。
- 不编造缺失的 DOI、BibTeX key、venue、PDF URL、数据集、代码链接或论文贡献。
- arXiv 已有可执行脚本；ACL / EMNLP / CCL 等来源目前通过 skill 里的 source policy 指导 Codex 使用官方页面/API 检索，后续可以继续补成独立脚本。
- 大批量任务默认先做候选筛选，不默认深读每一篇。
- 写入 Zotero 属于库写操作：除非用户明确要求“导入/写入 Zotero”，否则应先展示候选清单并等待确认。

## 安装方式

把仓库克隆到 Codex skills 目录：

```powershell
git clone https://github.com/jimzhou03/literature-harvest-zotero-obsidian-skill.git C:\Users\<you>\.codex\skills\literature-harvest-zotero-obsidian
```

如果你已经有同名目录，可以先备份或删除旧目录后再克隆。

安装后建议重启 Codex，或开一个新线程，确保新的 skill 被重新发现。

## 使用示例

### 1. 先生成检索计划

```powershell
python C:\Users\<you>\.codex\skills\literature-harvest-zotero-obsidian\scripts\build_literature_plan.py `
  --keywords "RAG, KG" `
  --venues "ACL,EMNLP,CCL" `
  --years "2023:2026" `
  --max-papers 20
```

输出会包含：

- 归一化后的关键词，例如 `retrieval augmented generation`、`knowledge graph`
- 会议名称归一化，例如把 `EINLP` 纠正为 `EMNLP`
- 推荐检索来源
- Zotero collection 建议
- Obsidian 输出路径建议

### 2. 跑 arXiv 抓取并下载开放 PDF

```powershell
python -B C:\Users\<you>\.codex\skills\literature-harvest-zotero-obsidian\scripts\harvest_arxiv.py `
  --keywords "retrieval augmented generation, knowledge graph" `
  --years "2023:2026" `
  --max-results 20 `
  --download `
  --out tmp\literature-harvest\rag-kg
```

输出目录中会生成：

- `manifest.json`：候选论文、来源 URL、PDF URL、下载状态、相关性分数。
- `references.bib`：可导入 Zotero 的 BibTeX。
- `pdfs/`：成功下载的开放 PDF。

### 3. 导入 Zotero

建议让 Codex 使用 Zotero skill 执行：

1. 先运行 Zotero 状态检查：`status --json`。
2. 按 DOI / title 搜索 Zotero，避免重复导入。
3. 导入 `references.bib`。
4. 只附加从开放来源下载成功的 PDF。
5. 在 Obsidian 笔记中记录 Zotero item key 和 BibTeX key。

### 4. 写入 Obsidian

默认写入结构：

```text
wiki/sources/论文阅读/<topic-slug>/
wiki/maps/<topic-slug> Literature Map.md
wiki/log.md
tmp/literature-harvest/<date>-<topic-slug>/manifest.json
```

如果只基于标题/摘要判断，要在笔记中标注：

```text
需要人工复核
```

## 推荐的 Codex 提示词

```text
使用 literature-harvest-zotero-obsidian skill，抓取 2024-2026 年 RAG 和 KG 相关的 arXiv/ACL/EMNLP 论文，最多 20 篇。先只给候选清单和下载状态，不要写入 Zotero。
```

```text
使用 literature-harvest-zotero-obsidian skill，把上一步确认的候选论文导入 Zotero，能下载 PDF 的附上 PDF，然后把前 5 篇深读结果写入 Obsidian。
```

## 本地验证状态

已验证：

- `build_literature_plan.py` 可以运行，并能把 `EINLP` 归一化为 `EMNLP`。
- `harvest_arxiv.py --help` 可以从全局 Codex skill 路径正常调用。
- 直接下载 arXiv PDF 的 smoke test 成功，文件头为 `%PDF-`。
- 启动 Zotero 后，本地 API 可达，测试环境中识别到 Zotero `9.0.5`、API v3。

已知限制：

- arXiv API 在频繁请求时可能超时或返回 HTTP 429。遇到这种情况应减小批量、增加 delay、稍后重试。
- 目前只有 arXiv 抓取器是脚本化 MVP；ACL / EMNLP / CCL 等来源还需要继续补充专用抓取脚本。

## 许可证

MIT
