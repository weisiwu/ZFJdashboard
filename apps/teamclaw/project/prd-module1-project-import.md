# PRD — 模块1：项目导入

> 版本：V1.0  
> 最后更新：2026-04-16  
> 优先级：P0（MVP 核心）

---

## 1. 功能概述

项目导入是 TeamClaw 的入口模块。用户通过创建/导入项目，建立 Agent 协作的工作空间。支持从零创建新项目，或导入已有 Git 仓库，配置 Agent 团队后即可开始多 Agent 协作。

---

## 2. 用户故事

| 编号 | 用户故事 | 优先级 |
|------|---------|--------|
| US-01 | 作为用户，我想创建一个新项目并设置基本信息 | P0 |
| US-02 | 作为用户，我想导入本地已有代码仓库 | P0 |
| US-03 | 作为用户，我想通过 Git URL 克隆远程仓库 | P0 |
| US-04 | 作为用户，我想为项目配置 Agent 团队（启用/禁用角色） | P0 |
| US-05 | 作为用户，我想在项目列表中浏览、搜索、筛选项目 | P0 |
| US-06 | 作为用户，我想查看项目详情（概览、对话、任务、知识库） | P0 |
| US-07 | 作为用户，我想删除或归档不再使用的项目 | P1 |
| US-08 | 作为用户，我想为项目设置标签以便分类管理 | P1 |
| US-09 | 作为用户，我想在项目间快速切换 | P1 |
| US-10 | 作为用户，我想编辑项目基本信息 | P2 |

---

## 3. 功能需求清单

### 3.1 创建新项目 [P0]

**输入**：
- 项目名称（必填，2-50字符）
- 项目描述（选填，最多500字符）
- 标签（选填，最多5个）
- 项目路径（本地存储目录，默认 `~/TeamClaw/projects/{name}`）

**流程**：
1. 用户点击「新建项目」
2. 填写项目信息表单
3. 系统创建项目目录结构
4. 初始化 SQLite 数据库记录
5. 进入项目配置页面

**输出**：项目创建成功，进入项目详情页

### 3.2 导入已有仓库 [P0]

**方式一：本地路径**
1. 用户选择「导入项目」→「本地目录」
2. 选择本地代码目录（Tauri 文件选择器）
3. 系统扫描目录，识别技术栈（package.json、pom.xml、Cargo.toml 等）
4. 展示识别结果，用户确认
5. 创建项目记录，关联本地路径

**方式二：Git 克隆**
1. 用户选择「导入项目」→「Git 仓库」
2. 输入 Git URL（支持 HTTPS/SSH）
3. 选择本地克隆目录
4. 系统执行 `git clone`，展示进度
5. 克隆完成后，扫描识别技术栈
6. 创建项目记录

**技术栈自动识别规则**：

| 文件 | 识别为 |
|------|--------|
| `package.json` | Node.js / 前端项目 |
| `next.config.*` | Next.js |
| `Cargo.toml` | Rust |
| `pyproject.toml` / `requirements.txt` | Python |
| `go.mod` | Go |
| `pom.xml` / `build.gradle` | Java |
| `*.sln` / `*.csproj` | C# / .NET |

### 3.3 Agent 团队配置 [P0]

**流程**：
1. 项目创建后进入「配置 Agent」步骤
2. 展示 8 个 Agent 角色卡片：Main、PM、Designer、Architect、CoderA、CoderB、DBA、DevOps
3. 用户勾选需要的 Agent（Main Agent 始终启用，不可取消）
4. 配置 OpenClaw 连接：
   - 连接方式：本地内嵌 / 远程 API
   - API Key（如远程）
   - 模型选择（如可选）
5. 确认配置

**默认配置**：
- 首次使用推荐启用：Main + PM + Architect + CoderA + CoderB（5 个）
- 提供预设模板：「全栈开发」「前端项目」「后端服务」

### 3.4 项目列表 [P0]

**视图**：
- 卡片视图（默认）：项目名、描述、标签、状态、最近活动时间
- 列表视图：紧凑展示

**操作**：
- 搜索：按项目名/描述搜索
- 筛选：按标签、状态（活跃/归档）、技术栈
- 排序：最近更新、创建时间、名称

### 3.5 项目详情页 [P0]

**Tab 结构**：

| Tab | 内容 |
|-----|------|
| 概览 | 项目信息、Agent 配置、技术栈、统计（对话数/任务数/代码量） |
| 对话 | 对话列表，支持新建对话、查看归档 |
| 任务 | 任务看板（待办/进行中/审核中/已完成） |
| 知识库 | 项目文档、RAG 索引管理（P1 功能） |
| 设置 | 项目信息编辑、Agent 配置修改、删除项目 |

---

## 4. 数据模型

```sql
-- 项目表
CREATE TABLE projects (
  id            TEXT PRIMARY KEY,          -- UUID
  name          TEXT NOT NULL,             -- 项目名称
  description   TEXT DEFAULT '',           -- 项目描述
  path          TEXT NOT NULL,             -- 本地路径
  git_url       TEXT,                      -- Git 远程地址（可选）
  tech_stack    TEXT DEFAULT '[]',         -- 技术栈 JSON 数组
  tags          TEXT DEFAULT '[]',         -- 标签 JSON 数组
  status        TEXT DEFAULT 'active',     -- active | archived
  agent_config  TEXT DEFAULT '{}',         -- Agent 配置 JSON
  openclaw_config TEXT DEFAULT '{}',       -- OpenClaw 连接配置 JSON
  created_at    INTEGER NOT NULL,          -- Unix timestamp
  updated_at    INTEGER NOT NULL           -- Unix timestamp
);

-- 项目统计缓存
CREATE TABLE project_stats (
  project_id    TEXT PRIMARY KEY REFERENCES projects(id),
  conversation_count INTEGER DEFAULT 0,
  task_count         INTEGER DEFAULT 0,
  agent_run_count    INTEGER DEFAULT 0,
  code_lines         INTEGER DEFAULT 0,
  updated_at    INTEGER NOT NULL
);
```

---

## 5. Tauri Commands 接口

```typescript
// 项目 CRUD
create_project(payload: CreateProjectInput): Promise<Project>
get_project(id: string): Promise<Project>
list_projects(filter?: ProjectFilter): Promise<Project[]>
update_project(id: string, payload: UpdateProjectInput): Promise<Project>
delete_project(id: string): Promise<void>
archive_project(id: string): Promise<void>

// 仓库导入
import_local_project(path: string): Promise<Project>
import_git_project(url: string, targetPath: string): Promise<ImportProgress>

// 技术栈识别
detect_tech_stack(path: string): Promise<TechStackResult>

// Agent 配置
update_agent_config(projectId: string, config: AgentConfig): Promise<void>
get_agent_config(projectId: string): Promise<AgentConfig>

// 项目统计
get_project_stats(projectId: string): Promise<ProjectStats>
```

---

## 6. UI 交互流程

### 6.1 新建项目

```
[项目列表页]
    │
    ├─ 点击「新建项目」
    │
    ▼
[新建项目弹窗/页面]
    ├─ 填写：名称、描述、标签
    ├─ 选择存储路径（默认值可改）
    │
    ▼
[Agent 配置步骤]
    ├─ 选择 Agent 角色（8 选 N，Main 必选）
    ├─ 选择预设模板 或 自定义
    ├─ 配置 OpenClaw 连接
    │
    ▼
[项目详情页] ← 创建完成
```

### 6.2 导入仓库

```
[项目列表页]
    │
    ├─ 点击「导入项目」
    │
    ▼
[选择导入方式]
    ├─ 本地目录
    │   ├─ 打开文件选择器
    │   ├─ 选择目录
    │   ├─ 自动识别技术栈
    │   └─ 确认导入
    │
    └─ Git 仓库
        ├─ 输入 Git URL
        ├─ 选择克隆目录
        ├─ 进度条展示克隆进度
        ├─ 自动识别技术栈
        └─ 确认导入
```

---

## 7. 边界条件与异常处理

| 场景 | 处理方式 |
|------|---------|
| 项目名重复 | 提示名称已存在，建议后缀编号 |
| 本地路径不存在 | 自动创建（需确认） |
| 本地路径已有文件 | 警告用户，提供合并/覆盖/取消选项 |
| Git URL 无效 | 提示 URL 格式错误 |
| Git 克隆失败（网络） | 提示网络错误，支持重试 |
| Git 克隆失败（权限） | 提示认证信息，支持输入凭据 |
| 目录无写权限 | 提示权限不足，建议更换路径 |
| 磁盘空间不足 | 检测并提前警告 |
| 技术栈识别失败 | 标记为「未知」，允许用户手动选择 |

---

## 8. 验收标准

### P0 验收（MVP）
- [ ] 能创建新项目，信息完整保存到 SQLite
- [ ] 能通过本地路径导入已有代码目录
- [ ] 能通过 Git URL 克隆远程仓库
- [ ] 技术栈自动识别至少支持 5 种（Node/Next/Rust/Python/Go）
- [ ] Agent 配置可保存和修改，Main Agent 不可取消
- [ ] 项目列表支持卡片展示、搜索、筛选
- [ ] 项目详情页展示概览信息
- [ ] 项目删除需二次确认
- [ ] 所有异常场景有友好提示

### P1 验收
- [ ] 项目标签管理
- [ ] 项目归档功能
- [ ] 项目间快速切换
- [ ] 项目统计信息展示

---

*文档维护者：TeamClaw 项目组*
