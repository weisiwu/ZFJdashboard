# PRD — 模块5：知识库（Knowledge Base）

> 版本：V1.0
> 最后更新：2026-04-17
> 优先级：P1（增强功能）

---

## 1. 功能概述

知识库是 TeamClaw 智能能力的核心组件，为 Agent 提供项目上下文、历史经验和领域知识的检索能力。它通过向量化存储和语义搜索，将项目的代码、文档、配置等结构化与非结构化内容转化为可检索的知识片段，支持 RAG（检索增强生成）流程，确保 Agent 在执行任务时能够精准定位相关资料。

本模块的核心目标：
- **多源索引**：支持代码、文档、配置等多种文件格式的索引和检索
- **语义搜索**：基于向量化存储的语义搜索，而非简单关键词匹配
- **增量更新**：监听文件变更，增量更新索引，避免全量重建
- **RAG 集成**：与 Agent 对话流程无缝集成，自动检索上下文相关内容
- **本地优先**：支持本地嵌入模型（onnxruntime + MiniLM）和 API 嵌入服务切换
- **知识关联**：自动提取知识片段间的关联关系，构建项目知识图谱
- **任务绑定**：知识库与任务、对话关联，支持按任务上下文精准检索

---

## 2. 核心概念

### 2.1 知识片段（Knowledge Fragment）

知识片段是知识库的最小可检索单元。一个文件被切分为多个片段，每个片段保持语义完整性。

```typescript
interface KnowledgeFragment {
  id: string;                   // 唯一标识
  file_id: string;              // 所属文件
  content: string;              // 文本内容
  embedding: number[];          // 向量表示（归一化）
  metadata: {
    file_type: string;          // md, py, ts, rs, json, yaml
    language?: string;          // 代码语言（ts, rs, python 等）
    start_line: number;         // 起始行号
    end_line: number;           // 结束行号
    tokens: number;             // Token 数量
    created_at: string;
    updated_at: string;
  };
  tags: string[];              // 自动提取的标签（如「数据库」「API」「前端」）
}
```

### 2.2 知识库（Knowledge Base）

知识库是按项目组织的数据集合。每个 TeamClaw 项目对应一个独立知识库。

```
KnowledgeBase
├── project_id: "project-uuid"
├── status: "active" | "building" | "error"
├── fragments_count: 12345
├── files_count: 256
├── embedding_provider: "local" | "openai" | "zhipu"
├── embedding_model: "sentence-transformers/all-MiniLM-L6-v2"
├── last_indexed_at: "2026-04-17T05:00:00Z"
├── storage_path: "/path/to/knowledge-bases/project-uuid"
└── settings: {
    chunk_size: 512,            // 每片段 Token 数
    chunk_overlap: 50,          // 片段重叠 Token 数
    max_fragments_per_file: 1000,
    enable_auto_index: true
  }
```

### 2.3 向量索引（Vector Index）

向量索引用于高效检索相似片段。采用 IVF（Inverted File）索引结构。

```
Vector Index (IVF)
├── nlist: 256                // 聚类中心数
├── nprobe: 32                // 搜索时检查的聚类数
├── metric: "cosine"           // 余弦相似度
└── dimension: 384            // MiniLM-L6 向量维度
```

### 2.4 嵌入提供商（Embedding Provider）

支持本地和远程两种嵌入方式。

| 提供商 | 模型 | 维度 | 延迟 | 成本 | 用途 |
|--------|------|------|------|------|------|
| Local | all-MiniLM-L6-v2 | 384 | ~20ms | 免费 | 离线、隐私敏感场景 |
| OpenAI | text-embedding-3-small | 1536 | ~500ms | 付费 | 高精度需求 |
| 智谱 | embedding-v2 | 1024 | ~300ms | 付费 | 中文优化 |

---

## 3. 用户故事

### P1 优先级

1. **作为开发者**，我希望首次打开项目时自动索引所有代码和文档，这样 Agent 就能立即检索上下文。
2. **作为 PM**，我希望通过语义搜索查询「支付接口设计」相关内容，而非手动翻阅代码。
3. **作为开发者**，我希望修改代码后知识库自动增量更新，而不是全量重建索引。
4. **作为团队 Leader**，我希望查看知识库的健康状态（片段数量、索引状态、上次更新时间）。
5. **作为开发者**，我希望切换本地和 API 嵌入模型，在离线和在线场景间无缝切换。
6. **作为 PM**，我希望知识库与对话关联，查询时只返回当前对话上下文相关的知识。
7. **作为开发者**，我希望手动触发全量索引重建，在索引损坏时快速恢复。

### P2 优先级

8. **作为开发者**，我希望查看知识图谱，了解模块、API、数据表之间的依赖关系。
9. **作为 PM**，我希望导出知识片段为 JSON/CSV，便于外部工具处理。
10. **作为开发者**，我希望排除某些目录（如 `node_modules`, `.git`）不被索引。
11. **作为 QA**，我希望验证知识片段的完整性，确保无重复、无遗漏。

### P3 优先级

12. **作为开发者**，我希望自定义切分策略，针对不同文件类型采用不同规则。

---

## 4. 功能需求清单

### 4.1 文件索引与扫描

- 支持扫描项目目录下所有符合条件的文件
- 按文件类型过滤器（支持 glob 模式：`**/*.md`, `src/**/*.ts`）
- 默认排除目录：`node_modules`, `.git`, `dist`, `build`, `.next`
- 支持自定义排除目录和文件扩展名
- 按文件哈希检测变更，仅处理修改过的文件

### 4.2 内容切分与片段生成

- 按语义边界切分（如代码按函数/类，文档按段落）
- 支持可配置的片段 Token 大小（默认 512）和重叠（默认 50）
- 保留片段的元数据：文件路径、行号、语言类型
- 针对不同文件类型应用不同切分策略

### 4.3 向量化与嵌入

- 本地嵌入模型：onnxruntime + MiniLM-L6-v2（首次自动下载）
- API 嵌入服务：OpenAI text-embedding-3-small、智谱 embedding-v2
- 支持批量嵌入（每批 100 个片段）
- 嵌入结果缓存，避免重复计算

### 4.4 语义搜索

- 支持文本查询，自动向量化查询语句
- 返回 Top-K 相似片段（K 可配置，默认 5）
- 支持按文件类型、语言、标签过滤
- 支持相似度阈值过滤（默认 > 0.7）

### 4.5 增量索引

- 基于文件系统监听（fs.watch）或 Git diff 检测变更
- 新增文件：创建知识片段并嵌入
- 修改文件：删除旧片段，重新切分和嵌入
- 删除文件：删除相关片段
- 支持手动触发增量索引

### 4.6 知识图谱

- 自动提取知识片段间的关联关系：
  - 代码引用关系（import/require/include）
  - API 调用关系
  - 数据库表关联
  - 文档交叉引用
- 支持可视化图谱展示

### 4.7 RAG 集成

- Agent 对话时自动检索相关知识片段
- 支持按对话上下文过滤（project_id, conversation_id）
- 支持检索结果排序和去重
- 支持检索结果摘要生成

### 4.8 知识库管理

- 查看知识库状态（片段数、文件数、最后更新时间）
- 切换嵌入提供商
- 配置切分策略
- 手动触发全量重建
- 导出知识片段

---

## 5. 数据模型

### 5.1 SQLite 表结构

#### knowledge_bases（知识库主表）

```sql
CREATE TABLE knowledge_bases (
    id              TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL REFERENCES projects(id),
    status          TEXT NOT NULL DEFAULT 'active', -- active, building, error
    fragments_count INTEGER NOT NULL DEFAULT 0,
    files_count     INTEGER NOT NULL DEFAULT 0,
    embedding_provider TEXT NOT NULL DEFAULT 'local',
    embedding_model TEXT NOT NULL DEFAULT 'all-MiniLM-L6-v2',
    last_indexed_at TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(project_id)
);

CREATE INDEX idx_kb_project ON knowledge_bases(project_id);
CREATE INDEX idx_kb_status ON knowledge_bases(status);
```

#### knowledge_fragments（知识片段表）

```sql
CREATE TABLE knowledge_fragments (
    id              TEXT PRIMARY KEY,
    knowledge_base_id TEXT NOT NULL REFERENCES knowledge_bases(id),
    file_id         TEXT NOT NULL,
    content         TEXT NOT NULL,
    file_type       TEXT NOT NULL,
    language        TEXT,
    start_line      INTEGER NOT NULL,
    end_line        INTEGER NOT NULL,
    tokens          INTEGER NOT NULL,
    embedding       BLOB NOT NULL, -- 序列化的浮点数组
    tags            TEXT, -- JSON 数组
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_kb_kb_id ON knowledge_fragments(knowledge_base_id);
CREATE INDEX idx_kb_file_id ON knowledge_fragments(file_id);
CREATE INDEX idx_kb_file_type ON knowledge_fragments(file_type);
CREATE INDEX idx_kb_language ON knowledge_fragments(language);
```

#### knowledge_files（文件索引表）

```sql
CREATE TABLE knowledge_files (
    id              TEXT PRIMARY KEY,
    knowledge_base_id TEXT NOT NULL REFERENCES knowledge_bases(id),
    file_path       TEXT NOT NULL,
    file_hash       TEXT NOT NULL, -- SHA-256
    file_size       INTEGER NOT NULL,
    file_type       TEXT NOT NULL,
    last_scanned_at TEXT NOT NULL DEFAULT (datetime('now')),
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(knowledge_base_id, file_path)
);

CREATE INDEX idx_kf_kb_id ON knowledge_files(knowledge_base_id);
CREATE INDEX idx_kf_hash ON knowledge_files(file_hash);
```

#### knowledge_graph_edges（知识图谱边表）

```sql
CREATE TABLE knowledge_graph_edges (
    id              TEXT PRIMARY KEY,
    knowledge_base_id TEXT NOT NULL REFERENCES knowledge_bases(id),
    source_fragment_id TEXT NOT NULL REFERENCES knowledge_fragments(id),
    target_fragment_id TEXT NOT NULL REFERENCES knowledge_fragments(id),
    edge_type       TEXT NOT NULL, -- 'import', 'call', 'reference', 'related'
    weight          REAL NOT NULL DEFAULT 1.0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_kge_kb_id ON knowledge_graph_edges(knowledge_base_id);
CREATE INDEX idx_kge_source ON knowledge_graph_edges(source_fragment_id);
CREATE INDEX idx_kge_target ON knowledge_graph_edges(target_fragment_id);
```

#### knowledge_search_logs（搜索日志表）

```sql
CREATE TABLE knowledge_search_logs (
    id              TEXT PRIMARY KEY,
    knowledge_base_id TEXT NOT NULL REFERENCES knowledge_bases(id),
    query           TEXT NOT NULL,
    top_k           INTEGER NOT NULL,
    results_count   INTEGER NOT NULL,
    filters         TEXT, -- JSON
    execution_time_ms INTEGER NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_ksl_kb_id ON knowledge_search_logs(knowledge_base_id);
CREATE INDEX idx_ksl_created ON knowledge_search_logs(created_at DESC);
```

---

## 6. Tauri Commands

### 6.1 接口定义

```typescript
// ── 知识库管理 ──

interface CreateKnowledgeBase {
  project_id: string;
  embedding_provider: 'local' | 'openai' | 'zhipu';
  embedding_model?: string;
}

interface GetKnowledgeBase {
  project_id: string;
}

interface UpdateKnowledgeBaseSettings {
  knowledge_base_id: string;
  settings: {
    chunk_size?: number;
    chunk_overlap?: number;
    max_fragments_per_file?: number;
    enable_auto_index?: boolean;
  };
}

// ── 索引操作 ──

interface TriggerFullIndex {
  knowledge_base_id: string;
  file_patterns?: string[]; // glob 模式，如 ['**/*.md', 'src/**/*.ts']
  exclude_patterns?: string[]; // 如 ['node_modules', '.git']
}

interface TriggerIncrementalIndex {
  knowledge_base_id: string;
}

interface GetIndexStatus {
  knowledge_base_id: string;
}

// ── 搜索操作 ──

interface SearchKnowledge {
  knowledge_base_id: string;
  query: string;
  top_k?: number;
  filters?: {
    file_type?: string;
    language?: string;
    tags?: string[];
  };
  conversation_id?: string; // 限制在对话上下文内
}

// ── 知识图谱 ──

interface GetKnowledgeGraph {
  knowledge_base_id: string;
  fragment_id?: string; // 可选：查询特定片段的关联
  edge_type?: string;
  max_depth?: number;
}

// ── 导出操作 ──

interface ExportFragments {
  knowledge_base_id: string;
  format: 'json' | 'csv';
  filters?: {
    file_type?: string;
    language?: string;
  };
}

// ── 统计信息 ──

interface GetKnowledgeStats {
  knowledge_base_id: string;
}
```

### 6.2 命令清单

```rust
#[tauri::command]
fn create_knowledge_base(
    state: State<DbState>,
    project_id: String,
    embedding_provider: String,
    embedding_model: Option<String>
) -> ApiResponse<KnowledgeBase>;

#[tauri::command]
fn get_knowledge_base(
    state: State<DbState>,
    project_id: String
) -> ApiResponse<KnowledgeBase>;

#[tauri::command]
fn update_knowledge_base_settings(
    state: State<DbState>,
    knowledge_base_id: String,
    settings: Json<Value>
) -> ApiResponse<String>;

#[tauri::command]
fn trigger_full_index(
    state: State<DbState>,
    knowledge_base_id: String,
    file_patterns: Option<Vec<String>>,
    exclude_patterns: Option<Vec<String>>
) -> ApiResponse<IndexTask>;

#[tauri::command]
fn trigger_incremental_index(
    state: State<DbState>,
    knowledge_base_id: String
) -> ApiResponse<IndexTask>;

#[tauri::command]
fn get_index_status(
    state: State<DbState>,
    knowledge_base_id: String
) -> ApiResponse<IndexStatus>;

#[tauri::command]
fn search_knowledge(
    state: State<DbState>,
    knowledge_base_id: String,
    query: String,
    top_k: Option<i32>,
    filters: Option<Json<Value>>,
    conversation_id: Option<String>
) -> ApiResponse<Vec<SearchResult>>;

#[tauri::command]
fn get_knowledge_graph(
    state: State<DbState>,
    knowledge_base_id: String,
    fragment_id: Option<String>,
    edge_type: Option<String>,
    max_depth: Option<i32>
) -> ApiResponse<KnowledgeGraph>;

#[tauri::command]
fn export_fragments(
    state: State<DbState>,
    knowledge_base_id: String,
    format: String,
    filters: Option<Json<Value>>
) -> ApiResponse<String>; // 返回导出内容或文件路径

#[tauri::command]
fn get_knowledge_stats(
    state: State<DbState>,
    knowledge_base_id: String
) -> ApiResponse<KnowledgeStats>;
```

---

## 7. UI 交互流程

### 7.1 知识库概览界面

```
┌─────────────────────────────────────────────────────────┐
│  知识库概览                                           │
├─────────────────────────────────────────────────────────┤
│  项目：TeamClaw                                       │
│  状态：🟢 已索引 (12,345 片段)                         │
│  最后更新：2026-04-17 05:00                           │
│  嵌入模型：all-MiniLM-L6-v2 (本地)                    │
├─────────────────────────────────────────────────────────┤
│  [🔄 重建索引]  [⚙️ 设置]  [📊 统计]                  │
├─────────────────────────────────────────────────────────┤
│  搜索框                                            [🔍]│
│  ───────────────────────────────────────────────────── │
│  搜索结果（Top 5）：                                  │
│  1. [src/db/mod.rs:45-78] DB 连接池初始化 (0.92)    │
│  2. [docs/api/payment.md:12-34] 支付接口文档 (0.88) │
│  3. [src/payment/service.ts:102-145] 支付服务 (0.85) │
│  4. [README.md:5-15] 项目介绍 (0.79)               │
│  5. [.env.example:1-8] 环境变量 (0.76)            │
├─────────────────────────────────────────────────────────┤
│  知识图谱预览                                         │
│  ┌──────┐         ┌──────┐         ┌──────┐         │
│  │ API  │────────►│Payment│────────►│  DB  │         │
│  └──────┘         └──────┘         └──────┘         │
└─────────────────────────────────────────────────────────┘
```

### 7.2 索引任务进度界面

```
┌─────────────────────────────────────────────────────────┐
│  索引进行中...                                        │
├─────────────────────────────────────────────────────────┤
│  进度：██████████████████░░░░░░░░░ 65%               │
│  已处理：256 / 394 文件                               │
│  已生成：12,345 片段                                  │
│  嵌入中：██████████████░░░░░ 80%                      │
├─────────────────────────────────────────────────────────┤
│  当前文件：src/payment/service.ts                     │
│  状态：嵌入向量中...                                  │
├─────────────────────────────────────────────────────────┤
│  [⏸️ 暂停]  [🗑️ 取消]                                 │
└─────────────────────────────────────────────────────────┘
```

### 7.3 知识图谱可视化界面

```
┌─────────────────────────────────────────────────────────┐
│  知识图谱                                             │
├─────────────────────────────────────────────────────────┤
│  过滤器：[文件类型▼] [语言▼] [边类型▼]               │
│  [放大] [缩小] [布局切换] [导出]                      │
├─────────────────────────────────────────────────────────┤
│                        ┌──────────┐                    │
│                   ┌───►│  Main    │                    │
│                   │    └────┬─────┘                    │
│  ┌─────────┐     │         │                          │
│  │ Payment │─────┘         ▼                          │
│  └────┬────┘            ┌──────────┐                  │
│       │                ┌►│  Service │                  │
│       │                │ └────┬─────┘                  │
│       ▼                │      │                        │
│  ┌─────────┐          │      ▼                        │
│  │   DB    │◄─────────┤ ┌──────────┐                  │
│  └─────────┘          └─│   Cache  │                  │
│                        └──────────┘                  │
│  顶点：156   边：324                                │
└─────────────────────────────────────────────────────────┘
```

---

## 8. 边界条件与异常处理

| 场景 | 处理方式 |
|------|---------|
| 文件编码非 UTF-8 | 跳过并记录警告，标记为 `skipped` |
| 文件过大（> 10MB） | 跳过并记录，提示用户手动处理 |
| 嵌入模型未下载 | 自动从 CDN 下载（本地模型），失败则切换到 API |
| 嵌入 API 调用失败 | 重试 3 次，失败后降级到本地模型或跳过 |
| 向量存储空间不足 | 清理最久未访问的片段，或提示用户清理 |
| 搜索查询为空 | 返回错误，要求输入查询文本 |
| 知识库不存在 | 返回 404，提示用户先创建知识库 |
| 索引任务中断（如进程崩溃） | 支持从断点续传，跳过已完成的文件 |
| 多个索引任务并发 | 拒绝新任务，提示当前任务进行中 |
| 知识图谱循环引用 | 检测并截断，最大深度 5 层 |
| 导出数据量过大 | 分页导出，每批 1000 片段 |

---

## 9. 性能指标与优化

| 指标 | 目标 | 优化措施 |
|------|------|---------|
| 全量索引速度 | > 100 文件/秒 | 并发嵌入，批量插入 |
| 增量索引延迟 | < 5 秒 | 文件系统监听，即时触发 |
| 嵌入延迟（本地） | < 30 ms/片段 | ONNX 优化，GPU 加速（可选） |
| 嵌入延迟（API） | < 500 ms/片段 | 批量请求，连接池复用 |
| 搜索延迟 | < 100 ms（Top 5） | IVF 索引，结果缓存 |
| 向量存储 | < 500 MB/万片段 | 量化压缩（INT8） |
| 知识图谱构建 | < 10 秒/千片段 | 增量更新，预计算索引 |
| 并发搜索 | > 50 QPS | 无锁数据结构，连接池 |

---

## 10. 验收标准

### P1 验收（核心功能）
- [ ] 知识库创建功能正常，支持选择嵌入提供商
- [ ] 全量索引功能正常，支持自定义文件过滤
- [ ] 增量索引功能正常，文件变更自动触发更新
- [ ] 语义搜索功能正常，返回 Top-K 相似片段
- [ ] 本地嵌入模型正常工作，首次自动下载
- [ ] API 嵌入服务正常工作，支持 OpenAI 和智谱
- [ ] 嵌入提供商切换正常，已索引数据兼容
- [ ] 知识片段元数据正确记录（文件路径、行号、语言）
- [ ] 知识库状态展示正常（片段数、文件数、更新时间）
- [ ] 搜索日志正确记录，支持筛选和导出
- [ ] 知识图谱自动构建，节点和边正确关联
- [ ] 知识图谱可视化界面正常，支持缩放和过滤
- [ ] RAG 集成正常，Agent 对话时自动检索相关内容
- [ ] 对话上下文过滤正常，检索结果限制在对话范围内
- [ ] 手动重建索引功能正常，支持中断和恢复
- [ ] 异常场景正确处理（文件编码、API 失败、空间不足）

### P2 验收（增强功能）
- [ ] 导出知识片段功能正常，支持 JSON 和 CSV 格式
- [ ] 自定义排除目录功能正常
- [ ] 切分策略可配置，支持不同文件类型
- [ ] 知识图谱导出功能正常

### P3 验收（扩展功能）
- [ ] 自定义嵌入模型插件 API 可用
- [ ] 知识库分享功能（可选）

---

*文档维护者：TeamClaw 项目组*
