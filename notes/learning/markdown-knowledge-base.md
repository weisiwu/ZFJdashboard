# 个人 Markdown 知识库方案设计：从细致切分到检索调优

> **主题**：知识库方案设计 / 切分策略 / 检索评估 / MCP 集成
> **日期**：2026 年 4 月 1 日
> **标签**：AI 应用 / 知识库 / RAG / 工程化

**为让 AI 工具查本地笔记设计完整方案：从 AST 感知切分到 BM25+向量混合检索，再到检索质量评估闭环，最后封装成 MCP Server 让 Claude Code、Cursor 等工具按需调用。核心不是选哪个开源系统，而是搭建一个可观测、可调优的自研系统。**

> **封面**：covers/个人Markdown知识库方案设计_cover.png

---

## 你的核心需求

你想搭建一套个人 Markdown 知识库系统，有三个明确要求：

1. **AI 工具能查你的笔记**：不是做一个独立的知识库产品，而是让 Claude Code、Cursor 这类 AI 工具在回答时能调用你的本地知识
2. **切分逻辑细致化**：不满足于简单的固定长度切分，希望根据 Markdown 结构做语义感知的切分
3. **检索逻辑可调优**：能观察 AI 回答质量和检索打分之间的相关性，用来迭代优化

这套方案的核心不是"选哪个开源系统"，而是"如何搭建一个可观测、可调优的自研系统"。

---

## 方案架构总览

基于你的需求，推荐的技术路线是：

```text
┌─────────────────────────────────────────────────────────────┐
│                      AI 工具层                               │
│   Claude Code / Cursor / Windsurf / 其他 MCP 兼容工具        │
└─────────────────┬───────────────────────────────────────────┘
                  │ MCP Protocol
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                   MCP Server 层                              │
│  search_local_docs / get_chunk / web_search / answer        │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                   知识库核心层                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 文档解析器   │  │ 混合检索器   │  │ 答案生成器   │      │
│  │ (AST切分)    │  │ (BM25+向量)  │  │ (带引用)     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                   存储层                                     │
│  SQLite FTS5 (全文) + Qdrant/pgvector (向量) + 元数据表     │
└─────────────────────────────────────────────────────────────┘
```

这套架构的特点：

- **MCP Server 作为统一入口**：所有 AI 工具通过 MCP 协议调用，不侵入工具本身
- **切分器可插拔**：可以不断优化切分逻辑，不影响下游检索
- **检索质量可观测**：每次检索都有打分，每次回答都有引用，方便分析相关性

---

## 第一层：细致化的 Markdown 切分策略

### 为什么固定长度切分不够

固定长度切分（比如每 500 字一块）最大的问题是：**它会切断语义边界**。

一个 Markdown 文档通常有这样的结构：

```markdown
# 一级标题：某个主题

## 二级标题：概念解释
段落1...
段落2...

## 二级标题：实践方案
### 子标题：方案A
代码块...
列表...

### 子标题：方案B
表格...
引用...
```

如果按固定长度切，可能出现：

- 一个标题和它下面的内容被切到两块
- 代码块被拦腰切断
- 表格被拆散

检索时召回的片段不完整，模型看到的上下文支离破碎，回答质量自然下降 [[1]](https://www.pinecone.io/learn/chunking-strategies/)。

### 推荐的切分策略：AST 感知 + 语义聚合

#### 第一步：解析 Markdown AST

Markdown 本质是一种轻量级标记语言，它的语法结构可以用抽象语法树（AST）表示。Python 的 `markdown-it-py` 或 LlamaIndex 的 `MarkdownNodeParser` 都能把 Markdown 解析成树形结构 [[3]](https://github.com/tsensei/Semantic-Markdown-Parser)。

树形结构的核心节点类型：

- `heading`：标题（一级到六级）
- `paragraph`：段落
- `code_block`：代码块
- `list`：列表
- `table`：表格
- `blockquote`：引用

#### 第二步：按标题层级做初始切分

最自然的切分单位是"标题下的内容块"。一个实用的规则：

```python
def split_by_heading(markdown_ast, file_path):
    chunks = []
    current_chunk = {
        "heading_path": [],  # 标题路径，如 ["一级标题", "二级标题"]
        "content": [],
        "metadata": {}
    }
    
    for node in markdown_ast:
        if node.type == "heading":
            # 遇到新标题，保存当前 chunk，开启新 chunk
            if current_chunk["content"]:
                chunks.append(current_chunk)
            current_chunk = {
                "heading_path": update_heading_path(
                    current_chunk["heading_path"],
                    node.level,
                    node.text
                ),
                "content": [],
                "metadata": {"file": file_path, "line": node.line_number}
            }
        else:
            # 其他节点加入当前 chunk
            current_chunk["content"].append(node)
    
    if current_chunk["content"]:
        chunks.append(current_chunk)
    
    return chunks
```

这样切出来的每个 chunk，都是一个完整的"标题 + 内容"单元。

#### 第三步：对过长 chunk 做二次切分

有些章节内容很长，比如一个二级标题下有 3000 字。这时候需要做二次切分，但要遵循语义边界：

1. **优先按段落切**：段落是最自然的语义单元
2. **代码块不切断**：代码块整体作为一个子 chunk
3. **表格不切断**：表格行可以单独索引，但表头要保留
4. **列表可以按项切**：但每个列表项要完整

Pinecone 的文章提到一种"语义切分"方法：先按句子切，然后用 embedding 计算相邻句子的语义距离，在距离突然增大的地方切分 [[1]](https://www.pinecone.io/learn/chunking-strategies/)。这种方法可以用在长段落内部。

#### 第四步：对小 chunk 做聚合

反过来，有些章节内容很短，比如一个二级标题下只有两句话。这时候可以考虑把相邻的小 chunk 合并，避免碎片化。

Semantic Markdown Parser 项目提供了一个思路：**Token-Aware Splitting**，即根据 token 长度动态决定是切分还是合并 [[3]](https://github.com/tsensei/Semantic-Markdown-Parser)。

```python
def aggregate_small_chunks(chunks, min_tokens=100, max_tokens=500):
    aggregated = []
    buffer = []
    buffer_tokens = 0
    
    for chunk in chunks:
        chunk_tokens = count_tokens(chunk)
        
        if (buffer_tokens < min_tokens) and (buffer_tokens + chunk_tokens <= max_tokens):
            buffer.append(chunk)
            buffer_tokens += chunk_tokens
        else:
            if buffer:
                aggregated.append(merge_chunks(buffer))
            buffer = [chunk]
            buffer_tokens = chunk_tokens
    
    if buffer:
        aggregated.append(merge_chunks(buffer))
    
    return aggregated
```

### 每个 chunk 应该记录的元数据

为了后续检索和调优，每个 chunk 至少要记录：

| 字段 | 说明 | 用途 |
|------|------|------|
| `chunk_id` | 唯一标识 | 引用追溯 |
| `file_path` | 原文件路径 | 定位来源 |
| `heading_path` | 标题路径 | 理解上下文 |
| `content` | chunk 内容 | 检索和生成 |
| `token_count` | token 数量 | 控制上下文长度 |
| `char_count` | 字符数 | 统计分析 |
| `created_at` | 创建时间 | 时效性判断 |
| `updated_at` | 更新时间 | 增量更新 |
| `tags` | 标签 | 过滤和分类 |
| `parent_chunk_id` | 父 chunk ID | 层级回溯 |

还有一个很容易埋雷的点：**`chunk_id` 必须稳定生成**。如果每次重建索引都随机生成 `chunk_id`，后面的 chunk 级增量更新会退化成整篇删除再整篇重建，引用回溯也会断掉。

一个可落地的做法，是让 `chunk_id` 基于 `file_path + heading_path + local_index` 这类稳定字段生成：

```python
def build_chunk_id(file_path, heading_path, local_index):
    raw = f"{file_path}::{'/'.join(heading_path)}::{local_index}"
    return sha1(raw.encode('utf-8')).hexdigest()[:16]
```

---

## 第二层：混合检索 + Rerank

### 为什么需要混合检索

单一检索方式都有盲区：

- **BM25 / 全文检索**：擅长精确匹配，但对语义相似但用词不同的查询效果差
- **向量检索**：擅长语义匹配，但对专有名词、代码片段、路径名等效果不稳定

你的 Markdown 笔记里可能同时包含：

- 概念解释（适合向量检索）
- 代码片段（适合全文检索）
- 配置路径、命令行参数（适合全文检索）
- 同义表达（适合向量检索）

所以最稳的做法是 **双路召回 + 融合重排**。

### 混合检索的实现

```python
def hybrid_search(query, top_k=10):
    # 第一路：BM25 全文检索
    bm25_hits = bm25_search(query, top_k=top_k * 2)
    
    # 第二路：向量检索
    query_embedding = embed(query)
    vector_hits = vector_search(query_embedding, top_k=top_k * 2)
    
    # 用 RRF 融合排序，避免直接拼接不同量纲的分数
    candidates = reciprocal_rank_fusion(
        [bm25_hits, vector_hits],
        k=60,
        top_k=top_k * 3
    )
    
    # Rerank
    reranked = rerank(candidates, query, top_k=top_k)
    
    return reranked
```

Rerank 的作用是把两路召回的结果统一排序。常用的 reranker 包括：

- **Cohere Rerank API**：效果好，但需要联网
- **BGE Reranker**：开源，可本地部署
- **Cross-Encoder 模型**：用本地模型做精排

这里不要直接把 BM25 分数和向量相似度做线性加权。两者往往不在同一个量纲上，硬加权很容易把某一路召回压扁。更稳的办法，是先用 Reciprocal Rank Fusion（RRF）融合排序，再交给 reranker 做精排 [[15]](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion)。

RAGFlow 明确强调"multiple recall paired with fused re-ranking"，这是生产级 RAG 系统的标准做法 [[4]](https://github.com/infiniflow/ragflow)。

---

## 第三层：检索质量评估与调优

### 你的核心诉求：观察 AI 回答和检索打分的相关性

这是这套方案最关键的部分。你希望知道：

- 检索打分高的时候，AI 回答质量是否真的好？
- 检索打分低的时候，AI 是否还能答好？
- 什么时候应该触发联网补充？

要回答这些问题，需要建立一个 **评估闭环**。

### 先理解检索评估的核心指标

在搭建评估系统之前，需要理解几个关键指标。这些指标能帮你判断检索质量，而不只是凭感觉 [[5]](https://weaviate.io/blog/retrieval-evaluation-metrics)。

#### Precision@K：前 K 个结果里有几个是相关的

Precision@K 衡量的是：检索返回的前 K 个结果中，有多少比例是真正相关的。

公式：`Precision@K = 前K个结果中相关文档数 / K`

举个例子：你检索返回了 5 个 chunk，人工判断其中 3 个是真正相关的，那么 Precision@5 = 3/5 = 0.6。

这个指标的局限是：它只关心数量，不关心顺序。第一个结果和第五个结果，在 Precision 计算中权重一样。

#### Recall@K：所有相关文档里，我找到了几个

Recall@K 衡量的是：整个知识库里所有相关的文档，我检索到了多少比例。

公式：`Recall@K = 前K个结果中相关文档数 / 全库中相关文档总数`

这个指标更适合评估"覆盖率"。如果你的知识库里有 10 篇文档都和问题相关，但检索只返回了其中 2 篇，Recall@5 = 2/10 = 0.2。

对于个人知识库来说，Recall 不如 Precision 重要。因为你更关心"返回的结果是不是靠谱"，而不是"有没有把所有相关文档都找出来"。

#### MRR：第一个相关结果排在第几位

Mean Reciprocal Rank（MRR）关心的是：第一个相关结果排在第几位。

公式：`MRR = 1 / 第一个相关结果的排名位置`

如果第一个相关结果排在第 1 位，MRR = 1；排在第 2 位，MRR = 0.5；排在第 3 位，MRR = 0.33。

这个指标适合评估"用户能不能快速找到答案"。如果你的系统总是把最相关的结果排在前面，MRR 会很高。

#### MAP：综合考虑多个相关结果的位置

Mean Average Precision（MAP）比 MRR 更全面：它不只看第一个相关结果，而是看所有相关结果的位置。

计算逻辑：对于每个相关结果，计算它所在位置的 Precision，然后取平均。

MAP 是 MTEB（Massive Text Embedding Benchmark）Reranking 类别的默认评估指标 [[5]](https://weaviate.io/blog/retrieval-evaluation-metrics)。如果你想对比不同 reranker 的效果，MAP 是一个标准选择。

#### NDCG：考虑相关程度和位置衰减

Normalized Discounted Cumulative Gain（NDCG）是最精细的指标：

1. 它允许文档有不同程度的相关性（不只是相关/不相关）
2. 它考虑位置衰减：排在后面的结果，贡献度会降低

公式核心思想：`DCG = Σ (相关度 / log2(排名+1))`

NDCG 是 MTEB Retrieval 类别的默认指标 [[5]](https://weaviate.io/blog/retrieval-evaluation-metrics)。如果你的评估重点是"检索排序质量"，NDCG 是首选。

### 这些指标怎么用在你的系统里

对于你的场景，推荐这样用：

| 指标 | 用途 | 为什么适合你 |
|------|------|--------------|
| Precision@5 | 判断前 5 个结果是否靠谱 | 你关心的是"返回的结果能不能用"，不是"有没有覆盖全" |
| MRR | 判断第一个结果是否足够好 | 如果第一个结果就相关，AI 回答会更直接 |
| NDCG | 综合评估排序质量 | 可以用来对比不同 reranker 的效果 |

实际操作时，可以这样设计评估流程：

1. 准备一组测试问题（比如 20-50 个你真实问过的问题）
2. 对每个问题，人工标注哪些 chunk 是相关的
3. 用系统检索，计算 Precision@5、MRR、NDCG
4. 把这些指标和 AI 回答质量做相关性分析

### eRAG 方法：用下游任务评估检索质量

2024 年的一篇论文 eRAG 提出了一个思路：**用 LLM 的下游表现来标注检索质量** [[2]](https://arxiv.org/html/2404.13781v1)。

核心思想：

1. 对于每个检索到的文档 $d$，单独喂给 LLM，让它基于这个文档回答问题
2. 用评估函数（比如 ROUGE、BERTScore、或人工标注）给回答打分
3. 这个分数就是文档 $d$ 的相关性标签

这样可以得到每个文档的真实相关性，然后和检索器的打分做对比，计算相关性指标。

#### 一个具体例子

假设你的知识库里有这样一篇笔记：

```markdown
# MCP 协议详解

MCP（Model Context Protocol）是一个开放协议...

## 核心概念
- Tool：工具接口
- Resource：资源接口
- Prompt：提示词模板
```

用户问："MCP 协议有哪些核心概念？"

检索返回了 3 个 chunk：

| chunk_id | 内容片段 | rerank_score |
|----------|----------|--------------|
| chunk_1 | MCP 协议详解...核心概念...Tool/Resource/Prompt | 0.85 |
| chunk_2 | MCP 是 Model Context Protocol 的缩写 | 0.72 |
| chunk_3 | 如何配置 Claude Code 使用 MCP | 0.45 |

用 eRAG 方法评估：

1. 把 chunk_1 单独喂给 LLM，问同样的问题，LLM 能答出 Tool/Resource/Prompt → 质量高
2. 把 chunk_2 单独喂给 LLM，只能答出"MCP 是什么" → 质量中
3. 把 chunk_3 单独喂给 LLM，答不出核心概念 → 质量低

这样得到真实相关性标签：chunk_1=高，chunk_2=中，chunk_3=低。

然后对比 rerank_score：0.85/0.72/0.45，发现排序是对的，但 chunk_2 的分数可能偏高。

这个方法的价值在于：**它能显著减少人工标注量，用 LLM 的回答质量近似反推检索质量**。但它不是完全免人工方案：LLM 评估会把模型自身偏差带回评估流程，最好保留一小部分人工金标集做抽样校验。

### 实现评估闭环

#### 第一步：记录每次检索的详细信息

```python
def search_with_logging(query):
    results = hybrid_search(query)
    
    log_entry = {
        "query": query,
        "timestamp": datetime.now(),
        "results": [
            {
                "chunk_id": r.chunk_id,
                "bm25_score": r.bm25_score,
                "vector_score": r.vector_score,
                "rerank_score": r.rerank_score,
                "heading_path": r.heading_path,
                "file_path": r.file_path
            }
            for r in results
        ],
        "top_rerank_score": results[0].rerank_score if results else 0,
        "avg_rerank_score": sum(r.rerank_score for r in results) / len(results) if results else 0
    }
    
    save_to_log(log_entry)
    return results
```

#### 第二步：记录每次回答的质量

```python
def answer_with_evaluation(query, retrieved_chunks):
    # 生成回答
    answer = generate_answer(query, retrieved_chunks)
    
    # 记录回答信息
    answer_log = {
        "query": query,
        "answer": answer,
        "cited_chunks": extract_citations(answer),
        "answer_length": len(answer),
        "has_citations": bool(extract_citations(answer))
    }
    
    # 可选：自动评估回答质量
    # 比如：是否包含代码、是否有引用、是否直接回答问题
    
    save_answer_log(answer_log)
    return answer
```

#### 第三步：分析相关性

有了检索日志和回答日志，就可以分析：

```python
def analyze_correlation():
    # 加载日志
    retrieval_logs = load_retrieval_logs()
    answer_logs = load_answer_logs()
    
    # 合并数据
    data = merge_logs(retrieval_logs, answer_logs)
    
    if len(data) < 30:
        return {"error": "样本量过小，先累计更多查询日志"}
    
    # 排序分和回答质量往往是单调关系，不一定是线性关系
    rank_correlation = spearman_correlation(
        [d["top_rerank_score"] for d in data],
        [d["answer_quality"] for d in data]
    )
    linear_correlation = pearson_correlation(
        [d["top_rerank_score"] for d in data],
        [d["answer_quality"] for d in data]
    )
    
    return {
        "spearman_correlation": rank_correlation,
        "pearson_correlation": linear_correlation,
        "high_score_good_answer_rate": ...,
        "low_score_good_answer_rate": ...
    }
```

### 可视化分析

可以生成图表来直观观察：

- **散点图**：X 轴是检索打分，Y 轴是回答质量
- **箱线图**：高分档 vs 低分档的回答质量分布
- **时序图**：随着系统迭代，相关性是否在提升

这些图表可以帮助你判断：

- 检索打分是否真的是回答质量的有效预测指标
- 什么时候应该调整 rerank 阈值
- 什么时候应该优化切分逻辑

#### 一个真实的调优案例

假设你运行了 100 次检索，收集了这些数据：

| 检索打分区间 | 回答质量（人工评分 1-5） | 样本数 |
|--------------|--------------------------|--------|
| 0.8-1.0 | 4.2 | 15 |
| 0.6-0.8 | 3.5 | 35 |
| 0.4-0.6 | 2.8 | 30 |
| 0.0-0.4 | 2.1 | 20 |

从这个数据可以看出：

1. 检索打分和回答质量确实正相关
2. 但 0.6-0.8 区间的回答质量已经不错（3.5分），可以作为"足够好"的阈值
3. 低于 0.4 的检索，回答质量明显下降，应该触发联网补充

基于这个分析，你可以把置信度阈值设为 0.6：低于这个值就自动联网搜索。

---

## 第四层：MCP Server 封装

### 为什么用 MCP

MCP（Model Context Protocol）是一个开放协议，用来把 AI 工具和外部数据源、工具系统通过统一接口连接起来 [[13]](https://www.anthropic.com/news/model-context-protocol)。

用 MCP 的好处：

- **解耦**：知识库系统独立部署，AI 工具按需调用
- **通用**：Claude Code、Cursor、Windsurf 都支持 MCP
- **可扩展**：未来可以加更多工具，不影响现有架构

### MCP Server 的核心工具设计示意

下面的代码是**能力边界示意**，不是某个 Python SDK 的原样接口。真实项目里，工具注册方式、装饰器名称和启动入口要以你选用的 MCP SDK 为准。

```python
# mcp_server.py

from mcp import MCPServer

server = MCPServer("markdown-knowledge-base")

@server.tool("search_local_docs")
def search_local_docs(query: str, top_k: int = 5) -> list:
    """Search local Markdown knowledge base for relevant chunks."""
    results = hybrid_search(query, top_k=top_k)
    return [
        {
            "chunk_id": r.chunk_id,
            "content": r.content,
            "file_path": r.file_path,
            "heading_path": r.heading_path,
            "score": r.rerank_score
        }
        for r in results
    ]

@server.tool("get_chunk")
def get_chunk(chunk_id: str) -> dict:
    """Get a specific chunk by ID, with full context."""
    chunk = load_chunk(chunk_id)
    return {
        "chunk_id": chunk.id,
        "content": chunk.content,
        "file_path": chunk.file_path,
        "heading_path": chunk.heading_path,
        "metadata": chunk.metadata
    }

@server.tool("web_search")
def web_search(query: str, top_k: int = 3) -> list:
    """Search the web for additional information (fallback)."""
    results = tavily_search(query, top_k=top_k)
    return results

@server.tool("answer_with_citations")
def answer_with_citations(query: str, context: list) -> str:
    """Generate an answer with citations from provided context."""
    answer = generate_answer(query, context)
    return answer

server.run()
```

### AI 工具的调用方式

在 Claude Code 或 Cursor 的配置文件中添加：

```json
{
  "mcpServers": {
    "markdown-kb": {
      "command": "python",
      "args": ["/path/to/mcp_server.py"]
    }
  }
}
```

这样 AI 工具就能在回答时主动调用你的知识库。

---

## 第五层：增量索引与持续更新机制

### 问题：文档在不停更新，如何保持索引同步

你的知识库不是静态的。今天改了一篇笔记，明天新增一个章节，后天可能删除过时的内容。如果每次更新都要全量重建索引，成本高、延迟大，根本无法持续运行 [[8]](https://vectorize.io/blog/how-to-manage-and-refresh-data-in-your-vector-database)。

需要一套**增量更新机制**：只处理变化的文档，不影响已有的索引。

### 增量更新的核心思路

向量数据库的增量更新涉及三个操作 [[8]](https://vectorize.io/blog/how-to-manage-and-refresh-data-in-your-vector-database)：

| 操作 | 说明 | 触发条件 |
|------|------|----------|
| **Insert** | 插入新的向量 | 新文档、新章节 |
| **Update** | 更新已有向量 | 文档内容修改 |
| **Delete** | 删除向量 | 文档删除、章节删除 |

关键挑战：**如何高效检测文档变化**。

### 方案一：基于文件哈希的变更检测

最直接的方法是为每个文档计算哈希值，定期比对。

```python
import hashlib
import os

def compute_file_hash(file_path):
    """计算文件的 MD5 哈希值"""
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hasher.update(chunk)
    return hasher.hexdigest()

def detect_changes(knowledge_base_dir, stored_hashes):
    """检测文件变化"""
    current_hashes = {}
    current_files = set()
    changes = {"added": [], "modified": [], "deleted": []}
    
    # 遍历当前文件
    for root, _, files in os.walk(knowledge_base_dir):
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                current_files.add(file_path)
                current_hash = compute_file_hash(file_path)
                current_hashes[file_path] = current_hash
                
                if file_path not in stored_hashes:
                    # 新文件
                    changes["added"].append(file_path)
                elif stored_hashes[file_path] != current_hash:
                    # 修改的文件
                    changes["modified"].append(file_path)
    
    # 检测删除的文件
    for file_path in stored_hashes:
        if file_path not in current_files:
            changes["deleted"].append(file_path)
    
    return changes, current_hashes
```

**优点**：简单可靠，100% 检测到变化。

**缺点**：需要全量扫描文件系统，文件多时效率低。

### 方案二：基于文件系统监听（推荐）

使用操作系统的文件监听机制，实时捕获变化事件。

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class MarkdownHandler(FileSystemEventHandler):
    def __init__(self, index_queue):
        self.index_queue = index_queue
    
    def on_created(self, event):
        if event.src_path.endswith('.md'):
            self.index_queue.put({"action": "insert", "path": event.src_path})
    
    def on_modified(self, event):
        if event.src_path.endswith('.md'):
            self.index_queue.put({"action": "update", "path": event.src_path})
    
    def on_deleted(self, event):
        if event.src_path.endswith('.md'):
            self.index_queue.put({"action": "delete", "path": event.src_path})

def start_file_watcher(knowledge_base_dir, index_queue):
    observer = Observer()
    handler = MarkdownHandler(index_queue)
    observer.schedule(handler, knowledge_base_dir, recursive=True)
    observer.start()
    return observer
```

**优点**：实时响应，零扫描成本。

**缺点**：依赖操作系统，极端情况可能丢事件（需要定期全量校验兜底）。

### 增量索引的处理流程

```
文件变化事件 → 解析文档 → 切分 chunk → 计算变化 chunk
                                              ↓
                                   对比已有 chunk，确定增/删/改
                                              ↓
                                   更新 SQLite FTS5 + 向量数据库
                                              ↓
                                   更新元数据表（哈希、时间戳）
```

**关键细节**：chunk 级别的增量更新。

文档级别的增量更新不够细：如果只改了一个段落，不应该重新索引整个文档。

```python
def incremental_update_chunks(file_path, old_chunks, new_chunks):
    """chunk 级别的增量更新"""
    old_chunk_ids = {c['chunk_id']: c for c in old_chunks}
    new_chunk_ids = {c['chunk_id']: c for c in new_chunks}
    
    to_delete = set(old_chunk_ids.keys()) - set(new_chunk_ids.keys())
    to_insert = set(new_chunk_ids.keys()) - set(old_chunk_ids.keys())
    to_update = set()
    
    for chunk_id in set(old_chunk_ids.keys()) & set(new_chunk_ids.keys()):
        if old_chunk_ids[chunk_id]['content'] != new_chunk_ids[chunk_id]['content']:
            to_update.add(chunk_id)
    
    return {
        "delete": list(to_delete),
        "insert": [new_chunk_ids[cid] for cid in to_insert],
        "update": [new_chunk_ids[cid] for cid in to_update]
    }
```

### 定时任务 + 事件监听的混合方案

生产级系统通常采用**双重保障**：

1. **实时监听**：watchdog 监听文件变化，立即触发增量更新
2. **定时校验**：每天凌晨全量扫描哈希，补齐漏掉的变化

```python
import schedule
import time

def daily_full_check():
    """每日全量校验"""
    global stored_hashes
    changes, new_hashes = detect_changes(KB_DIR, stored_hashes)
    process_changes(changes)
    stored_hashes = new_hashes

# 实时监听
observer = start_file_watcher(KB_DIR, index_queue)

# 定时校验
schedule.every().day.at("02:00").do(daily_full_check)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### 更新策略的选择

| 策略 | 适用场景 | 延迟 | 成本 |
|------|----------|------|------|
| **批量更新** | 文档更新不频繁，可接受延迟 | 分钟级 | 低 |
| **增量更新** | 文档更新频繁，需要近实时 | 秒级 | 中 |
| **实时更新** | 文档持续变化，需要即时响应 | 毫秒级 | 高 |

个人知识库推荐**增量更新 + 定时校验**，平衡效果和成本 [[8]](https://vectorize.io/blog/how-to-manage-and-refresh-data-in-your-vector-database)。

---

## 第六层：多人协作与版本管理

### 问题：AI 协作场景下的全篇冲突

你提出的问题击中了要害：**传统 Git 冲突解决假设的是"局部修改"，但 AI 协作场景往往是"全文重写"**。

真实场景是这样的：

1. A 用 AI 优化文档，AI 重写了 80% 的内容
2. B 也用 AI 优化同一篇文档，AI 也重写了 80% 的内容
3. 两人同时提交，Git 检测到全篇冲突
4. 传统"逐行合并"策略完全失效——整篇文档都是冲突标记

更深层的问题是：**Git 的冲突解决机制本身就是错的思路**。它在"解决冲突"，而我们需要的是"让冲突不可能发生"。

### 为什么 Git 思路从根本上就错了

Git 的设计假设：

| 假设 | 现实 |
|------|------|
| 人手工编辑，改动局部 | AI 重写，改动全局 |
| 改动可以逐行对比 | 结构重组后无法逐行对比 |
| 冲突是例外 | 冲突是常态 |
| 需要版本回溯 | 需要实时一致 |

**Git 是"事后补救"**：先让冲突发生，再想办法解决。

**我们需要"事前预防"**：让冲突根本不可能发生。

这不是 Git 的错——Git 是为代码版本控制设计的，不是为实时协作设计的。Google Docs、Notion、飞书文档这些工具，从来不会提示你"有冲突需要手动解决"，因为它们用了完全不同的技术。

### 方案评估：哪种方案最适合 AI 协作

| 方案 | 核心思路 | 冲突是否存在 | 实现难度 | AI 协作适配度 | 评分 |
|------|----------|--------------|----------|---------------|------|
| **AI 协作专用协议** | AI 提交提案，协调器合并 | 否 | 中 | 高 | 9分 |
| **语义级操作** | 语义操作可合并 | 否 | 高 | 高 | 9分 |
| **CRDT** | 数学上无冲突的数据结构 | 否 | 中 | 中 | 8分 |
| **OT** | 操作转换 | 否 | 高 | 低 | 7分 |
| 实时协作平台 | 用协作工具替代 Git | 否 | 低 | 低 | 6分 |

**保留三种方案**：AI 协作专用协议（用户指定）、语义级操作（9分）、CRDT（8分）。

---

### 方案一：AI 协作专用协议（推荐）

如果 AI 是主要协作者，可以设计一套 **AI 协作专用协议**。这是最直接解决 AI 协作冲突的方案。

#### 协议设计

```
1. AI 不直接修改文档，而是提交"修改提案"
2. 提案包含：修改意图、影响范围、优先级
3. 协调器收集所有提案，按规则合并
4. 合并后的结果写入文档
5. 索引自动更新
```

#### 提案格式

```json
{
  "proposal_id": "p_20260402_001",
  "author": "AI_Agent_1",
  "timestamp": "2026-04-02T12:00:00Z",
  "base_version": 42,
  "target_sections": ["auth"],
  "intent": "优化 API 文档的可读性",
  "priority": 5,
  "operations": [
    {
      "type": "rewrite_section",
      "section_id": "auth",
      "reason": "增加参数类型说明"
    }
  ],
  "conflict_strategy": "merge_if_possible",
  "fallback": "keep_original"
 }
```

#### 提案字段为什么要设计成这样

这个 JSON 不是为了让输出更漂亮，而是为了让协调器真的能稳定运行。

| 字段 | 作用 | 如果缺失会怎样 |
|------|------|----------------|
| `proposal_id` | 唯一标识一次提案 | 无法去重，也无法审计 |
| `base_version` | 提案生成时依赖的文档版本 | 协调器无法判断提案是否已经过期 |
| `target_sections` | 声明提案影响范围 | 冲突检测只能退化成全文扫描 |
| `priority` | 冲突裁决时的优先级 | 轻重缓急无法自动判断 |
| `operations` | 语义级操作载荷 | 协议只剩意图，无法执行 |
| `conflict_strategy` | 冲突时的默认策略 | 协调器没有默认分支 |
| `fallback` | 自动处理失败时的兜底动作 | 失败后只能报错，不能恢复 |

如果这里只有 `intent` 和一整段改写后的文本，这套协议最后还是会退回到"拿两份大文本硬比较"，只是把 Git 冲突搬到了服务层。

#### 协调器逻辑

```python
class ProposalCoordinator:
    def __init__(self):
        self.proposals = []
        self.document_version = 0
    
    def submit_proposal(self, proposal):
        """提交提案"""
        if proposal["base_version"] != self.document_version:
            return {
                "status": "rebase_required",
                "current_version": self.document_version
            }
        
        # 检查与已有提案的冲突
        conflicts = self.detect_conflicts(proposal)
        
        if conflicts:
            decision = self.resolve_conflicts(proposal, conflicts)
            if decision["status"] == "pending":
                return decision
            proposal_to_apply = decision["proposal"]
            status = decision["status"]
        else:
            proposal_to_apply = proposal
            status = "applied"
        
        self.apply_proposal(proposal_to_apply)
        self.proposals.append(proposal_to_apply)
        self.document_version += 1
        return {"status": status, "document_version": self.document_version}
    
    def detect_conflicts(self, new_proposal):
        """检测提案冲突"""
        conflicts = []
        new_targets = set(new_proposal["target_sections"])
        for existing in self.proposals:
            if new_targets & set(existing["target_sections"]):
                conflicts.append(existing)
        return conflicts
    
    def resolve_conflicts(self, new_proposal, conflicts):
        """解决提案冲突"""
        # 策略 1：优先级高的优先
        if new_proposal["priority"] > max(c["priority"] for c in conflicts):
            return {"status": "applied", "proposal": new_proposal, "reason": "higher_priority"}
        
        # 策略 2：可以合并则合并
        if self.can_merge(new_proposal, conflicts):
            merged = self.merge_proposals(new_proposal, conflicts)
            return {"status": "merged", "proposal": merged}
        
        # 策略 3：需要人工决策
        return {
            "status": "pending",
            "conflicts": conflicts,
            "options": [
                "apply_new",
                "keep_existing",
                "merge_manually"
            ]
        }
```

#### AI 提交提案而非直接修改

```python
def ai_optimize_with_proposals(document, instruction):
    """AI 优化文档，提交提案而非直接修改"""
    
    # 分析文档，生成提案
    analysis = analyze_document(document)
    
    proposal = {
        "proposal_id": generate_proposal_id(),
        "author": "AI_Agent",
        "timestamp": datetime.now().isoformat(),
        "base_version": current_document_version(),
        "target_sections": infer_target_sections(analysis, instruction),
        "intent": instruction,
        "operations": generate_operations(analysis, instruction),
        "priority": calculate_priority(instruction),
        "conflict_strategy": "merge_if_possible"
    }
    
    proposal = validate_proposal(proposal)
    
    # 提交到协调器
    result = coordinator.submit_proposal(proposal)
    
    if result["status"] == "applied":
        return "提案已应用"
    elif result["status"] == "merged":
        return "提案已合并"
    else:
        return f"提案待决策，冲突：{result['conflicts']}"
```

#### 为什么这里必须上状态机

只要系统里同时出现下面这些情况，单纯的 `if/else` 就开始不够用了：

- **提案重复提交**
- **提案基于旧版本文档生成**
- **需要等待人工审核**
- **文档已经写入，但索引更新失败**
- **外部服务超时后自动重试**

Durable Workflow 系统一般都会把执行名或幂等键作为去重依据，让一次执行可以安全重试，而不会重复制造副作用 [[17]](https://docs.aws.amazon.com/lambda/latest/dg/durable-execution-idempotency.html)。人工审批类工作流也通常不是"报个错等人来处理"，而是**流程正式暂停，等待人工 approve / reject 后继续推进** [[18]](https://docs.aws.amazon.com/step-functions/latest/dg/tutorial-human-approval.html)。

放到 AI 协作文档场景里，最合理的建模方式就是：

- **提案状态机**：管理单个提案的生命周期
- **协调器状态机**：管理协调器当前在执行哪一步

#### 提案状态机

提案本身建议至少有这些状态：

| 状态 | 含义 | 进入条件 | 退出条件 |
|------|------|----------|----------|
| `draft` | AI 刚生成草案 | LLM 输出原始 JSON | 通过结构校验 |
| `validated` | 字段合法、操作合法 | `validate_proposal()` 通过 | 入队 |
| `queued` | 已进入协调器队列 | 等待处理 | 被协调器取出 |
| `rebase_required` | 基线版本已过期 | `base_version` 落后 | 基于新版本重生成 |
| `conflict_detected` | 影响范围重叠 | 命中其他提案的 `target_sections` | 进入自动合并或人工审核 |
| `mergeable` | 可自动合并 | 合并规则能给出确定结果 | 生成 merged proposal |
| `pending_review` | 需要人工介入 | 无法自动裁决 | 人工 approve / reject / edit |
| `approved` | 已获批准 | 自动批准或人工批准 | 应用到文档 |
| `applied` | 已写入正文 | 文档存储成功 | 触发索引 |
| `indexed` | 索引已完成 | 全文索引与向量索引同步完成 | 生命周期结束 |
| `rejected` | 被拒绝 | 人工拒绝或策略拒绝 | 生命周期结束 |
| `expired` | 审核超时 | 超过 `review_deadline` | 生命周期结束 |
| `failed` | 执行失败 | 写入、索引或补偿失败 | 重试或人工接管 |

可以把它概括成这条主路径：

```text
draft
  ↓
validated
  ↓
queued
  ↓
conflict_detected ─────────────┐
  ↓                           │
mergeable → approved          │
  ↓                           │
applied                       │
  ↓                           │
indexed                       │
                              │
rebase_required               │
pending_review ─→ approved ───┘
      │
      ├──→ rejected
      ├──→ expired
      └──→ failed
```

#### 协调器状态机

协调器自身也应该被当成状态机，而不是一个黑盒函数。

| 状态 | 协调器在做什么 | 关键输出 |
|------|---------------|----------|
| `idle` | 等待新提案 | 无 |
| `deduplicating` | 按 `proposal_id` / `idempotency_key` 去重 | 返回旧结果或继续 |
| `validating` | 校验 schema 和操作合法性 | `validated` / `failed` |
| `checking_base_version` | 校验提案是否基于当前版本 | `rebase_required` / 继续 |
| `detecting_conflicts` | 根据 `target_sections` 和语义操作判断重叠 | `mergeable` / `pending_review` |
| `merging` | 生成合并后的提案 | `merged proposal` |
| `waiting_review` | 暂停并等待人工反馈 | `approved` / `rejected` / `expired` |
| `applying` | 应用提案到正文 | 新文档版本 |
| `persisting` | 写事件日志、快照、审计记录 | 可恢复状态 |
| `indexing` | 触发索引流水线 | 新索引版本 |
| `retrying` | 对临时失败做有限重试 | 成功或失败 |
| `completed` | 一轮执行结束 | 对外响应 |

#### 完整处理流程图

```text
新提案到达
   ↓
幂等检查（proposal_id / idempotency_key）
   ├── 命中重复请求 → 直接返回旧结果
   └── 新请求
        ↓
字段校验、操作校验
   ├── 不合法 → failed
   └── 合法
        ↓
base_version 校验
   ├── 落后 → rebase_required → 返回 AI 重生成
   └── 一致
        ↓
冲突检测
   ├── 无冲突 → approved
   ├── 可自动合并 → mergeable → merged → approved
   └── 不可自动合并 → pending_review
                             ↓
                    人工 approve / reject / edit
                             ↓
                          applying
                             ↓
                          persisting
                             ↓
                           indexing
                             ↓
                 completed / retrying / failed
```

#### 端到端泳道图

如果把 AI、协调器、人工审核、文档存储和索引系统放在同一张图里，整个链路会更清楚：

```text
AI Agent
  ↓ 生成 proposal
Proposal API
  ↓ validate_proposal
Coordinator Queue
  ↓
Proposal Coordinator
  ├── 去重
  ├── base_version 检查
  ├── target_sections 冲突检测
  ├── merge rules / semantic merge
  └── review routing
         ↓
Manual Review Queue
  ├── approve
  ├── reject
  └── edit_then_approve
         ↓
Document Store
  ├── 写正文新版本
  ├── 写 snapshot
  └── 写 proposal_event_log
         ↓
Index Pipeline
  ├── 更新 chunk
  ├── 更新全文索引
  └── 更新向量索引
         ↓
Audit / Metrics
  ├── auto_merge_rate
  ├── manual_review_rate
  ├── index_lag
  └── proposal_latency
```

#### 事件日志必须单独存

如果没有 `proposal_event_log`，这套状态机几乎没法恢复，也没法审计。建议至少记录这些字段：

| 字段 | 说明 |
|------|------|
| `event_id` | 事件唯一 ID |
| `proposal_id` | 对应提案 |
| `from_state` | 迁移前状态 |
| `to_state` | 迁移后状态 |
| `event_type` | 如 `validated`、`merged`、`review_approved` |
| `operator` | AI、协调器或人工审核人 |
| `document_version` | 发生迁移时的文档版本 |
| `created_at` | 事件时间 |
| `payload` | 附加上下文 |

这张表的价值不只是排查问题，还包括：

- **恢复能力**：协调器崩掉后可以从最后一个稳定状态继续跑
- **审计能力**：可以回答"这段内容是谁在什么时候通过什么策略改进去的"
- **调优能力**：能统计自动合并率、人工介入率和超时率

#### 幂等、重试和补偿

这套协议只要做成服务，就必须假设这些事会发生：

- AI 接口超时后重发同一个提案
- 队列重复投递消息
- 文档已写成功，但索引更新失败
- 人工审核链接被点两次

所以要明确三条规则：

1. **提案提交必须幂等**：用 `proposal_id` 或单独的 `idempotency_key` 把重复请求折叠为同一次执行 [[17]](https://docs.aws.amazon.com/lambda/latest/dg/durable-execution-idempotency.html)
2. **文档写入和事件日志要么一起成功，要么一起失败**：不能正文更新了，但状态还停留在旧值
3. **索引更新允许异步，但必须有补偿**：如果索引失败，提案状态不能直接标成完成，而应进入 `retrying` 或 `failed`

一个更稳的处理函数大概会长这样：

```python
def process_proposal(proposal):
    existing = load_by_idempotency_key(proposal["proposal_id"])
    if existing:
        return existing
    
    with transaction():
        save_event(proposal, from_state=None, to_state="validated")
        decision = coordinator.submit_proposal(proposal)
        save_event(proposal, from_state="validated", to_state=decision["status"])
    
    if decision["status"] in ["applied", "merged"]:
        enqueue_index_job(proposal["proposal_id"])
    
    return decision
```

#### 人工审核节点怎么设计

人工审核不是一个模糊的"后续有人看看"，而是状态机里的正式节点。它至少要支持三种动作：

- **approve**：接受当前提案或合并结果，直接应用
- **reject**：拒绝提案，结束生命周期
- **edit_then_approve**：人工先调整操作，再批准写入

等待人工时，流程应该明确停在 `pending_review`，而不是不停轮询。AWS Step Functions 的人工审批示例本质上就是：**流程暂停在等待节点，收到人工批准或拒绝回调后再继续推进** [[18]](https://docs.aws.amazon.com/step-functions/latest/dg/tutorial-human-approval.html)。

对 AI 协作文档来说，这一点很关键。因为真正难合并的不是字符，而是含义。一旦进入人工审核，系统就要接受"暂停"是正常状态，而不是异常状态。

#### 超时和回收策略

如果提案长时间停在 `pending_review`，系统会逐渐堆积一批过时提案。建议补三条回收规则：

| 场景 | 建议策略 |
|------|----------|
| 审核 24 小时无人处理 | 自动转 `expired` |
| 审核超时但优先级高 | 自动提醒负责人，并再延长一次 |
| 提案基于旧版本且长期未处理 | 转 `rebase_required` |
| 同一作者连续提交相似提案 | 合并成一个 review batch |

#### 一个更完整的真实案例

假设当前文档版本是 `v42`，其中 `auth` 和 `retry` 是两个独立章节。

- **提案 A**：AI_Agent_1 基于 `v42`，重写 `auth`，优先级 5
- **提案 B**：AI_Agent_2 基于 `v42`，给 `auth` 增加示例，优先级 3
- **提案 C**：AI_Agent_3 基于 `v41`，修改 `retry`，优先级 4

处理过程：

```text
A 到达 → validated → queued → 无冲突 → approved → applied → indexed
B 到达 → validated → queued → conflict_detected(A 命中同一 section)
      → mergeable（rewrite + add_content 可自动合并）
      → merged → approved → applied → indexed
C 到达 → validated → base_version 校验失败
      → rebase_required → 返回 AI 基于 v44 重新生成
```

这三个提案里，没有一个会落成"冲突文件"。系统处理的是**状态迁移**：

- A 走自动应用
- B 走自动合并
- C 走重新基线化

这就是这套协议和 Git 模式最根本的差别：**把冲突从文本层，提前改造成协议层、状态层和调度层的问题。**

#### 最容易被忽略的三个点

| 容易忽略的点 | 后果 | 修法 |
|--------------|------|------|
| 只存当前状态，不存状态迁移事件 | 无法恢复，也无法审计 | 加 `proposal_event_log` |
| 只写正文，不做索引补偿 | 文档版本和索引版本漂移 | 单独维护 `index_job` 和失败重试 |
| 把 `pending_review` 当异常 | 系统会不停重试、制造噪音 | 把人工等待视为正式状态 |

#### 与 AI 协作协议的关系

语义级操作是 AI 协作协议的**基础**。协议中的"提案"包含的就是"语义操作"。

```
AI 协作协议 = 协调器 + 语义级操作
```

---

### 方案二：语义级操作

CRDT 这类底层同步机制解决了"字符级"冲突，但 AI 协作的问题是"语义级"冲突。

#### 语义级操作的思路

**将 AI 的重写拆解为语义操作，而不是字符操作**。

```
传统视角：AI 重写了 1000 个字符
语义视角：AI 执行了以下操作：
  - 重命名章节标题："API 文档" → "API 接口文档 v2.0"
  - 重构章节结构：合并"登录"和"注册"为"认证模块"
  - 补充参数说明：为每个参数添加类型和约束
  - 增加示例：为每个接口添加 curl 示例
```

#### 操作的定义

定义一套**语义操作原语**：

| 操作 | 说明 | 示例 |
|------|------|------|
| `rename_section` | 重命名章节 | 标题从 A 改为 B |
| `merge_sections` | 合并章节 | 合并 1.1 和 1.2 |
| `split_section` | 拆分章节 | 拆分 1 为 1.1 和 1.2 |
| `add_content` | 增加内容 | 在章节末尾增加段落 |
| `remove_content` | 删除内容 | 删除某个段落 |
| `rewrite_content` | 重写内容 | 重写某个段落 |
| `reorder_sections` | 重排章节 | 调整章节顺序 |

#### 操作的合并规则

语义操作可以定义合并规则：

```python
def merge_operations(op_a, op_b):
    """合并两个语义操作"""
    
    # 规则 1：同一章节的重命名，选择更具体的
    if op_a.type == 'rename_section' and op_b.type == 'rename_section':
        if op_a.section_id == op_b.section_id:
            # 选择更长的标题（通常更具体）
            return op_a if len(op_a.new_title) > len(op_b.new_title) else op_b
    
    # 规则 2：同一章节的 add_content，合并内容
    if op_a.type == 'add_content' and op_b.type == 'add_content':
        if op_a.section_id == op_b.section_id:
            return Operation(
                type='add_content',
                section_id=op_a.section_id,
                content=op_a.content + '\n' + op_b.content
            )
    
    # 规则 3：rewrite_content 与 add_content，保留两者
    if {op_a.type, op_b.type} == {'rewrite_content', 'add_content'}:
        if op_a.section_id == op_b.section_id:
            rewrite_op = op_a if op_a.type == 'rewrite_content' else op_b
            add_op = op_b if op_b.type == 'add_content' else op_a
            return [
                rewrite_op,
                add_op
            ]
    
    # 默认：标记为需要人工审核，而不是静默保留
    return {
        "status": "needs_review",
        "operations": [op_a, op_b]
    }
```

#### AI 输出操作而非文本

让 AI 输出操作序列，而不是直接输出重写后的文本：

```python
def ai_optimize_with_operations(document, instruction):
    """AI 优化文档，输出操作序列"""
    
    prompt = f"""
你是一个文档优化助手。请分析文档并输出优化操作，而不是直接输出优化后的文本。

当前文档：
{document}

优化目标：
{instruction}

请输出 JSON 格式的操作列表：
[
  {{"type": "rename_section", "section_id": "s1", "new_title": "..."}},
  {{"type": "add_content", "section_id": "s2", "content": "..."}},
  {{"type": "rewrite_content", "section_id": "s3", "content": "..."}}
]
"""
    
    raw_operations = call_llm(prompt)
    operations = validate_operations(json.loads(raw_operations))
    return operations
```

**优点**：操作可以合并，文本无法合并。

#### 与 AI 协作协议的关系

语义级操作是 AI 协作协议的**基础**。协议中的"提案"包含的就是"语义操作"。

```
AI 协作协议 = 协调器 + 语义级操作
```

---

### 方案三：CRDT —— 让冲突在数学上不可能发生

**CRDT（Conflict-free Replicated Data Types，无冲突复制数据类型）** 是一种数学上保证无冲突的数据结构 [[11]](https://crdt.tech/)。

#### 核心原理

CRDT 的核心思想：**设计一种数据结构，使得任意两个状态都可以无冲突地合并**。

```
用户 A 的操作：在位置 5 插入"Hello"
用户 B 的操作：在位置 10 插入"World"

传统思路：位置冲突，需要解决
CRDT 思路：每个字符有唯一 ID，插入操作是独立的，自动合并
```

#### 为什么 CRDT 能做到无冲突

CRDT 通过以下机制保证无冲突：

1. **每个操作有唯一 ID**：不是"在位置 5 插入"，而是"在 ID 为 X 的字符后插入 ID 为 Y 的字符"
2. **操作可交换**：先应用 A 再应用 B，和先应用 B 再应用 A，结果相同
3. **操作可结合**：多次合并的顺序不影响最终结果
4. **最终一致**：所有副本最终会收敛到相同状态 [[12]](https://wang1xiang.github.io/blog/docs/tiptap/tiptap-tutorial5.html)

#### CRDT 的两种类型

| 类型 | 说明 | 适用场景 |
|------|------|----------|
| **Op-based CRDT** | 传播操作，只同步变更 | 网络稳定，带宽敏感 |
| **State-based CRDT** | 传播全量状态，合并状态 | 离线场景，网络不稳定 |

#### 实际应用：Yjs 框架

[Yjs](https://docs.yjs.dev/) 是最成熟的 CRDT 实现，用于构建协作文档应用 [[12]](https://wang1xiang.github.io/blog/docs/tiptap/tiptap-tutorial5.html)。

```javascript
import * as Y from 'yjs';

// 创建文档
const doc = new Y.Doc();

// 创建文本类型
const text = doc.getText('content');

// 用户 A 插入内容
text.insert(0, 'Hello World');

// 用户 B 在另一个副本插入
// 即使同时操作，合并后也是一致的

// 同步机制
const state1 = Y.encodeStateAsUpdate(doc);
// 发送 state1 到其他副本
// 接收其他副本的 state2
Y.applyUpdate(doc, state2);
```

**关键点**：无论操作顺序如何，所有副本最终状态一致，不需要冲突解决。

#### CRDT 的局限

CRDT 不是万能的：

| 局限 | 说明 |
|------|------|
| **数据结构受限** | 只能用于特定类型（文本、数组、Map、集合） |
| **语义冲突仍存在** | 两个人写同一段落的不同内容，技术上无冲突，语义上可能矛盾 |
| **需要专用存储** | 不能直接用普通 Markdown 文件 |

#### CRDT 与 AI 协作的关系

CRDT 解决的是**字符级冲突**，但 AI 协作的问题是**语义级冲突**。

如果两个人用 AI 重写同一篇文档，CRDT 会把两份修改都保留（技术上无冲突），但结果可能是一堆矛盾的内容。

**CRDT 适合的场景**：多人实时编辑，每个人编辑不同部分。

**CRDT 不适合的场景**：AI 全篇重写，需要语义级合并。

---

### 三种方案的关系

```
┌─────────────────────────────────────────────────────────────┐
│           AI 协作专用协议（协调器 + 提案机制）                │
│           最适合 AI 协作场景                                 │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  │ 提案包含语义操作
                  ▼
┌─────────────────────────────────────────────────────────────┐
│           语义级操作（操作可合并）                            │
│           解决 AI 全篇重写的语义冲突                          │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  │ 操作最终写入文档
                  ▼
┌─────────────────────────────────────────────────────────────┐
│           CRDT（字符级无冲突）                               │
│           解决多人实时编辑的字符冲突                          │
│           可选：如果需要实时协作                              │
└─────────────────────────────────────────────────────────────┘
```

**推荐组合**：AI 协作专用协议 + 语义级操作。如果还需要多人实时编辑，再加 CRDT。

---

### 最佳实践：跳出 Git 思维

| 实践 | 说明 |
|------|------|
| **不要用 Git 管理协作文档** | Git 是版本控制，不是协作工具 |
| **AI 提交提案而非直接修改** | 提案可以审核、合并、拒绝 |
| **定义语义操作原语** | 操作可以合并，文本无法合并 |
| **设计协调器** | 检测冲突、按规则合并、必要时人工决策 |
| **CRDT 作为可选层** | 如果需要多人实时编辑，再加 CRDT |

### 三层架构

```
┌─────────────────────────────────────────────────────────────┐
│                   协作层 (AI 协议/CRDT)                       │
│  提案协调、语义操作合并、字符级无冲突                          │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                   存储层 (Markdown/数据库)                   │
│  持久化、快照、备份                                          │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                   索引层 (向量数据库)                        │
│  Chunk 切分、向量化、增量更新                                │
└─────────────────────────────────────────────────────────────┘
```

**协作层负责**：提案协调、语义操作合并、字符级无冲突。

**存储层负责**：持久化、快照备份。

**索引层负责**：增量更新、检索。

**Git 的角色**：可选的备份机制，而非协作机制。

---

## 技术选型建议

### 文档解析

| 选项 | 优点 | 缺点 | 推荐场景 |
|------|------|------|----------|
| `markdown-it-py` | 纯 Python，AST 完整 | 需要自己实现切分逻辑 | 高度定制需求 |
| `LlamaIndex MarkdownNodeParser` | 开箱即用，集成度高 | 灵活度受框架约束 | 快速原型 |
| `Semantic Markdown Parser` | Token 感知，语义聚合 | 需要理解项目结构 | 平衡定制和效率 |

**推荐**：先用 LlamaIndex 快速跑通，再根据需要迁移到自研解析器。

### 全文检索

| 选项 | 优点 | 缺点 | 推荐场景 |
|------|------|------|----------|
| SQLite FTS5 | 零依赖，够用 | 不支持分布式 | 个人知识库首选 |
| Meilisearch | 上手快，效果好 | 需要单独部署 | 中等规模 |
| Elasticsearch | 功能完整，生态好 | 重，维护成本高 | 企业级 |

**推荐**：个人知识库用 SQLite FTS5 足够。

但如果你的笔记主体是中文，这里要多看一步。FTS5 默认的 `unicode61` tokenizer 更适合按通用 Unicode 规则切 token，对英文单词友好，对中文短词和子串召回不一定理想。至少要评估 `trigram` tokenizer，或者接入自定义中文分词器，否则全文检索对短语、路径片段和局部匹配的表现可能不稳定 [[16]](https://sqlite.org/fts5.html)。

### 向量检索

| 选项 | 优点 | 缺点 | 推荐场景 |
|------|------|------|----------|
| pgvector | 复用 PostgreSQL，省心 | 性能一般 | 已有 PG 环境 |
| Qdrant | 性能好，功能完整 | 需要单独部署 | 生产级首选 |
| Chroma | 本地运行，上手快 | 功能有限 | 快速原型 |

**推荐**：Qdrant，Docker 部署即可。

### Reranker

| 选项 | 优点 | 缺点 | 推荐场景 |
|------|------|------|----------|
| Cohere Rerank | 效果最好 | 需要联网，收费 | 追求效果 |
| BGE Reranker | 开源，可本地 | 效果略逊 | 隐私敏感 |
| Cross-Encoder | 灵活 | 需要自己选模型 | 定制需求 |

**推荐**：BGE Reranker，平衡效果和隐私。

---

## 实施路线图

### 第一阶段：最小可用系统（1-2 周）

目标：跑通核心链路，验证可行性

1. 用 LlamaIndex 实现基础切分
2. 用 SQLite FTS5 + Chroma 做混合检索
3. 用 BGE Reranker 做重排
4. 封装成 MCP Server
5. 在 Claude Code 中测试调用

### 第二阶段：切分优化（2-3 周）

目标：实现细致化的切分逻辑

1. 自研 AST 解析器
2. 实现标题层级切分
3. 实现语义聚合
4. 对比不同切分策略的检索效果

### 第三阶段：评估闭环（2-3 周）

目标：建立检索质量评估体系

1. 实现检索日志
2. 实现回答日志
3. 实现相关性分析
4. 可视化分析结果

### 第四阶段：联网补充（1-2 周）

目标：实现低置信度联网回退

1. 集成 Tavily 或 SerpAPI
2. 实现置信度判断逻辑
3. 实现本地 + 网页结果融合

---

## 参考来源

| 编号 | 来源 | 说明 |
|------|------|------|
| 1 | [Chunking Strategies for LLM Applications](https://www.pinecone.io/learn/chunking-strategies/) | Pinecone 对切分策略的系统性介绍，包括固定长度、语义切分、结构化切分等方法 |
| 2 | [Evaluating Retrieval Quality in RAG](https://arxiv.org/html/2404.13781v1) | eRAG 方法：用下游任务评估检索质量，提出用 LLM 回答质量反推文档相关性 |
| 3 | [Semantic Markdown Parser](https://github.com/tsensei/Semantic-Markdown-Parser) | Token 感知的 Markdown 切分器，支持 AST 解析和语义聚合 |
| 4 | [RAGFlow GitHub](https://github.com/infiniflow/ragflow) | 多路召回 + 融合重排的实践参考，生产级 RAG 系统架构 |
| 5 | [Evaluation Metrics for Search and Recommendation Systems](https://weaviate.io/blog/retrieval-evaluation-metrics) | Weaviate 对检索评估指标的详细解释，包括 Precision、Recall、MRR、MAP、NDCG |
| 6 | [LlamaIndex Node Parser Modules](https://developers.llamaindex.ai/python/framework/module_guides/loading/node_parsers/modules/) | LlamaIndex 官方文档，MarkdownNodeParser 的使用方法 |
| 7 | [BGE Reranker v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3) | BGE Reranker 的使用方法，支持本地部署和多语言 |
| 8 | [How to Manage and Refresh Data in Your Vector Database](https://vectorize.io/blog/how-to-manage-and-refresh-data-in-your-vector-database) | 向量数据库数据管理策略，包括批量更新、增量更新、实时更新三种方式 |
| 9 | [设计支持实时更新知识库的RAG系统数据同步机制](https://blog.csdn.net/gs80140/article/details/146591490) | 企业级 RAG 系统的数据同步机制设计，包括 CDC、消息队列、流处理等组件 |
| 10 | [Git多人协作与冲突解决](https://blog.51cto.com/gblfy/5653401) | Git 分支协作模式、冲突检测与解决方法 |
| 11 | [About CRDTs - Conflict-free Replicated Data Types](https://crdt.tech/) | CRDT 技术的官方资源站，介绍无冲突复制数据类型的原理和应用 |
| 12 | [初识协同编辑：OT和CRDT算法](https://wang1xiang.github.io/blog/docs/tiptap/tiptap-tutorial5.html) | OT 和 CRDT 算法的对比分析，Yjs 框架的原理介绍 |
| 13 | [Introducing the Model Context Protocol](https://www.anthropic.com/news/model-context-protocol) | Anthropic 对 MCP 的官方介绍，说明其开放协议定位与客户端/服务端结构 |
| 14 | [Introduction - Yjs Docs](https://docs.yjs.dev) | Yjs 官方文档，说明其共享数据结构、网络无关同步和协作编辑生态 |
| 15 | [Reciprocal rank fusion - Elasticsearch Reference](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion) | RRF 的官方说明，适合为混合检索的结果融合提供依据 |
| 16 | [SQLite FTS5 Extension](https://sqlite.org/fts5.html) | SQLite FTS5 官方文档，包含 `unicode61` 与 `trigram` tokenizer 的行为说明 |
| 17 | [Idempotency - AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/durable-execution-idempotency.html) | Durable execution 中的执行名、步骤幂等和重放语义，适合为提案幂等与重试设计提供依据 |
| 18 | [Deploying a workflow that waits for human approval in Step Functions](https://docs.aws.amazon.com/step-functions/latest/dg/tutorial-human-approval.html) | 官方的人审工作流示例，说明流程可以暂停等待人工 approve/reject 后继续推进 |
