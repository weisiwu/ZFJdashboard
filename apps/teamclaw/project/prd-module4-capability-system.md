# PRD — 模块4：能力系统（Capability System）

> 版本：V1.0  
> 最后更新：2026-04-17  
> 优先级：P1（增强功能）

---

## 1. 功能概述

能力系统是 TeamClaw 多 Agent 协作的底层基座。它定义了每个 Agent「能做什么」——包括 Agent 角色的身份、职责边界、可用工具、通信协议和 Prompt 模板。能力系统为模块 2（多 Agent 编排）和模块 3（任务体系）提供 Agent 实例化与调用的标准接口，确保 Agent 间协作有规可循、有迹可循。

本模块的核心目标：
- **角色标准化**：8 种 Agent 角色（Main、PM、Designer、Architect、CoderA、CoderB、DBA、DevOps）拥有统一的角色定义结构，可扩展
- **能力可发现**：每个 Agent 的能力以能力卡片（Capability Card）形式注册到全局能力注册中心，其他 Agent 可查询并调用
- **通信规范化**：Agent 间消息传递、事件订阅遵循统一的通信协议，支持同步 invoke 和异步 hook 两种模式
- **Prompt 可管理**：Agent 的系统提示词、角色设定、上下文模板集中管理，支持版本控制和热更新
- **权限可控制**：能力矩阵定义每个 Agent 角色可调用哪些能力和工具，防止越权操作
- **运行时可追踪**：Agent 执行上下文贯穿整个生命周期，支持状态快照、异常恢复和调试回放

---

## 2. 核心概念

### 2.1 Agent 角色（Agent Role）

Agent 角色是能力系统的基础单元。每个角色定义了一类 Agent 的身份标识、职责范围和可用能力集合。角色是静态定义的，Agent 实例是运行时创建的。

```
AgentRole (静态定义)          AgentInstance (运行时)
┌──────────────────┐         ┌──────────────────┐
│ role: 'coderA'   │ ──创建──►│ instance_id: uuid │
│ display_name     │         │ role: 'coderA'   │
│ description      │         │ status: running   │
│ capabilities[]   │         │ context: {...}    │
│ permissions[]    │         │ created_at        │
│ prompt_template  │         └──────────────────┘
│ tool_bindings[]  │
│ constraints[]    │
└──────────────────┘
```

### 2.2 能力卡片（Capability Card）

能力卡片是 Agent 能力的最小描述单元。一个 Agent 角色可以拥有多张能力卡片，每张卡片描述一个原子能力。

```typescript
interface CapabilityCard {
  id: string;                  // 能力唯一标识，如 'code_generation'
  name: string;                // 能力名称，如 '代码生成'
  description: string;         // 能力描述
  category: CapabilityCategory;// 能力分类
  input_schema: JSONSchema;    // 输入参数定义
  output_schema: JSONSchema;   // 输出结果定义
  version: string;             // 能力版本号，如 '1.2.0'
  owner_roles: AgentRole[];    // 拥有此能力的角色列表
  required_tools: string[];    // 执行此能力需要的工具列表
  timeout: number;             // 执行超时时间（秒）
  tags: string[];              // 标签，用于检索
}
```

### 2.3 能力注册中心（Capability Registry）

能力注册中心是全局单例服务，负责维护所有已注册能力的索引。Agent 启动时注册自身能力，其他 Agent 通过注册中心发现和调用能力。

```
┌─────────────────────────────────────────────┐
│            Capability Registry               │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │  能力索引（capability_index）        │    │
│  │  code_generation   → CoderA, CoderB │    │
│  │  prd_writing       → PM             │    │
│  │  ui_design         → Designer       │    │
│  │  architecture      → Architect      │    │
│  │  schema_design     → DBA            │    │
│  │  deployment        → DevOps         │    │
│  │  task_orchestration→ Main           │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │  权限矩阵（permission_matrix）       │    │
│  │  CoderA  → [code_generation, ...]   │    │
│  │  CoderB  → [code_generation, ...]   │    │
│  │  PM      → [prd_writing, ...]       │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

### 2.4 通信协议（Communication Protocol）

Agent 间通信遵循统一的消息格式，支持两种调用模式：

| 模式 | 标识 | 说明 | 场景 |
|------|------|------|------|
| 同步调用 | `invoke` | 调用方等待返回结果 | CoderA 调用 DBA 查询表结构 |
| 异步钩子 | `hook` | 调用方不等待，被调用方自行处理 | 任务完成后通知 DevOps 执行部署 |

### 2.5 Prompt 模板（Prompt Template）

Prompt 模板是 Agent 的"灵魂"，定义了 Agent 的行为模式、输出规范和上下文注入方式。

| 模板类型 | 标识 | 说明 |
|---------|------|------|
| 系统提示词 | `system_prompt` | Agent 身份、职责、行为准则 |
| 角色设定 | `persona` | Agent 的性格特征、沟通风格 |
| 上下文模板 | `context_template` | 动态注入的项目信息、任务信息、依赖产物 |
| 输出规范 | `output_format` | Agent 输出的格式要求（如 Markdown、JSON） |
| 工具说明 | `tool_instruction` | Agent 可用工具的使用说明 |

---

## 3. 用户故事

| 编号 | 用户故事 | 优先级 |
|------|---------|--------|
| US-01 | 作为用户，我想看到每个 Agent 角色的职责和能力说明 | P1 |
| US-02 | 作为用户，我想查看当前项目中已激活的 Agent 角色列表 | P1 |
| US-03 | 作为用户，我想为项目自定义 Agent 的 Prompt 模板（如增加特定技术栈要求） | P1 |
| US-04 | 作为用户，我想查看 Agent 间的调用关系和通信日志 | P1 |
| US-05 | 作为用户，我想在 Agent 执行过程中查看其上下文信息（当前任务、依赖产物等） | P1 |
| US-06 | 作为用户，我想启用/禁用某些 Agent 能力（如禁止 Agent 直接执行部署） | P1 |
| US-07 | 作为系统管理员，我想配置 Agent 的能力权限矩阵 | P1 |
| US-08 | 作为用户，我想回放 Agent 的执行上下文用于调试 | P2 |
| US-09 | 作为高级用户，我想创建自定义 Agent 角色（如 CodeReviewer） | P2 |
| US-10 | 作为用户，我想导入/导出 Agent 配置（Prompt、权限等） | P2 |
| US-11 | 作为用户，我想查看 Agent 的 Token 消耗统计（按角色、按任务） | P2 |
| US-12 | 作为开发者，我想通过 API 注册自定义能力插件 | P3 |

---

## 4. 功能需求清单

### 4.1 Agent 角色定义与管理 [P1]

**内置角色定义**：

| 角色 | 标识 | 职责 | 核心能力 |
|------|------|------|---------|
| 主管 | `main` | 任务接收、拆解、调度、汇总提问 | task_orchestration, question_aggregation, progress_monitoring |
| 产品经理 | `pm` | 需求分析、PRD 编写 | requirement_analysis, prd_writing, user_story_generation |
| 设计师 | `designer` | UI/UX 设计、原型制作 | ui_design, prototype_generation, style_guide_creation |
| 架构师 | `architect` | 技术选型、架构设计、API 设计 | architecture_design, api_design, tech_stack_selection |
| 前端开发 | `coderA` | 前端代码开发 | code_generation, component_development, frontend_testing |
| 后端开发 | `coderB` | 后端代码开发 | code_generation, api_implementation, backend_testing |
| 数据库管理员 | `dba` | 数据库设计、迁移脚本 | schema_design, migration_creation, query_optimization |
| 运维工程师 | `devops` | 部署配置、CI/CD、环境管理 | deployment_config, cicd_setup, environment_management |

**角色定义结构**：
```typescript
interface AgentRoleDefinition {
  role: AgentRole;
  display_name: string;
  emoji: string;                      // 如 🏗️
  description: string;
  responsibilities: string[];
  capabilities: string[];             // 能力 ID 列表
  permissions: PermissionSet;
  constraints: Constraint[];
  prompt_config: PromptConfig;
  tool_bindings: ToolBinding[];
  metadata: RoleMetadata;
}

interface PermissionSet {
  can_invoke: AgentRole[];            // 可调用的 Agent 角色
  can_be_invoked_by: AgentRole[];     // 可被哪些角色调用
  allowed_tools: string[];
  denied_tools: string[];
  max_concurrent_instances: number;
  requires_user_confirmation: string[];// 需要用户确认的操作
}
```

**角色管理操作**：
- 查看所有角色定义（只读）
- 查看角色详情（能力、权限、约束）
- 项目级角色配置覆盖（如为特定项目修改 PM 的 Prompt）
- 角色启用/禁用

### 4.2 能力注册与发现机制 [P1]

**能力分类体系**：

| 分类 | 标识 | 说明 |
|------|------|------|
| 分析能力 | `analysis` | 需求分析、技术分析、风险评估 |
| 设计能力 | `design` | UI 设计、架构设计、数据建模 |
| 生成能力 | `generation` | 代码生成、文档生成、配置生成 |
| 执行能力 | `execution` | 代码运行、测试执行、部署执行 |
| 审核能力 | `review` | 代码审查、设计审查、PRD 审核 |
| 通信能力 | `communication` | 问题提问、进度汇报、结果汇总 |
| 协调能力 | `coordination` | 任务调度、依赖管理、冲突解决 |

**注册流程**：
```
Agent 实例启动
    ↓
读取角色定义中的 capabilities 列表
    ↓
向 Capability Registry 注册每张能力卡片
    ↓
Registry 校验能力定义合法性
    ↓
校验通过 → 加入能力索引，通知其他 Agent
校验失败 → 拒绝注册，返回错误信息
    ↓
Agent 就绪，可接受能力调用
```

**发现接口**：
```typescript
query_capability(capabilityId: string): CapabilityCard
query_capabilities_by_role(role: AgentRole): CapabilityCard[]
query_capabilities_by_category(category: string): CapabilityCard[]
search_capabilities(keyword: string): CapabilityCard[]
get_capability_dependency_graph(): CapabilityGraph
```

**能力健康检查**：
- 每个 Agent 实例定期（每 30 秒）向 Registry 发送心跳
- 心跳超时（90 秒无响应）→ 标记该 Agent 的能力为「不可用」
- 能力恢复时自动重新标记为「可用」

### 4.3 Agent 间通信协议 [P1]

**消息格式**：
```typescript
interface AgentMessage {
  id: string;
  from: { instance_id: string; role: AgentRole };
  to: { instance_id?: string; role?: AgentRole };
  type: MessageType;
  payload: AgentMessagePayload;
  context: {
    task_id: string;
    conversation_id: string;
    correlation_id?: string;
  };
  timestamp: number;
  priority: 'low' | 'normal' | 'high' | 'urgent';
  ttl: number;
}

type MessageType =
  | 'invoke_request' | 'invoke_response' | 'invoke_error'
  | 'hook_event' | 'hook_ack'
  | 'status_update' | 'progress_report'
  | 'question_broadcast' | 'artifact_share' | 'context_sync';
```

**invoke（同步调用）流程**：
```
CoderA ── invoke_request ──────► DBA
         { capability: 'schema_query', params: { table: 'users' } }
                                   [DBA 执行]
CoderA ◄── invoke_response ──── DBA
         { result: { columns: [...] } }
```

**hook（异步钩子）流程**：
```
CoderA ── hook_event ──────► DevOps
         { event: 'code_completed', params: { files: [...] } }
CoderA ◄── hook_ack ──────── DevOps
         { status: 'received' }
                  [DevOps 异步处理]
CoderA ◄── status_update ── DevOps { status: 'deployed' }
```

**事件订阅**：
```typescript
interface EventSubscription {
  id: string;
  subscriber_instance_id: string;
  event_types: MessageType[];
  filter?: { from_roles?: AgentRole[]; task_ids?: string[] };
}
```

**消息队列管理**：
- 每个 Agent 实例拥有独立的消息队列，按优先级排序
- 队列容量上限 1000 条，超出后丢弃低优先级消息并告警
- 消息 TTL 到期后自动丢弃

### 4.4 能力调用接口（invoke/hook 机制） [P1]

**调用接口**：
```typescript
interface InvokeRequest {
  capability_id: string;
  target_role?: AgentRole;
  target_instance_id?: string;
  params: Record<string, any>;
  timeout?: number;        // 默认 60 秒
  priority?: MessagePriority;
}

interface InvokeResult {
  success: boolean;
  data?: any;
  error?: AgentError;
  latency_ms: number;
  from_instance: string;
}

interface HookEvent {
  event_type: string;
  capability_id?: string;
  payload: Record<string, any>;
  broadcast: boolean;
  target_roles?: AgentRole[];
}
```

**调用路由策略**：

| 策略 | 标识 | 说明 | 适用场景 |
|------|------|------|---------|
| 角色路由 | `by_role` | 按角色找到空闲实例 | 通用场景 |
| 实例直连 | `by_instance` | 指定实例 ID | 需要特定上下文 |
| 负载均衡 | `least_busy` | 选择任务最少的实例 | 多实例并行 |

### 4.5 Agent Prompt 模板管理 [P1]

**Prompt 配置结构**：
```typescript
interface PromptConfig {
  system_prompt: PromptTemplate;
  persona: PromptTemplate;
  context_template: PromptTemplate;
  output_format: PromptTemplate;
  tool_instruction: PromptTemplate;
  guardrails: PromptTemplate;
}

interface PromptTemplate {
  id: string;
  version: string;           // 语义化版本
  content: string;           // 支持 {{variable}} 插值
  variables: TemplateVariable[];
  language: string;
  is_active: boolean;
  created_at: number;
  updated_at: number;
}
```

**模板变量插值示例**：
```
原始模板：
你是 {{project_name}} 项目的 {{role_display_name}}（{{role_emoji}}）。
项目描述：{{project_description}}
技术栈：{{tech_stack}}

插值后：
你是 电商后台系统 项目的前端开发（💻）。
项目描述：一个全栈电商管理后台，包含商品管理、订单管理等模块
技术栈：React + TypeScript + TailwindCSS + Node.js + PostgreSQL
```

**Prompt 版本管理**：
- 每次修改自动创建新版本，旧版本保留
- 支持版本回退和 diff 对比
- 遵循语义化版本（SemVer）

**项目级 Prompt 覆盖**：
```
系统默认 Prompt（全局）→ 项目级 Prompt 覆盖 → 任务级 Prompt 增强
最终 Prompt = 基础模板 + 项目覆盖 + 任务增强
```

### 4.6 Agent 执行上下文与状态追踪 [P1]

**执行上下文结构**：
```typescript
interface AgentExecutionContext {
  instance_id: string;
  role: AgentRole;
  task_id: string;
  task_description: string;
  conversation_id: string;
  project_id: string;

  status: AgentStatus;
  // initializing | ready | executing | waiting_response
  // waiting_user | paused | completed | failed | terminated
  progress: number;           // 0-100

  input_context: {
    artifacts: ArtifactReference[];
    messages: ContextMessage[];
    user_instructions: string[];
  };

  output_state: {
    generated_artifacts: ArtifactReference[];
    pending_questions: string[];
    errors: AgentError[];
  };

  resource_usage: {
    total_tokens: number;
    input_tokens: number;
    output_tokens: number;
    api_calls: number;
  };

  snapshots: ContextSnapshot[];
}
```

**状态快照机制**：

| 时机 | 类型 | 说明 |
|------|------|------|
| Agent 开始执行 | `auto` | 记录初始状态 |
| invoke 调用前/后 | `auto` | 记录调用边界状态 |
| 用户发送补充指令 | `auto` | 记录用户干预点 |
| Agent 遇到错误 | `error` | 记录错误现场 |
| 用户手动触发 | `manual` | 手动保存检查点 |

### 4.7 能力权限与约束 [P1]

**权限矩阵**：

```
              Main  PM  Designer  Architect  CoderA  CoderB  DBA  DevOps
Main           ✅    ✅    ✅        ✅        ✅      ✅      ✅    ✅
PM             ❌    ❌    ✅        ✅        ❌      ❌      ❌    ❌
Designer       ❌    ❌    ❌        ✅        ❌      ❌      ❌    ❌
Architect      ❌    ❌    ❌        ❌        ❌      ❌      ✅    ❌
CoderA         ❌    ❌    ✅        ❌        ❌      ❌      ✅    ❌
CoderB         ❌    ❌    ❌        ✅        ❌      ❌      ✅    ✅
DBA            ❌    ❌    ❌        ❌        ❌      ❌      ❌    ❌
DevOps         ❌    ❌    ❌        ❌        ❌      ❌      ❌    ❌

✅ = 可调用    ❌ = 不可调用
```

> 注：Main Agent 作为主管角色，可调用所有角色。具体权限可在项目级配置中覆盖。

**工具权限矩阵**：

| 工具 | Main | PM | Designer | Architect | CoderA | CoderB | DBA | DevOps |
|------|------|-----|----------|-----------|--------|--------|-----|--------|
| 文件读取 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 文件写入 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 代码执行 | ⚠️ | ❌ | ❌ | ❌ | ⚠️ | ⚠️ | ⚠️ | ⚠️ |
| 数据库操作 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ⚠️ |
| 部署操作 | ⚠️ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 网络请求 | ⚠️ | ❌ | ❌ | ❌ | ⚠️ | ⚠️ | ❌ | ⚠️ |

> ⚠️ = 需要用户确认后才能执行

**约束条件定义**：

| 约束类型 | 说明 | 默认值 |
|---------|------|-------|
| 超时 | 单次能力调用最大时长 | 60 秒 |
| 重试 | 失败后最大重试次数 | 3 次 |
| 文件范围 | 允许操作的目录范围 | 项目目录内 |
| Token 预算 | 单次任务最大 Token 用量 | 50,000 |
| 并发限制 | 同一角色最大并行实例数 | 4 |

### 4.8 能力的热加载与配置 [P1]

**热加载场景**：
1. 运行时更新 Agent Prompt 模板（无需重启）
2. 运行时调整能力权限配置
3. 运行时启用/禁用特定能力
4. 运行时更新工具绑定配置

**热加载流程**：
```
用户修改配置（Prompt/权限/工具）
    ↓
配置版本号递增
    ↓
写入配置存储（SQLite）
    ↓
通过事件总线广播配置变更事件
    ↓
运行中的 Agent 收到变更通知
    ↓
Agent 在下次任务开始时应用新配置
    ↓
当前正在执行的任务不受影响
```

**配置变更通知**：
```typescript
interface ConfigChangeEvent {
  config_type: 'prompt' | 'permission' | 'tool_binding' | 'constraint';
  role: AgentRole;
  project_id?: string;               // 项目级变更时指定
  old_version: string;
  new_version: string;
  changed_fields: string[];
  effective_at: number;              // 生效时间戳
}
```

**配置回滚**：
- 所有配置变更保留历史版本
- 支持一键回滚到指定版本
- 回滚同样通过事件广播生效

---

## 5. 数据模型

```sql
-- Agent 角色定义表
CREATE TABLE agent_roles (
  id              TEXT PRIMARY KEY,              -- 角色标识（main, pm, designer...）
  display_name    TEXT NOT NULL,                 -- 显示名称
  emoji           TEXT NOT NULL,                 -- 角色图标
  description     TEXT NOT NULL,                 -- 角色描述
  responsibilities TEXT NOT NULL,                -- 职责清单 JSON
  capabilities    TEXT NOT NULL,                 -- 能力 ID 列表 JSON
  permissions     TEXT NOT NULL,                 -- 权限集合 JSON
  constraints     TEXT NOT NULL,                 -- 约束条件 JSON
  tool_bindings   TEXT NOT NULL,                 -- 工具绑定 JSON
  is_builtin      INTEGER DEFAULT 1,             -- 是否为内置角色
  is_active       INTEGER DEFAULT 1,             -- 是否启用
  created_at      INTEGER NOT NULL,
  updated_at      INTEGER NOT NULL
);

-- 能力卡片注册表
CREATE TABLE capability_cards (
  id              TEXT PRIMARY KEY,              -- 能力 ID（如 code_generation）
  name            TEXT NOT NULL,                 -- 能力名称
  description     TEXT NOT NULL,                 -- 能力描述
  category        TEXT NOT NULL,                 -- 能力分类
  input_schema    TEXT NOT NULL,                 -- 输入参数 JSON Schema
  output_schema   TEXT NOT NULL,                 -- 输出参数 JSON Schema
  version         TEXT NOT NULL,                 -- 版本号
  owner_roles     TEXT NOT NULL,                 -- 拥有此能力的角色 JSON
  required_tools  TEXT NOT NULL,                 -- 需要的工具列表 JSON
  timeout         INTEGER DEFAULT 60,            -- 超时时间（秒）
  tags            TEXT DEFAULT '[]',             -- 标签 JSON
  is_active       INTEGER DEFAULT 1,
  created_at      INTEGER NOT NULL,
  updated_at      INTEGER NOT NULL
);

-- Agent 实例表
CREATE TABLE agent_instances (
  id              TEXT PRIMARY KEY,              -- 实例 UUID
  role            TEXT NOT NULL,                 -- 角色标识
  project_id      TEXT NOT NULL,
  conversation_id TEXT,
  task_id         TEXT,                          -- 当前执行的任务 ID
  session_id      TEXT NOT NULL,                 -- 会话 ID
  status          TEXT DEFAULT 'initializing',   -- 实例状态
  context         TEXT,                          -- 执行上下文 JSON
  progress        INTEGER DEFAULT 0,             -- 进度 0-100
  total_tokens    INTEGER DEFAULT 0,             -- 累计 Token
  input_tokens    INTEGER DEFAULT 0,
  output_tokens   INTEGER DEFAULT 0,
  api_calls       INTEGER DEFAULT 0,
  started_at      INTEGER NOT NULL,
  updated_at      INTEGER NOT NULL,
  completed_at    INTEGER,
  FOREIGN KEY (role) REFERENCES agent_roles(id),
  FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE INDEX idx_agent_instances_role ON agent_instances(role);
CREATE INDEX idx_agent_instances_status ON agent_instances(status);
CREATE INDEX idx_agent_instances_task ON agent_instances(task_id);

-- Prompt 模板表
CREATE TABLE prompt_templates (
  id              TEXT PRIMARY KEY,              -- 模板 UUID
  role            TEXT NOT NULL,                 -- 所属角色
  template_type   TEXT NOT NULL,                 -- system_prompt | persona | context_template | output_format | tool_instruction | guardrails
  version         TEXT NOT NULL,                 -- 版本号
  content         TEXT NOT NULL,                 -- 模板内容
  variables       TEXT DEFAULT '[]',             // 变量定义 JSON
  language        TEXT DEFAULT 'zh-CN',          -- 语言
  is_active       INTEGER DEFAULT 0,             -- 是否为当前激活版本
  project_id      TEXT,                          -- 项目级覆盖时非空
  created_at      INTEGER NOT NULL,
  updated_at      INTEGER NOT NULL,
  FOREIGN KEY (role) REFERENCES agent_roles(id),
  UNIQUE(role, template_type, version, project_id)
);

CREATE INDEX idx_prompt_templates_role_type ON prompt_templates(role, template_type);
CREATE INDEX idx_prompt_templates_active ON prompt_templates(role, template_type, is_active);

-- 项目级 Prompt 覆盖表
CREATE TABLE project_prompt_overrides (
  id              TEXT PRIMARY KEY,
  project_id      TEXT NOT NULL,
  role            TEXT NOT NULL,
  template_type   TEXT NOT NULL,
  template_id     TEXT NOT NULL,                 -- 引用的模板 ID
  created_at      INTEGER NOT NULL,
  FOREIGN KEY (project_id) REFERENCES projects(id),
  FOREIGN KEY (template_id) REFERENCES prompt_templates(id),
  UNIQUE(project_id, role, template_type)
);

-- Agent 通信日志表
CREATE TABLE agent_communications (
  id              TEXT PRIMARY KEY,              -- 消息 UUID
  message_id      TEXT NOT NULL,                 -- 原始消息 ID
  from_instance   TEXT NOT NULL,                 -- 发送方实例 ID
  from_role       TEXT NOT NULL,
  to_instance     TEXT,                          -- 接收方实例 ID
  to_role         TEXT,                          // 接收方角色
  message_type    TEXT NOT NULL,                 -- 消息类型
  capability_id   TEXT,                          // 调用的能力 ID
  action          TEXT,                          // 具体动作
  params_summary  TEXT,                          // 参数摘要（脱敏）
  result_status   TEXT,                          -- success | error | timeout | pending
  latency_ms      INTEGER,                       // 调用耗时
  error_message   TEXT,                          // 错误信息
  task_id         TEXT,
  conversation_id TEXT,
  timestamp       INTEGER NOT NULL,
  FOREIGN KEY (from_instance) REFERENCES agent_instances(id)
);

CREATE INDEX idx_comm_from ON agent_communications(from_instance);
CREATE INDEX idx_comm_to ON agent_communications(to_instance);
CREATE INDEX idx_comm_task ON agent_communications(task_id);
CREATE INDEX idx_comm_type ON agent_communications(message_type);
CREATE INDEX idx_comm_time ON agent_communications(timestamp);

-- 执行上下文快照表
CREATE TABLE context_snapshots (
  id              TEXT PRIMARY KEY,
  agent_instance_id TEXT NOT NULL,
  task_id         TEXT NOT NULL,
  snapshot_type   TEXT NOT NULL,                 -- auto | manual | error
  context_state   TEXT NOT NULL,                 -- 序列化的上下文 JSON
  checkpoint_name TEXT,
  token_usage     INTEGER DEFAULT 0,
  created_at      INTEGER NOT NULL,
  FOREIGN KEY (agent_instance_id) REFERENCES agent_instances(id),
  FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE INDEX idx_snapshots_instance ON context_snapshots(agent_instance_id);
CREATE INDEX idx_snapshots_task ON context_snapshots(task_id);

-- 事件订阅表
CREATE TABLE event_subscriptions (
  id              TEXT PRIMARY KEY,
  subscriber_instance_id TEXT NOT NULL,
  event_types     TEXT NOT NULL,                 -- 订阅的事件类型 JSON
  filter_criteria TEXT,                          -- 过滤条件 JSON
  is_active       INTEGER DEFAULT 1,
  created_at      INTEGER NOT NULL,
  FOREIGN KEY (subscriber_instance_id) REFERENCES agent_instances(id)
);

-- 能力权限配置表（项目级覆盖）
CREATE TABLE capability_permission_overrides (
  id              TEXT PRIMARY KEY,
  project_id      TEXT NOT NULL,
  from_role       TEXT NOT NULL,
  to_role         TEXT NOT NULL,
  is_allowed      INTEGER NOT NULL,              -- 1=允许, 0=禁止
  created_at      INTEGER NOT NULL,
  FOREIGN KEY (project_id) REFERENCES projects(id),
  UNIQUE(project_id, from_role, to_role)
);

-- 配置变更历史表
CREATE TABLE config_change_history (
  id              TEXT PRIMARY KEY,
  config_type     TEXT NOT NULL,                 -- prompt | permission | tool_binding | constraint
  role            TEXT NOT NULL,
  project_id      TEXT,
  old_version     TEXT,
  new_version     TEXT,
  changed_fields  TEXT,                          -- 变更字段 JSON
  operator        TEXT NOT NULL,                 -- user | system
  created_at      INTEGER NOT NULL
);
```

---

## 6. Tauri Commands 接口

```typescript
// ===== Agent 角色管理 =====
list_agent_roles(): Promise<AgentRoleDefinition[]>
get_agent_role(role: AgentRole): Promise<AgentRoleDefinition>
toggle_agent_role(role: AgentRole, active: boolean): Promise<void>

// ===== 能力注册与发现 =====
list_capabilities(filter?: CapabilityFilter): Promise<CapabilityCard[]>
get_capability(capabilityId: string): Promise<CapabilityCard>
search_capabilities(keyword: string): Promise<CapabilityCard[]>
get_capability_graph(): Promise<CapabilityGraph>
get_capability_health(): Promise<CapabilityHealthStatus[]>

// ===== 能力调用 =====
invoke_capability(request: InvokeRequest): Promise<InvokeResult>
emit_hook(event: HookEvent): Promise<HookAck[]>
get_invocation_logs(filter: InvocationLogFilter): Promise<CapabilityInvocationLog[]>

// ===== Prompt 模板管理 =====
list_prompt_templates(role: AgentRole): Promise<PromptTemplate[]>
get_active_prompt(role: AgentRole, type: TemplateType): Promise<PromptTemplate>
create_prompt_template(template: CreatePromptInput): Promise<PromptTemplate>
update_prompt_template(templateId: string, content: string): Promise<PromptTemplate>
activate_prompt_version(templateId: string): Promise<void>
diff_prompt_versions(templateId: string, v1: string, v2: string): Promise<string>
preview_prompt_interpolation(templateId: string, variables: Record<string, string>): Promise<string>
estimate_prompt_tokens(templateId: string): Promise<number>

// ===== 项目级 Prompt 覆盖 =====
set_project_prompt_override(projectId: string, role: AgentRole, type: TemplateType, templateId: string): Promise<void>
remove_project_prompt_override(projectId: string, role: AgentRole, type: TemplateType): Promise<void>
get_project_prompt_config(projectId: string): Promise<ProjectPromptConfig>

// ===== 执行上下文 =====
get_agent_context(instanceId: string): Promise<AgentExecutionContext>
list_agent_instances(filter: AgentInstanceFilter): Promise<AgentInstance[]>
get_instance_snapshots(instanceId: string): Promise<ContextSnapshot[]>
restore_context_snapshot(snapshotId: string): Promise<void>

// ===== 权限管理 =====
get_permission_matrix(): Promise<PermissionMatrix>
update_project_permission(projectId: string, fromRole: AgentRole, toRole: AgentRole, allowed: boolean): Promise<void>
get_project_permissions(projectId: string): Promise<ProjectPermissionConfig>

// ===== 配置变更 =====
get_config_change_history(role?: AgentRole, configType?: string): Promise<ConfigChange[]>
rollback_config(changeId: string): Promise<void>

// ===== 通信日志 =====
get_communication_logs(filter: CommLogFilter): Promise<AgentCommunication[]>
export_communication_logs(conversationId: string, format: 'json' | 'csv'): Promise<string>
```

---

## 7. UI 交互流程

### 7.1 Agent 角色浏览流程

```
[项目设置 → Agent 能力 Tab]
    │
    ├─ 角色卡片网格
    │   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
    │   │ 🧠 Main  │ │ 📋 PM    │ │ 🎨 Design│ │ 🏗️ Arch  │
    │   │ 主管     │ │ 产品经理  │ │ 设计师    │ │ 架构师    │
    │   │ 7 项能力  │ │ 3 项能力  │ │ 3 项能力  │ │ 3 项能力  │
    │   │ 🟢 已启用 │ │ 🟢 已启用 │ │ 🟢 已启用 │ │ 🟢 已启用 │
    │   └──────────┘ └──────────┘ └──────────┘ └──────────┘
    │   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
    │   │ 💻 CoderA│ │ 💻 CoderB│ │ 🗄️ DBA   │ │ 🚀 DevOps│
    │   │ 前端开发  │ │ 后端开发  │ │ 数据库    │ │ 运维     │
    │   │ 3 项能力  │ │ 3 项能力  │ │ 3 项能力  │ │ 3 项能力  │
    │   │ 🟢 已启用 │ │ 🟢 已启用 │ │ 🟢 已启用 │ │ 🟢 已启用 │
    │   └──────────┘ └──────────┘ └──────────┘ └──────────┘
    │
    └─ 点击角色卡片
        ▼
    [角色详情页]
        ├─ 📋 基本信息（名称、描述、职责）
        ├─ ⚡ 能力列表（能力卡片列表）
        ├─ 🔐 权限矩阵（可视化矩阵图）
        ├─ 📝 Prompt 配置（查看/编辑）
        └─ 🔧 工具绑定（工具列表）
```

### 7.2 Prompt 模板编辑流程

```
[角色详情页 → Prompt 配置]
    │
    ├─ 模板类型 Tab
    │   [系统提示词] [角色设定] [上下文模板] [输出规范] [工具说明] [安全约束]
    │
    ├─ 版本列表
    │   v1.2.0 (当前) ✅  [查看] [编辑]
    │   v1.1.0            [查看] [激活] [对比]
    │   v1.0.0            [查看] [激活] [对比]
    │
    ├─ 编辑器区域
    │   ┌──────────────────────────────────────┐
    │   │ 编辑器（Markdown + 变量高亮）         │
    │   │                                      │
    │   │ 你是 {{project_name}} 的             │
    │   │ {{role_display_name}}...             │
    │   │                                      │
    │   ├──────────────────────────────────────┤
    │   │ 变量面板                             │
    │   │ {{project_name}}    项目配置         │
    │   │ {{tech_stack}}      项目配置         │
    │   │ {{role_display_name}} Agent 配置     │
    │   ├──────────────────────────────────────┤
    │   │ [预览插值效果]  [Token 估算: ~450]   │
    │   └──────────────────────────────────────┘
    │
    └─ 操作
        [保存新版本] [取消]
```

### 7.3 执行上下文查看流程

```
[任务执行中 → 点击 Agent 头像]
    │
    ▼
[Agent 执行上下文面板]（侧边抽屉）
    │
    ├─ 状态卡片
    │   角色、状态、进度条、运行时间
    │
    ├─ 资源使用
    │   Token 用量、API 调用次数、工具调用次数
    │
    ├─ 调用历史（时间线）
    │   invoke → DBA ✅ 120ms
    │   invoke → Architect ✅ 89ms
    │   hook → DevOps ✅ 已确认
    │
    ├─ 输入上下文
    │   依赖产物列表、用户指令列表
    │
    ├─ 输出状态
    │   已生成产物、待回答问题、错误列表
    │
    └─ 状态快照
        [保存快照] [查看历史快照]
```

### 7.4 通信日志查看流程

```
[项目设置 → 通信日志 Tab]
    │
    ├─ 筛选栏
    │   [消息类型 ▼] [发送方 ▼] [接收方 ▼] [时间范围]
    │   [搜索框]
    │
    ├─ 日志列表
    │   ┌─────────────────────────────────────────┐
    │   │ 10:32:01 CoderA → DBA    invoke ✅ 120ms │
    │   │ 10:32:05 CoderA → Arch   invoke ✅ 89ms  │
    │   │ 10:32:12 CoderA → DevOps hook   ✅ 已确认 │
    │   │ 10:32:18 Main ← CoderA   progress 80%    │
    │   └─────────────────────────────────────────┘
    │
    ├─ 点击日志条目 → 展开详情
    │   消息 ID、完整参数、返回结果
    │
    └─ [导出 JSON] [导出 CSV]
```

### 7.5 权限矩阵配置流程

```
[项目设置 → 权限矩阵 Tab]
    │
    ├─ 权限矩阵热力图
    │            Main  PM  Des  Arch  CA  CB  DBA  Dev
    │   Main      🟢   🟢  🟢   🟢   🟢  🟢  🟢   🟢
    │   PM        🔴   🔴  🟢   🟢   🔴  🔴  🔴   🔴
    │   Designer  🔴   🔴  🔴   🟢   🔴  🔴  🔴   🔴
    │   ...
    │
    ├─ 点击单元格 → 切换权限
    │   🟢（允许）→ 🔴（禁止）→ 🟡（需确认）
    │
    ├─ 工具权限配置
    │   [展开工具权限详情]
    │
    └─ [恢复默认] [导出配置]
```

---

## 8. 边界条件与异常处理

| 场景 | 处理方式 |
|------|---------|
| invoke 目标 Agent 不可用 | 等待队列最多 30 秒，超时返回错误，建议重试或跳过 |
| invoke 调用超时 | 返回超时错误，调用方可配置是否重试（默认重试 1 次） |
| hook 广播无订阅者 | 静默丢弃，记录日志 |
| 消息队列溢出 | 丢弃低优先级消息，向 Main Agent 报警 |
| 能力注册时 ID 冲突 | 拒绝注册，提示能力 ID 已存在 |
| Prompt 模板变量缺失 | 使用默认值填充，标记为「部分插值」，在日志中告警 |
| Prompt 模板超长（超过模型上下文窗口） | 截断低优先级部分，在日志中告警 |
| 权限配置循环依赖（A→B→C→A） | 检测并拒绝，提示移除循环依赖 |
| 配置热加载时 Agent 正在执行 | 不中断当前任务，下次任务开始时生效 |
| Agent 实例异常崩溃 | 自动创建新实例，从最近快照恢复上下文 |
| 多个项目同时修改同一角色配置 | 以最后提交为准，版本号冲突时提示 |
| 能力调用链路过深（>5 层） | 强制中断，防止递归调用 |

---

## 9. 性能与优化

| 指标 | 目标 | 优化措施 |
|------|------|---------|
| 能力注册延迟 | < 50 ms | 内存索引，异步持久化 |
| invoke 调用延迟 | < 200 ms（不含 LLM） | 直连通道，无中间转发 |
| 消息队列吞吐 | > 5000 条/秒 | 批量处理，零拷贝序列化 |
| Prompt 模板加载 | < 10 ms | 内存缓存，LRU 淘汰 |
| 通信日志写入 | 异步批量写入，不影响主流程 | WAL 模式，批量 INSERT |
| 权限校验延迟 | < 1 ms | 预计算权限矩阵缓存 |
| 能力发现查询 | < 20 ms | 倒排索引，模糊搜索 |
| 并发 Agent 实例 | 最多 32 个 | 连接池复用，资源限制 |

---

## 10. 验收标准

### P1 验收（核心功能）
- [ ] 8 种内置 Agent 角色正确定义，职责和能力描述清晰
- [ ] 能力注册中心正常工作，Agent 启动时自动注册能力
- [ ] 能力发现机制可用，支持按角色、分类、关键词查询
- [ ] invoke 同步调用正常工作，调用方能获取返回结果
- [ ] hook 异步钩子正常工作，订阅方能收到事件通知
- [ ] 事件订阅机制可用，支持按消息类型和角色过滤
- [ ] Prompt 模板编辑器可用，支持变量插值和实时预览
- [ ] Prompt 版本管理可用，支持版本切换和 diff 对比
- [ ] 项目级 Prompt 覆盖可用，不影响全局默认配置
- [ ] 执行上下文正确追踪，可查看 Agent 状态和资源使用
- [ ] 状态快照机制可用，支持自动和手动快照
- [ ] 权限矩阵正确生效，越权调用被拒绝
- [ ] 工具权限正确生效，危险操作需用户确认
- [ ] 热加载机制可用，运行时配置变更不影响当前任务
- [ ] 通信日志完整记录，支持筛选和导出

### P2 验收（增强功能）
- [ ] 上下文快照回放可用于调试
- [ ] 自定义 Agent 角色可用（P2）
- [ ] 配置导入/导出可用
- [ ] Agent Token 消耗统计准确

### P3 验收（扩展功能）
- [ ] 自定义能力插件注册 API 可用
- [ ] 能力市场（可选）

---

*文档维护者：TeamClaw 项目组*
