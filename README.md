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
6. 对可访问 PDF 提取全文证据、章节线索、方法/实验/局限片段和关键图表算法引用。
7. 通过 Codex 对选中论文做结构化阅读，回答“解决什么问题、用了什么方法、实验证明什么、工具/数据/代码是什么、局限在哪里”。
8. 把单篇阅读笔记和主题级方法/工具/趋势/研究 gap 综述写入 Obsidian vault。

## 适用场景

当你对 Codex 说下面这些话时，这个 skill 应该被触发：

- “抓取 RAG 最近的 arXiv 论文”
- “爬取 KG / 知识图谱相关 ACL、EMNLP、CCL 论文”
- “下载神经网络相关论文 PDF 并导入 Zotero”
- “检索顶会顶刊文献，分析后写进 Obsidian”
- “从头到尾读这些论文，拆解方法、实验、工具和趋势”
- “给我做这个方向近三年的文献综述和研究 gap”
- “监控某个关键词的新论文，先给我候选清单”

它特别适合长期维护一个“Zotero 负责引用管理 + Obsidian 负责研究笔记”的文献工作流。

## 当前能力

- `SKILL.md`：Codex skill 入口，包含触发词、工作流、边界和输出纪律。
- `scripts/build_literature_plan.py`：根据关键词、会议、年份生成检索计划。
- `scripts/harvest_arxiv.py`：arXiv MVP 抓取器，可以查询 arXiv、过滤候选、下载开放 PDF、生成 BibTeX 和 manifest。
- `scripts/extract_pdf_evidence.py`：PDF 全文证据提取器，可生成 `pdf-evidence.json` 和 `full_text/`，供后续结构化阅读使用。
- `scripts/zotero_web_import.py`：Zotero Web API 全自动导入器，可自动创建 collection、导入 items、挂 PDF attachment、回填 manifest、Obsidian 笔记、topic map 和 `wiki/log.md`。
- `scripts/zotero_preflight.py`：Zotero 写入前的只读目标检查器，防止导入到错误 collection。
- `references/source-policy.md`：定义各类来源的优先级、会议处理策略和版权/访问边界。
- `references/deep-reading-workflow.md`：定义阅读深度、单篇拆解、主题综述、证据约束和人工判断边界。
- `references/obsidian-output.md`：定义 Obsidian 笔记、topic map 和日志格式。
- `references/zotero-web-api.md`：定义 Zotero Web API 全自动导入、credential 处理和 attachment 模式。
- `references/zotero-workflow.md`：定义 Zotero selected-target 预检、暂停导入和恢复流程。
- `agents/openai.yaml`：Codex UI 元数据。

## 当前边界

- 不绕过付费墙、登录墙、验证码、出版社限制或 robots 规则。
- 不从 ACM、IEEE、Springer、Elsevier 等页面批量强行下载 PDF。
- 不编造缺失的 DOI、BibTeX key、venue、PDF URL、数据集、代码链接或论文贡献。
- arXiv 已有可执行脚本；ACL / EMNLP / CCL 等来源目前通过 skill 里的 source policy 指导 Codex 使用官方页面/API 检索，后续可以继续补成独立脚本。
- 大批量任务默认先做候选筛选，不默认深读每一篇；但用户明确要求“精读 / 从头到尾 / 完整分析”时，会对可访问 PDF 做结构化阅读，并在数量过大时明确说明深度与批量的取舍。
- triage 只代表标题/摘要层面的初筛，不能当成最终读文献结论。
- 写入 Zotero 属于库写操作。全自动模式优先使用 Zotero Web API 和 `ZOTERO_API_KEY` 自动创建 collection / 导入 item；没有 API key 时才退回本地 Connector selected-target 预检。

## 安装方式

把仓库克隆到 Codex skills 目录：

```powershell
git clone https://github.com/jimzhou03/literature-harvest-zotero-obsidian-skill.git C:\Users\<you>\.codex\skills\literature-harvest-zotero-obsidian
```

如果你已经有同名目录，可以先备份或删除旧目录后再克隆。

安装后建议重启 Codex，或开一个新线程，确保新的 skill 被重新发现。

PDF 全文证据提取需要轻量依赖 `pypdf`：

```powershell
python -m pip install --user pypdf
```

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

路径策略：

- `manifest.json` 默认使用相对 PDF 路径，便于分享和审计。
- `references.bib` 默认使用本机绝对 PDF 路径，便于 Zotero 导入时附加 PDF。不要把 `tmp/literature-harvest/` 运行产物提交到公开仓库。

### 3. 导入 Zotero

#### 全自动模式：Zotero Web API

一次性准备：创建一个有写权限的 Zotero API key，并在 Codex 运行环境中设置：

获取 API key：

1. 登录 Zotero 官网。
2. 打开 [https://www.zotero.org/settings/keys](https://www.zotero.org/settings/keys)。
3. 点击 `Create new private key` 或类似按钮。
4. 权限建议：
   - 勾选个人库访问。
   - 勾选写入权限 / write access。
   - 如果只用个人库，不需要给 group 权限。
5. 创建后复制 key。

不要把 key 发到聊天里，也不要写进仓库、manifest、Obsidian 笔记或日志。

临时设置，只对当前 PowerShell 窗口有效：

```powershell
$env:ZOTERO_API_KEY = "你的key"
```

长期生效，写入当前 Windows 用户环境变量：

```powershell
[Environment]::SetEnvironmentVariable("ZOTERO_API_KEY", "你的key", "User")
```

设置长期变量后，重启 Codex 或新开 Codex 线程，让 Codex 进程能读到这个环境变量。

然后让 Codex 执行：

```powershell
python C:\Users\<you>\.codex\skills\literature-harvest-zotero-obsidian\scripts\zotero_web_import.py `
  --manifest tmp\literature-harvest\<run>\manifest.json `
  --collection "Literature Harvest\<date>\<topic>" `
  --note-root wiki\sources\论文阅读\<topic> `
  --map "wiki\maps\<topic> Literature Map.md" `
  --pdf-mode imported-url `
  --update
```

这个模式会自动创建 collection、导入文献 item、添加 PDF attachment，并回填 manifest、Obsidian 笔记、topic map 和 `wiki/log.md`。`--pdf-mode upload-file --fallback-url-attachment` 会尝试上传本地 PDF 到 Zotero File Storage，失败时回退为 PDF URL attachment。

#### Fallback：本地 Zotero Connector

建议让 Codex 使用 Zotero skill 执行：

1. 先运行 Zotero 状态检查：`status --json`。
2. 检查当前 Zotero 选中的目标 collection：

```powershell
python C:\Users\<you>\.codex\skills\literature-harvest-zotero-obsidian\scripts\zotero_preflight.py `
  --expected-name "rag-kg" `
  --json
```

3. 如果目标不匹配，停止导入，只保留 `references.bib`、PDF、manifest 和 Obsidian 笔记，并把状态标记为 `pending_target_confirmation`。
4. 目标正确后，按 DOI / title 搜索 Zotero，避免重复导入。
5. 导入 `references.bib`。
6. 只附加从开放来源下载成功的 PDF。
7. 在 Obsidian 笔记中记录 Zotero item key 和 BibTeX key。

说明：Zotero Connector 的 BibTeX/RIS 导入会写入“当前选中的”库或 collection。只有 Web API 模式能自动创建/选择目标 collection；Connector fallback 必须先做 selected-target 预检。

### 4. 提取 PDF 全文证据

导入或下载 PDF 后，先提取全文证据，而不是直接写一句话总结：

```powershell
python C:\Users\<you>\.codex\skills\literature-harvest-zotero-obsidian\scripts\extract_pdf_evidence.py `
  --manifest tmp\literature-harvest\<run>\manifest.json `
  --write-text `
  --update
```

输出包括：

- `pdf-evidence.json`：页数、字符数、章节线索、问题/方法/实验/局限片段、图/表/算法引用。
- `full_text/*.txt`：带页码标记的全文抽取结果。
- `manifest.json` 回填：`full_text_status`、`full_text_chars`、`full_text_path`、`pdf_evidence_path`。

这一步只是证据索引，不替你下最终判断。Codex 后续写笔记时必须回到这些证据或原文。

### 5. 写入 Obsidian

默认写入结构：

```text
wiki/sources/论文阅读/<topic-slug>/
wiki/maps/<topic-slug> Literature Map.md
wiki/log.md
tmp/literature-harvest/<date>-<topic-slug>/manifest.json
```

单篇笔记默认不再只写一两句话，而是包含：

- 研究问题和边界
- Motivation / Basic Idea
- Method 机制拆解
- Evaluation、dataset、metric、baseline、ablation
- Key Artifacts：关键图、表、公式、算法、定义
- Tools / Data / Code
- Strengths / Limitations / My Takeaways
- Reading Confidence 和需要人工复核的问题

主题地图必须包含方法分类、工具/数据/代码矩阵、趋势时间线、论文关系、研究 gap 和推荐阅读顺序。

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

```text
使用 literature-harvest-zotero-obsidian skill，抓取近三年 Text-to-SQL 热门论文，导入 Zotero 后对可访问 PDF 做 structured-read。Obsidian 里不要只写摘要，要拆解研究问题、方法、实验、工具/数据/代码、趋势和 gap。
```

## 本地验证状态

已验证：

- `build_literature_plan.py` 可以运行，并能把 `EINLP` 归一化为 `EMNLP`。
- `harvest_arxiv.py --help` 可以从全局 Codex skill 路径正常调用。
- `extract_pdf_evidence.py --help` 可以运行，用于对已下载 PDF 提取全文证据。
- `zotero_preflight.py --help` 可以运行，用于导入前检查 selected collection。
- `zotero_web_import.py --help` 可以运行；实际写入需要 `ZOTERO_API_KEY`。
- 直接下载 arXiv PDF 的 smoke test 成功，文件头为 `%PDF-`。
- 启动 Zotero 后，本地 API 可达，测试环境中识别到 Zotero `9.0.5`、API v3。

已知限制：

- arXiv API 在频繁请求时可能超时或返回 HTTP 429。遇到这种情况应减小批量、增加 delay、稍后重试。
- 目前只有 arXiv 抓取器是脚本化 MVP；ACL / EMNLP / CCL 等来源还需要继续补充专用抓取脚本。
- 无 `ZOTERO_API_KEY` 时，Zotero collection 仍需要用户在 Zotero UI 中先选中或创建；skill 负责检测和阻止错误导入。

## 许可证

MIT
