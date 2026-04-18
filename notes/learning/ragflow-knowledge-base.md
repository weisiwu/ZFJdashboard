# RAGFlow 知识库构建指南：深度文档理解的开源 RAG 引擎

> **主题**：知识库系统 / RAG / 深度文档理解 / 开源工具
> **日期**：2026 年 4 月 2 日
> **标签**：AI 应用 / 知识库 / RAGFlow / 文档解析

**开源 RAG 引擎，基于深度文档理解构建知识库，15+ 种切片方法适配不同文档类型，支持 OCR、布局识别、表格结构识别。RAGFlow 核心不是"选哪个开源系统"，而是"当你的文档包含大量表格、扫描件、复杂排版时，它能比别人解析得更准"。**

> **封面**：covers/RAGFlow知识库构建指南_cover.png

---

## RAGFlow 是什么

RAGFlow 是一款开源的检索增强生成（RAG）引擎，核心特点是基于**深度文档理解**（Deep Document Understanding）构建知识库 [[1]](https://github.com/infiniflow/ragflow)。

由 InfiniFlow 团队开发，GitHub Star 数超过 35k，定位是"重型知识库引擎"——与轻量化 RAG 工具不同，RAGFlow 在文档解析环节投入了大量工程资源，力求从复杂格式文档中提取高质量知识 [[2]](https://news.qq.com/rain/a/20240409A01DO500)。

### 核心特点

| 特点 | 说明 |
|------|------|
| **深度文档理解** | 自研 DeepDoc 模块，支持 OCR、布局识别、表格结构识别 |
| **模板化分块** | 15+ 种切片方法，针对不同文档类型优化 |
| **可视化干预** | 分块结果可视化，支持人工检查和调整 |
| **多模态支持** | PDF、DOCX、Excel、PPT、图片、扫描件、音频等 |
| **GraphRAG 集成** | 支持知识图谱提取，增强多跳问答能力 |

---

## 与其他 RAG 工具的定位差异

| 工具 | 定位 | 文档解析深度 | 适用场景 |
|------|------|--------------|----------|
| **RAGFlow** | 重型引擎 | 深度解析，支持复杂格式 | 企业文档、扫描件、表格密集型文档 |
| **MaxKB** | 开箱即用 | 标准解析，快速上手 | 内部知识库、客服问答 |
| **Dify** | 应用编排平台 | 依赖外部解析器 | 复杂工作流、多 Agent 协作 |
| **自研** | 完全可控 | 自定义 | 特殊需求、研究场景 |

RAGFlow 的核心价值在于：**当你的文档包含大量表格、扫描件、复杂排版时，它能比别人解析得更准** [[3]](https://www.h3blog.com/article/588/)。

---

## DeepDoc：深度文档理解模块

DeepDoc 是 RAGFlow 的核心竞争力，包含视觉（Vision）和解析器（Parser）两部分 [[4]](https://github.com/infiniflow/ragflow/blob/main/deepdoc/README.md)。

### 视觉能力

#### 1. OCR（光学字符识别）

对于图片或扫描版 PDF，OCR 是文本提取的基础。

```bash
# 测试 OCR 效果
python deepdoc/vision/t_ocr.py --inputs=path_to_pdfs --output_dir=./ocr_outputs
```

#### 2. 布局识别（Layout Recognition）

识别文档的结构组件，判断哪些文本是连续的、哪些是表格、哪些是图片。RAGFlow 定义了 10 种基本布局组件：

| 组件 | 说明 |
|------|------|
| Text | 正文文本 |
| Title | 标题 |
| Figure | 图片 |
| Figure caption | 图片说明 |
| Table | 表格 |
| Table caption | 表格说明 |
| Header | 页眉 |
| Footer | 页脚 |
| Reference | 参考文献 |
| Equation | 公式 |

```bash
# 测试布局识别
python deepdoc/vision/t_recognizer.py --inputs=path_to_pdfs --mode=layout --output_dir=./layouts_outputs
```

#### 3. 表格结构识别（TSR）

识别表格的层级表头、跨行跨列单元格，并将表格内容重组为 LLM 可理解的自然语言句子。

TSR 使用 5 种标签：

| 标签 | 说明 |
|------|------|
| Column | 列 |
| Row | 行 |
| Column header | 列头 |
| Projected row header | 投影行头 |
| Spanning cell | 跨单元格 |

```bash
# 测试表格结构识别
python deepdoc/vision/t_recognizer.py --inputs=path_to_pdfs --mode=tsr --output_dir=./tsr_outputs
```

#### 4. 表格自动旋转

扫描版 PDF 中的表格可能被旋转（90°、180°、270°），RAGFlow 会自动检测最佳旋转角度后再进行 OCR 和 TSR。

```bash
# 控制自动旋转
export TABLE_AUTO_ROTATE=true  # 启用（默认）
export TABLE_AUTO_ROTATE=false # 禁用
```

### 解析器

RAGFlow 为不同文档格式提供专用解析器：

| 格式 | 解析器 | 输出内容 |
|------|--------|----------|
| PDF | PdfParser | 文本块 + 表格（图片+自然语言）+ 图片（带说明） |
| DOCX | DocxParser | 结构化文本 + 内嵌图片 |
| Excel | ExcelParser | 表格数据 |
| PPT | PptParser | 幻灯片内容 |

PDF 解析器最复杂，因为 PDF 格式本身极其灵活（也是 RAGFlow 重点投入的方向）。

---

## 知识库构建完整流程

### 步骤 1：部署 RAGFlow

**系统要求** [[1]](https://github.com/infiniflow/ragflow)：

- CPU >= 4 核
- RAM >= 16 GB
- Disk >= 50 GB
- Docker >= 24.0.0
- Docker Compose >= v2.26.1

**快速启动**：

```bash
# 1. 确保 vm.max_map_count >= 262144
sysctl vm.max_map_count
# 如果不足，临时设置
sudo sysctl -w vm.max_map_count=262144

# 2. 克隆仓库
git clone https://github.com/infiniflow/ragflow.git
cd ragflow

# 3. 启动服务
cd docker
docker compose up -d
```

访问 `http://localhost:80`，默认账号 `ragflow@example.com`，密码 `infiniflow`。

### 步骤 2：配置模型

进入系统后，点击右上角头像 → Model providers：

1. 添加 LLM 提供商（如 OpenAI、Ollama、DeepSeek）
2. 添加 Embedding 模型
3. 设置默认模型（至少配置 chat 和 embedding）

### 步骤 3：创建知识库

点击顶部导航栏 "Knowledge Base" → "Create knowledge base"：

1. 输入知识库名称
2. 配置解析参数（见下节）
3. 上传文档

### 步骤 4：配置知识库参数

RAGFlow 提供丰富的知识库配置选项 [[5]](https://www.pondhouse-data.com/blog/introduction-to-ragflow)：

#### PDF 解析器选择

| 解析器 | 说明 | 适用场景 |
|--------|------|----------|
| **deepdoc** | RAGFlow 自研 OCR + TSR | 扫描件、复杂表格（推荐） |
| **gpt-4o / gpt-4.1** | 使用 GPT-4 视觉能力 | 高预算、高精度需求 |
| **MinerU** | 开源 PDF 解析器 | 替代方案 |
| **Docling** | IBM 开源解析器 | 替代方案 |

#### 切片方法选择

RAGFlow 提供 15+ 种切片方法，针对不同文档类型优化 [[6]](https://blog.csdn.net/qq_35354529/article/details/151190820)：

| 方法 | 适用文档 | 说明 |
|------|----------|------|
| **General** | 通用文档 | 智能分割，适合大多数场景 |
| **Naive** | 简单文本 | 固定长度分割 |
| **Q&A** | 问答对数据 | 每个问答对作为一个 chunk |
| **Resume** | 简历 | 结构化提取姓名、教育、工作经历等 |
| **Manual** | 技术手册 | 按章节分割，保持完整性 |
| **Table** | 表格数据 | 按行处理，适合 Excel/CSV |
| **Paper** | 学术论文 | 按章节和段落分割 |
| **Book** | 书籍 | 按章节分割 |
| **Laws** | 法律文件 | 保持条文结构 |
| **Presentation** | PPT | 按幻灯片分割 |
| **One** | 短文档 | 整个文档作为一个 chunk |
| **Tag** | 标签数据 | 支持跨知识库关联检索 |
| **KnowledgeGraph** | 知识图谱 | 提取实体和关系 |
| **Audio** | 音频 | 语音识别后处理 |

#### 高级配置

| 配置项 | 说明 | 建议 |
|--------|------|------|
| **Auto-Keyword** | 自动提取关键词数量 | 推荐 5-10，提升检索精度 |
| **Auto-Question** | 自动生成问题数量 | 类似 HyDe，提升语义匹配 |
| **RAPTOR** | 递归聚类摘要 | 长文档多跳问答，成本较高 |
| **Extract knowledge graph** | 知识图谱提取 | 复杂关系推理，成本高 |

### 步骤 5：上传与解析文档

上传文档后，RAGFlow 会异步处理：

```
处理流程：
├── 文档解析：DeepDoc 提取文本、表格、图片
├── 智能分块：按选定方法切分
├── 向量化：调用 Embedding 模型
├── 增强：自动关键词/问题提取（如启用）
└── 索引：存储到 Elasticsearch 或 Infinity
```

### 步骤 6：检查与干预分块结果

RAGFlow 提供可视化界面查看分块结果：

1. 进入知识库 → 点击文档
2. 查看每个 chunk 的内容
3. 可以手动调整分块边界
4. 删除无效 chunk

这是 RAGFlow 相比其他工具的独特优势——**允许人工干预解析结果**，而不是"黑盒"处理。

---

## 实操案例一：处理包含表格的扫描版财务报表

### 场景

假设你有一份扫描版 PDF 财务报表，包含多个跨页表格，希望通过 RAGFlow 实现精准问答。

### 步骤 1：创建知识库

名称：财务报表知识库

### 步骤 2：配置参数

| 配置项 | 选择 | 原因 |
|--------|------|------|
| PDF Parser | deepdoc | 扫描件首选 |
| Chunking method | Table | 表格密集型文档 |
| Auto-Keyword | 5 | 提取关键词辅助检索 |
| Auto-Question | 0 | 表格数据不需要 |

### 步骤 3：上传文档

上传扫描版 PDF，等待处理完成。

### 步骤 4：检查解析结果

进入文档详情页：

1. 检查表格是否正确识别
2. 检查跨页表格是否合并
3. 检查表格内容是否转为自然语言

**示例**：原始表格

| 项目 | 2023年 | 2024年 |
|------|--------|--------|
| 营业收入 | 100万 | 120万 |
| 净利润 | 10万 | 15万 |

解析后的自然语言：

```
表格：财务数据
项目：营业收入，2023年：100万，2024年：120万
项目：净利润，2023年：10万，2024年：15万
```

### 步骤 5：测试问答

创建 Chat Assistant，关联知识库：

**问题**：2024年营业收入是多少？

**回答**：根据财务报表，2024年营业收入为 120 万。

**来源**：财务报表.pdf - 第 3 页，表格"财务数据"

---

## 实操案例二：批量简历智能筛选

### 场景

HR 部门收到 500 份简历 PDF，需要快速筛选出"5 年以上 Java 经验、有分布式系统背景"的候选人。

### 步骤 1：创建知识库

名称：候选人简历库

### 步骤 2：配置参数

| 配置项 | 选择 | 原因 |
|--------|------|------|
| PDF Parser | deepdoc | 简历格式多样，需要 OCR |
| Chunking method | Resume | 专用解析器，结构化提取 |
| Auto-Keyword | 10 | 提取技能关键词 |
| Auto-Question | 0 | 简历不需要 |

### 步骤 3：批量上传

上传 500 份简历 PDF，等待处理。

### 步骤 4：验证解析效果

进入文档详情页，检查结构化提取结果：

```
简历：张三
├── 姓名：张三
├── 电话：138-xxxx-xxxx
├── 邮箱：zhangsan@example.com
├── 教育背景：
│   └── 清华大学 计算机科学 硕士 2015-2018
├── 工作经历：
│   ├── 阿里巴巴 高级工程师 2018-2023
│   │   └── 负责分布式交易系统开发
│   └── 字节跳动 技术专家 2023-至今
│       └── 负责云原生架构设计
├── 技能：Java, Spring, Kafka, Kubernetes
└── 工作年限：7 年
```

### 步骤 5：智能筛选

创建 Chat Assistant，提问：

**问题**：筛选出 5 年以上 Java 经验、有分布式系统背景的候选人。

**回答**：

根据简历库分析，符合条件的有：

1. **张三** - 7 年经验，阿里巴巴分布式交易系统，技能：Java, Kafka
2. **李四** - 6 年经验，美团订单系统，技能：Java, Spring Cloud
3. **王五** - 8 年经验，京东物流系统，技能：Java, Dubbo

**来源**：简历库 - 张三.pdf、李四.pdf、王五.pdf

### Resume 切片方法的独特价值

传统 RAG 工具对简历的处理方式：

- 固定长度切分 → 破坏字段边界
- 段落切分 → 无法结构化检索

RAGFlow 的 Resume 方法：

- **字段级提取**：姓名、教育、工作经历分别存储
- **结构化索引**：可以按"工作年限"、"技能"精确过滤
- **跨简历聚合**：支持"所有候选人的技能分布"等统计查询

---

## RAGFlow 的设计思路

### 为什么重视文档解析

RAG 的三大关键环节：**文档解析 → Embedding → LLM**。如果解析不准确，后续环节再强也会出错 [[7]](https://deepseek.csdn.net/6804a866da5d787fd5d06c4a)。

RAGFlow 选择在解析环节"扎深"，因为：

1. **PDF 是最常见但最复杂的格式**：布局自由、表格嵌套、图文混排
2. **扫描件普遍存在**：OCR 质量直接影响检索
3. **表格是高价值信息**：财务、法律、技术文档的核心

### 为什么选择模板化分块

不同文档有不同的"最佳切法"：

- 简历：按字段（姓名、教育、经历）提取
- 论文：按章节（摘要、方法、结论）分割
- 法律：按条文（第一条、第二条）保持完整
- 表格：按行分割，每行一个 chunk

"一刀切"的固定长度分割会破坏语义完整性，RAGFlow 通过模板化解决这一问题。

### 为什么提供可视化干预

自动解析不可能 100% 准确，RAGFlow 选择：

1. **透明化**：让用户看到解析结果
2. **可干预**：允许手动调整
3. **可追溯**：回答时引用具体 chunk

这符合"Quality in, quality out"的理念——高质量输入才能产出高质量输出。

---

## 高级功能

### GraphRAG 集成

RAGFlow 支持从文档中提取知识图谱，用于多跳问答 [[5]](https://www.pondhouse-data.com/blog/introduction-to-ragflow)：

```
启用方式：知识库配置 → Extract knowledge graph = true
```

适用场景：

- 文档包含复杂实体关系
- 需要多跳推理（如"A 的上级的下属是谁"）
- 法律、医疗等专业领域

注意：成本较高，不建议默认启用。

### RAPTOR

RAPTOR（Recursive Abstractive Processing for Tree Organized Retrieval）是一种递归聚类摘要技术 [[5]](https://www.pondhouse-data.com/blog/introduction-to-ragflow)：

- 对长文档进行层次化摘要
- 构建树形索引结构
- 支持跨段落问答

适用场景：长篇报告、书籍。

### Agent 与 MCP

RAGFlow 支持 Agent 功能和 MCP 协议 [[1]](https://github.com/infiniflow/ragflow)：

- 低代码 Agent 构建器
- Python/JavaScript 代码执行器
- MCP 工具调用

---

## 最佳实践建议

### 文档类型与切片方法匹配

| 文档类型 | 推荐切片方法 | 原因 |
|----------|--------------|------|
| 扫描版 PDF | Table / General | deepdoc 擅长处理 |
| 技术手册 | Manual | 保持章节完整 |
| 简历 | Resume | 结构化提取 |
| FAQ 文档 | Q&A | 问答对天然分块 |
| 学术论文 | Paper | 按章节分割 |
| 法律文件 | Laws | 保持条文完整 |
| Excel 表格 | Table | 按行处理 |

### 参数调优建议

| 参数 | 起始值 | 调优方向 |
|------|--------|----------|
| Auto-Keyword | 5 | 增加可提升召回，但成本上升 |
| Auto-Question | 0 | 语义模糊时启用 3-5 |
| RAPTOR | 关闭 | 长文档多跳问答时启用 |
| Knowledge Graph | 关闭 | 复杂关系推理时启用 |

### 解析器选择建议

| 场景 | 推荐解析器 |
|------|------------|
| 扫描件、复杂表格 | deepdoc |
| 高精度需求、预算充足 | gpt-4o |
| 常规 PDF | deepdoc 或 MinerU |

---

## 参考来源

| 编号 | 来源 | 说明 |
|------|------|------|
| 1 | [GitHub - infiniflow/ragflow](https://github.com/infiniflow/ragflow) | RAGFlow 官方仓库，包含功能介绍和快速开始 |
| 2 | [由近期 RAGFlow 的火爆看 RAG 的现状与未来](https://news.qq.com/rain/a/20240409A01DO500) | RAGFlow 定位分析，重型引擎 vs 轻量化工具 |
| 3 | [从零开始：掌握RAGFlow](https://www.h3blog.com/article/588/) | 实战经验分享，与 Dify 对比 |
| 4 | [DeepDoc README](https://github.com/infiniflow/ragflow/blob/main/deepdoc/README.md) | DeepDoc 模块详细说明，OCR/布局/TSR |
| 5 | [Introduction to RAGFlow](https://www.pondhouse-data.com/blog/introduction-to-ragflow) | 完整使用教程，知识库配置详解 |
| 6 | [RAGFlow切分方法详解](https://blog.csdn.net/qq_35354529/article/details/151190820) | 15 种切片方法说明 |
| 7 | [3分钟读懂RAGFlow](https://deepseek.csdn.net/6804a866da5d787fd5d06c4a) | RAG 三大关键环节分析 |
| 8 | [RAGFlow解析方法说明](https://devpress.csdn.net/v1/article/detail/146184908) | 各切片方法详细说明 |
