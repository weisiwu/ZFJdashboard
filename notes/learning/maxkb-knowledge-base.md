# MaxKB 知识库构建指南：从文档上传到智能问答

> **主题**：知识库系统 / RAG / 向量化 / 开源工具
> **日期**：2026 年 4 月 2 日
> **标签**：AI 应用 / 知识库 / MaxKB / RAG

**开源企业级 RAG 平台，从文档上传到智能问答的完整流程，包括智能拆分、向量化、工作流编排和 MCP 工具调用。MaxKB 核心不是"选哪个开源系统"，而是"如何快速搭建一个开箱即用的知识库问答系统"。**

> **封面**：covers/MaxKB知识库构建指南_cover.png

---

## MaxKB 是什么

MaxKB（Max Knowledge Brain）是一款开源的企业级智能体平台，核心能力是基于 RAG 技术构建知识库问答系统 [[1]](https://docs.maxkb.pro/)。

由飞致云旗下的 1Panel 团队开发，GitHub Star 数超过 13k，属于国内最活跃的开源 RAG 项目之一 [[2]](https://github.com/1Panel-dev/MaxKB)。

### 核心特点

| 特点 | 说明 |
|------|------|
| **开箱即用** | 支持直接上传文档、自动爬取在线文档，自动完成文本拆分、向量化、RAG |
| **多模型支持** | 支持私有模型（DeepSeek、Llama、Qwen）和公有模型（OpenAI、Claude、Gemini） |
| **MCP 工具调用** | 支持通过 MCP 协议调用外部工具，实现"从回答到行动" |
| **零编码集成** | 可快速嵌入第三方业务系统 |
| **多模态** | 原生支持文本、图片、音频、视频的输入输出 |

---

## 知识库构建完整流程

MaxKB 的知识库构建分为四个阶段：文档导入 → 智能拆分 → 向量化 → 持久化存储 [[3]](https://blog.csdn.net/gitblog_00074/article/details/151164486)。

### 第一步：创建知识库

登录 MaxKB 管理后台（默认地址 `http://your_server_ip:8080`，账号 `admin`，密码 `MaxKB@123`），进入知识库管理页面：

1. 点击"新建知识库"
2. 填写名称和描述
3. 选择知识库类型（通用/技术文档/FAQ 等）
4. 选择向量模型（默认 `text2vec-base-Chinese`，可替换）

### 第二步：上传文档

MaxKB 支持多种文档来源：

| 来源类型 | 说明 | 适用场景 |
|----------|------|----------|
| 本地文档 | 上传 PDF、DOCX、Markdown、TXT 等 | 内部资料、手册、规范 |
| 在线文档 | 输入 URL 自动爬取 | 官方文档、博客文章 |
| Web 站点爬虫 | 配置域名和深度自动抓取 | 整站迁移、知识聚合 |

上传后系统自动触发处理流程，无需手动干预。

### 第三步：智能拆分

文档拆分是决定问答质量的关键步骤。MaxKB 内置三种拆分算法 [[3]](https://blog.csdn.net/gitblog_00074/article/details/151164486)：

#### 1. 按固定长度拆分

适合结构化文档，通过配置 `chunk_size` 参数控制段落长度。

```python
# 配置示例
chunk_size = 500  # 每个 chunk 约 500 字符
overlap = 50      # 相邻 chunk 重叠 50 字符
```

#### 2. 按语义段落拆分

基于标点符号和换行符识别自然段落，保持语义完整性。

```python
# 语义拆分核心逻辑
class SemanticChunkHandle(IChunkHandle):
    def handle(self, chunk_list: List[str]):
        semantic_chunks = []
        for text in chunk_list:
            # 基于 NLTK 的句子分割
            sentences = sent_tokenize(text)
            # 合并短句形成语义完整段落
            semantic_chunks.extend(self.merge_short_sentences(sentences))
        return semantic_chunks
```

#### 3. 混合拆分策略

长文档自动启用分层拆分：先按章节拆分，再进行语义切割。

#### 拆分参数建议

| 文档类型 | 推荐 chunk_size | 推荐 overlap |
|----------|-----------------|--------------|
| 技术手册 | 500-800 | 10-15% |
| FAQ 文档 | 200-300 | 5% |
| 长篇报告 | 800-1000 | 15% |
| 代码文档 | 300-500 | 10% |

### 第四步：向量化处理

向量化是实现语义检索的核心。MaxKB 将文本转化为高维向量后，通过余弦相似度快速找到语义相近的内容 [[3]](https://blog.csdn.net/gitblog_00074/article/details/151164486)。

#### 向量化核心代码

```python
def _save(self, text, source_type, knowledge_id, document_id, paragraph_id, source_id, is_active, embedding):
    # 生成文本向量
    text_embedding = [float(x) for x in embedding.embed_query(text)]
    
    # 存储向量及元数据
    embedding = Embedding(
        id=uuid.uuid7(),
        knowledge_id=knowledge_id,
        document_id=document_id,
        paragraph_id=paragraph_id,
        embedding=text_embedding,
        search_vector=to_ts_vector(text)  # 全文搜索向量
    )
    embedding.save()
```

#### 三种检索模式

MaxKB 支持三种检索模式，可在应用配置中选择：

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| 纯向量检索 | 基于余弦相似度精确匹配 | 语义相似查询 |
| 关键词检索 | 利用 PostgreSQL 全文搜索 | 精确词匹配、专有名词 |
| 混合检索 | 向量相似度 + 关键词匹配度加权排序 | 综合场景，推荐 |

---

## 高级功能：工作流编排与 MCP 工具调用

MaxKB 不仅是知识库问答系统，还是一个完整的智能体平台。核心能力包括工作流编排、函数库和 MCP 工具调用 [[7]](https://maxkb.cn/docs/v2/user_manual/app/workflow_app/)。

### 工作流编排

MaxKB 支持通过可视化画布编排 AI 流程，满足复杂业务场景。工作流由三类组件构成：

| 组件类型 | 说明 | 典型用途 |
|----------|------|----------|
| **基础组件** | AI 能力、知识库、业务逻辑 | AI 对话、知识库检索、条件判断 |
| **工具** | 通过函数处理复杂需求 | 数据库查询、API 调用、数据处理 |
| **智能体** | 引入其他智能体作为子流程 | 能力复用、模块化设计 |

#### 核心节点说明

**开始节点**：工作流执行的起点，输出用户问题 `{question}`。还支持：

- 文件上传：支持文档、图片、音频、视频
- 用户输入：会话开始时收集必要信息
- 接口传参：通过 URL 参数传入数据
- 会话变量：在对话流程中全程有效的变量

**AI 对话节点**：与大语言模型交互的核心节点。

- AI 模型：选择 LLM 及参数
- 系统提示词：设定角色和身份
- 用户提示词：引导模型生成输出
- 技能调用：自动调用 MCP、工具、Skills、智能体

**判断器节点**：根据条件分支执行不同逻辑。

**循环节点**：支持三种循环模式：

1. 数组循环：遍历数组元素
2. 指定次数循环：固定次数重复
3. 无限循环：持续执行直到满足停止条件

#### 一个工作流编排实例

假设要构建一个"智能客服"应用，流程如下：

```
开始 → 知识库检索 → 判断器（是否找到答案）
                        ↓
                   是 → AI 对话 → 结束
                        ↓
                   否 → MCP 工具（查询工单系统） → AI 对话 → 结束
```

具体配置：

1. **开始节点**：接收用户问题 `{question}`
2. **知识库检索节点**：检索 FAQ 知识库，输出 `{paragraph_list}`
3. **判断器节点**：判断 `{paragraph_list}` 是否为空
   - 分支 A（不为空）：进入 AI 对话，基于检索结果回答
   - 分支 B（为空）：调用 MCP 工具查询工单系统
4. **AI 对话节点**：生成最终回答

### MCP 工具调用

MaxKB 支持 MCP（Model Context Protocol）协议，让 AI 能够调用外部工具 [[8]](https://www.oschina.net/news/343279/maxkb-1-10-3-lts)。

#### MCP 的核心价值

传统 RAG 系统只能"回答"，无法"行动"。MCP 让 AI 能够：

- 查询数据库
- 调用内部 API
- 触发外部工作流
- 执行业务操作

#### 如何配置 MCP

在 AI 对话节点中，可以添加 MCP 工具：

1. **引用 MCP**：从已配置的 MCP 服务中选择
2. **自定义 MCP Server Config**：直接配置 MCP 服务端点

```json
// MCP Server Config 示例
{
  "mcpServers": {
    "database-query": {
      "command": "python",
      "args": ["/path/to/mcp_server.py"],
      "env": {
        "DB_URL": "postgresql://localhost/mydb"
      }
    }
  }
}
```

#### 注意事项

MCP 工具调用需要大语言模型支持 Function Calling。如果模型不支持，配置将无效 [[7]](https://maxkb.cn/docs/v2/user_manual/app/workflow_app/)。

支持的模型包括：

- 阿里云百炼 Qwen-Max
- OpenAI GPT 系列
- Claude 系列
- 其他支持 Function Calling 的模型

### 函数库

MaxKB 提供函数库，支持内置函数和自定义函数 [[9]](https://maxkb.cn/docs/v1/user_manual/fx/fx/)。

#### 内置函数

| 函数 | 说明 | 典型用途 |
|------|------|----------|
| MySQL 查询 | 查询 MySQL 数据库 | 从业务系统获取数据 |
| PostgreSQL 查询 | 查询 PostgreSQL 数据库 | 从业务系统获取数据 |
| Google Search | Google 搜索 | 联网补充信息 |
| 博查搜索 | 中文搜索 | 国内场景 |
| LangSearch | 语义搜索 | 高精度检索 |

内置函数需要配置启动参数（如数据库连接信息、API Key）后才能使用。

#### 自定义函数

用户可以根据业务需求编写自定义函数：

```python
# 自定义函数示例：提取关键词
def extract_keywords(text: str) -> list:
    """
    从文本中提取关键词
    
    参数:
        text: 输入文本
    
    返回:
        关键词列表
    """
    import jieba.analyse
    keywords = jieba.analyse.extract_tags(text, topK=5)
    return keywords
```

函数创建后，在工作流编排时以组件方式调用。

#### 函数与 MCP 的区别

| 特性 | 函数 | MCP |
|------|------|------|
| 定义方式 | 在 MaxKB 内部编写 | 外部服务，通过协议调用 |
| 适用场景 | 简单数据处理、API 调用 | 复杂外部系统集成 |
| 灵活性 | 受限于 MaxKB 环境 | 可独立部署和扩展 |
| 调用方式 | 工作流节点直接调用 | 通过 LLM Function Calling |

---

## 向量模型选型

MaxKB 默认内置 `text2vec-base-Chinese` 向量模型，但存在一些局限 [[4]](https://www.cnblogs.com/xiaobaiysf/p/18743739)：

### 默认模型的不足

- **长文本处理能力弱**：处理长文本时可能搜索不到相关结果
- **向量"坍缩"现象**：BERT 倾向于将所有句子编码到较小空间区域，导致大多数句子对都有较高相似度分数
- **模型更新滞后**：官方库最近更新时间为 2023 年 9 月

### 推荐的替代模型

| 模型 | 特点 | 适用场景 |
|------|------|----------|
| **BGE 系列** | 全球下载量超 1500 万，多语言支持好 | 通用场景首选 |
| **M3E** | 私有部署友好，资源节约 | 隐私敏感场景 |
| **OpenAI text-embedding-ada-002** | 效果好，支持 8191 token | 公有云场景 |
| **Sentence Transformers** | 句子级别效果好 | 短文本匹配 |

### 如何替换向量模型

MaxKB 支持三种方式接入向量模型 [[4]](https://www.cnblogs.com/xiaobaiysf/p/18743739)：

1. **接入公有向量模型**：直接配置 OpenAI、百度千帆等 API
2. **通过 Xinference 接入**：本地部署向量模型服务
3. **通过 Ollama 接入**：使用 Ollama 托管本地模型

具体步骤：

```
步骤一：安装部署 Xinference 或 Ollama
步骤二：加载向量模型（如 bge-large-zh-v1.5）
步骤三：在 MaxKB 模型管理中对接向量模型
步骤四：在知识库配置中选择新向量模型
```

---

## 实操案例：10 分钟构建技术文档知识库

### 场景

假设你有一份 Python 编程手册 PDF，希望通过 MaxKB 实现智能问答。

### 步骤 1：部署 MaxKB

```bash
docker run -d --name=maxkb --restart=always -p 8080:8080 -v ~/.maxkb:/opt/maxkb 1panel/maxkb
```

访问 `http://localhost:8080`，账号 `admin`，密码 `MaxKB@123`。

### 步骤 2：配置模型

进入"模型管理"：

1. 添加 LLM（如 Ollama 本地的 qwen2.5，或 OpenAI API）
2. 添加向量模型（推荐 bge-large-zh-v1.5）

### 步骤 3：创建知识库

1. 进入"知识库管理" → "新建知识库"
2. 名称：Python 编程手册
3. 类型：技术文档
4. 向量模型：bge-large-zh-v1.5

### 步骤 4：上传文档

上传 PDF 文件，系统自动处理：

```
处理中...
├── 文档解析：提取文本内容
├── 智能拆分：按章节和代码块拆分
├── 向量化：调用 embedding 生成向量
└── 完成：128 个段落，326 个向量
```

### 步骤 5：创建应用

进入"应用管理" → "新建应用"：

1. 关联知识库：Python 编程手册
2. 配置检索：top-k=5，混合检索
3. 配置提示词：

```
你是一个 Python 编程助手。请基于提供的文档内容回答问题。
如果文档中没有相关信息，请明确说"我不知道"。
回答时请引用来源段落。
```

### 步骤 6：测试问答

在聊天界面输入：`如何使用 Python 的列表推导式？`

系统返回：

```
列表推导式是 Python 中创建列表的简洁语法。基本格式：

[x for x in iterable if condition]

示例：
# 生成 1-10 的平方数列表
squares = [x**2 for x in range(10)]

来源：Python 编程手册 - 第 3 章 列表与推导式
```

---

## MaxKB 的设计思路

### 为什么选择 PostgreSQL + pgvector

MaxKB 使用 PostgreSQL + pgvector 作为向量数据库，而非独立的向量库（如 Qdrant、Milvus）[[2]](https://github.com/1Panel-dev/MaxKB)。

原因：

1. **简化部署**：一个数据库同时支持全文搜索和向量检索
2. **混合检索原生支持**：可直接结合 `tsvector` 全文搜索和向量相似度
3. **运维成本低**：复用现有 PostgreSQL 运维能力

### 为什么默认用 text2vec-base-Chinese

虽然这个模型有局限，但选择它的原因是：

1. **开箱即用**：无需额外配置即可启动
2. **中文优化**：针对中文语义匹配任务优化
3. **资源友好**：模型体积小，CPU 也能跑

用户可以根据需求替换为更强的模型。

### RAG 管道的核心设计

MaxKB 的 RAG 管道遵循标准流程 [[5]](https://sider.ai/blog/ai-tools/how-to-use-maxkb-a-practical-end-to-end-guide-to-build-ai-assistants-fast)：

```
Ingest（摄入）→ Retrieve（检索）→ Generate（生成）
```

关键设计决策：

| 环节 | 设计选择 | 原因 |
|------|----------|------|
| 摄入 | Celery 异步任务队列 | 避免阻塞主线程，提升稳定性 |
| 检索 | 混合检索 + 可选 rerank | 兼顾语义匹配和精确匹配 |
| 生成 | 可配置提示词和护栏 | 控制回答质量和安全性 |

---

## 与其他方案的对比

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **MaxKB** | 开箱即用、多模型、MCP 支持 | 切分策略相对简单 | 企业内部知识库、客服 |
| **Dify** | 可视化编排、插件生态丰富 | 部署稍复杂 | 需要复杂工作流的场景 |
| **RAGFlow** | 切分策略精细、支持多模态 | 学习曲线陡 | 高精度检索需求 |
| **自研** | 完全可控、可深度定制 | 开发成本高 | 特殊需求、研究场景 |

---

## 最佳实践建议

### 文档准备

1. **清洗内容**：移除导航栏、页脚、重复内容
2. **分类标签**：按产品、版本、日期打标签，便于后续过滤
3. **时效管理**：设置文档有效期，定期更新

### 检索调优

1. **chunk_size 调优**：从 500 开始，根据问答效果调整
2. **top-k 调优**：从 4-8 开始，太少召回不足，太多噪音增加
3. **启用 rerank**：对召回结果重排序，提升精度

### 评估指标

| 指标 | 说明 | 目标值 |
|------|------|--------|
| 召回准确率 | 前 K 个结果中相关文档比例 | > 80% |
| 回答准确率 | 回答正确的比例 | > 85% |
| 无答案率 | 应该拒绝但回答了的比例 | < 10% |
| 平均延迟 | 从提问到返回的时间 | < 3s |

---

## 参考来源

| 编号 | 来源 | 说明 |
|------|------|------|
| 1 | [MaxKB Documentation](https://docs.maxkb.pro/) | MaxKB 官方文档，介绍核心功能和架构 |
| 2 | [GitHub - 1Panel-dev/MaxKB](https://github.com/1Panel-dev/MaxKB) | GitHub 仓库，包含快速开始和技术栈说明 |
| 3 | [10倍效率提升：MaxKB文档自动拆分与向量化全攻略](https://blog.csdn.net/gitblog_00074/article/details/151164486) | 详细介绍 MaxKB 的拆分策略和向量化实现 |
| 4 | [基于RAG的MaxKB知识库问答系统如何选择向量模型](https://www.cnblogs.com/xiaobaiysf/p/18743739) | 向量模型选型指南，包括默认模型局限和替代方案 |
| 5 | [How to Use MaxKB: A Practical, End-to-End Guide](https://sider.ai/blog/ai-tools/how-to-use-maxkb-a-practical-end-to-end-guide-to-build-ai-assistants-fast) | 实战教程，涵盖 RAG、工具调用、工作流编排 |
| 6 | [MaxKB 产品介绍 - FIT2CLOUD 飞致云](https://bbs.fit2cloud.com/t/topic/3876) | 官方产品介绍，核心功能概览 |
| 7 | [高级智能体 - MaxKB 文档](https://maxkb.cn/docs/v2/user_manual/app/workflow_app/) | 工作流编排详细说明，包括节点类型和配置方法 |
| 8 | [全面支持 MCP 协议，开启便捷连接之旅](https://www.oschina.net/news/343279/maxkb-1-10-3-lts) | MCP 协议支持说明，内置函数介绍 |
| 9 | [函数库 - MaxKB 文档](https://maxkb.cn/docs/v1/user_manual/fx/fx/) | 内置函数和自定义函数的使用说明 |
