# PRD — 模块2：多 Agent 编排

> 版本：V1.0  
> 最后更新：2026-04-16  
> 优先级：P0（MVP 核心）

---

## 1. 功能概述

多 Agent 编排是 TeamClaw 的核心引擎。Main Agent 将用户需求拆解为任务 DAG，调度多个专业 Agent 并行/串行执行，在关键节点汇总问题统一提问用户，支持 7 种用户干预操作。内嵌 OpenClaw 实现 Agent 运行时，不重复造轮子。

---

## 2. 用户故事

| 编号 | 用户故事 | 优先级 |
|------|---------|--------|
| US-01 | 作为用户，我想看到 Main Agent 自动将需求拆分为任务 DAG | P0 |
| US-02 | 作为用户，我想查看 Agent 实时执行进度和日志 | P0 |
| US-03 | 作为用户，我想在 Agent 执行过程中暂停所有任务 | P0 |
| US-04 | 作为用户，我想修改正在执行任务的参数或方向 | P0 |
| US-05 | 作为用户，我想跳过当前任务，继续后续任务 | P0 |
| US-06 | 作为用户，我想回滚到上一个检查点 | P0 |
| US-07 | 作为用户，我想中途终止整个对话 | P0 |
| US-08 | 作为用户，我想在 DAG 中插入新任务 | P0 |
| US-09 | 作为用户，我想向执行中的 Agent 发送补充指令 | P0 |
| US-10 | 作为用户，我想让多个 Agent 的问题被统一汇总提问，避免被轰炸 | P0 |
| US-11 | 作为用户，我想查看任务依赖关系图 | P1 |
| US-12 | 作为用户，我想调整任务优先级 | P1 |
| US-13 | 作为用户，我想手动触发某个任务的重新执行 | P1 |
| US-14 | 作为用户，我想为任务设置超时时间 | P2 |

---

## 3. 功能需求清单

### 3.1 任务 DAG 生成 [P0]

**触发**：用户确认 PRD 后（阶段 ② → ③）

**流程**：
1. Architect Agent 分析 PRD，输出技术方案草案
2. Main Agent 将方案拆解为可执行任务
3. 为每个任务分配 Agent 角色
4. 建立任务间依赖关系（DAG）
5. 预估每个任务的执行时间
6. 展示 DAG 给用户确认

**任务定义结构**：
```typescript
interface Task {
  id: string;                    // UUID
  title: string;                 // 任务标题
  description: string;           // 详细描述
  agent_role: AgentRole;         // 分配的 Agent
  status: TaskStatus;           // pending | assigned | in_progress | blocked | done | failed
  depends_on: string[];          // 依赖的任务 ID 列表
  estimated_time: number;        // 预估时间（分钟）
  timeout: number;               // 超时时间（分钟）
  artifacts: Artifact[];         // 产物列表
  created_at: number;            // 创建时间戳
  started_at?: number;           // 开始时间戳
  completed_at?: number;         // 完成时间戳
}

type AgentRole = 'main' | 'pm' | 'designer' | 'architect' | 'coderA' | 'coderB' | 'dba' | 'devops';
```

**DAG 可视化**：
- 使用 Mermaid.js 或类似库展示 DAG
- 不同 Agent 角色用不同颜色标记
- 当前执行中任务高亮
- 已完成任务用灰色标记
- 失败任务用红色标记

### 3.2 Agent 调度引擎 [P0]

**调度策略**：
1. **拓扑排序**：按照依赖关系确定执行顺序
2. **并行执行**：无依赖关系的任务同时启动
3. **资源管理**：控制同时运行的最大 Agent 数量（默认 4 个）
4. **超时处理**：任务超时后标记失败，进入异常处理流程

**调度流程**：
```
1. 初始化：所有无依赖任务标记为「ready」
2. 循环调度：
   a. 从「ready」队列取任务，分配给对应 Agent
   b. 监听 Agent 进度更新
   c. 任务完成后，检查其依赖任务是否全部完成
   d. 如果依赖满足，将后置任务加入「ready」队列
3. 所有任务完成 → 进入阶段 ⑤（中间审核）
```

**Agent 实例管理**：
- 每个 Agent 角色对应一个 OpenClaw Agent 实例
- 实例生命周期：分配 → 启动 → 运行 → 完成/失败 → 销毁
- 支持同一角色多个实例并行（如 CoderA 和 CoderB 可同时运行）

### 3.3 并发提问汇总 [P0]

**问题收集**：
- 各 Agent 遇到问题时，将问题发送给 Main Agent
- Main Agent 维护一个待提问队列

**汇总规则**：
- 每累积 3 个问题或每隔 30 秒（取先到），统一向用户提问
- 相关问题归类：技术选型、功能确认、边界条件等
- 避免重复问题：相似问题合并提问

**提问格式（桌面端）**：
```
📋 Agent 汇总提问 (3 个)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎨 Designer Agent:
「登录页是否需要记住密码功能？」

🏗️ Architect Agent:
「后端用什么数据库？PostgreSQL / MySQL / 其他？」

💻 CoderA Agent:
「是否需要做单元测试？」

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

回复格式：编号+答案（可多选），如「1 需要 2 PostgreSQL 3 需要」
或「跳过该问题」
```

**提问格式（微信端）**：
```
📋 有 3 个问题需确认

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ 登录页是否需要记住密码功能？
   [需要] [不需要]

2️⃣ 后端用什么数据库？
   [PostgreSQL] [MySQL] [其他]

3️⃣ 是否需要做单元测试？
   [是] [否]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

回复编号，如「123」或「1 需要 3 是」
```

### 3.4 用户干预操作 [P0]

**7 种操作定义**：

| 操作 | 图标 | 触发时机 | 效果 |
|------|------|---------|------|
| 暂停 | ⏸️ | 任何时候 | 暂停所有正在运行的 Agent，状态变为 `paused` |
| 修改 | ✏️ | 任务执行中 | 修改当前任务的参数或方向，Agent 重新执行 |
| 跳过 | ⏭️ | 任务执行中 | 跳过当前任务，标记为 `skipped`，继续后续任务 |
| 回滚 | ↩️ | 任务完成后 | 回滚到上一个检查点，撤销产物变更 |
| 中止 | 🛑 | 任何时候 | 终止整个对话，所有任务停止，对话状态变为 `aborted` |
| 插入 | 📝 | 任何时候 | 在 DAG 中插入新任务，自动计算依赖关系 |
| 提问 | 💬 | 任务执行中 | 向执行中的 Agent 发送补充指令 |

**暂停/恢复流程**：
```
用户点击「暂停」
    ↓
Main Agent 发送暂停信号给所有运行中的 Agent
    ↓
Agent 保存当前状态，停止执行
    ↓
用户点击「恢复」
    ↓
Main Agent 唤醒 Agent，从暂停点继续
```

**修改任务流程**：
```
用户点击任务卡片 →「修改」
    ↓
弹窗显示任务详情，可修改：标题、描述、参数
    ↓
用户提交修改
    ↓
Main Agent 重新分配任务给对应 Agent
    ↓
Agent 重新执行，覆盖原产物
```

**回滚流程**：
```
用户点击「回滚」
    ↓
选择回滚目标（检查点列表）
    ↓
系统执行回滚操作：
   - 代码恢复到 Git commit
   - 数据库执行 down migration
   - 文件恢复快照
    ↓
任务状态变为 `pending`，可重新执行
```

### 3.5 任务进度监控 [P0]

**实时信息展示**：

| 元素 | 说明 |
|------|------|
| Agent 头像 | 当前 Agent 角色 |
| 进度条 | 0-100% |
| 状态标签 | 执行中 / 等待中 / 已完成 / 失败 |
| 日志流 | 实时输出的 Agent 日志 |
| 产物预览 | 生成的文件、代码片段 |
| 预估剩余时间 | 根据当前进度计算 |

**任务看板视图**：
- 列：待办、进行中、审核中、已完成、失败
- 卡片：任务标题、Agent、进度、时间

**DAG 可视化视图**：
- 节点：任务
- 边：依赖关系
- 实时更新：任务状态变化时动态刷新

### 3.6 OpenClaw 集成 [P0]

**Agent 启动流程**：
```
Main Agent 请求 OpenClaw 启动指定角色 Agent
    ↓
OpenClaw 创建 Agent 实例，注入任务上下文
    ↓
Agent 连接到 OpenClaw Runtime
    ↓
Agent 开始执行，调用工具（代码生成、文件读写等）
    ↓
Main Agent 监听 Agent 事件（进度、产物、错误）
    ↓
任务完成 → OpenClaw 销毁 Agent 实例
```

**事件通信**：
```typescript
// Main Agent → OpenClaw
interface AgentStartRequest {
  task_id: string;
  agent_role: AgentRole;
  task_context: {
    description: string;
    dependencies: Artifact[];
    constraints: string[];
  };
}

// OpenClaw → Main Agent
interface AgentEvent {
  task_id: string;
  event_type: 'progress' | 'artifact' | 'question' | 'error' | 'completed';
  payload: any;
  timestamp: number;
}
```

**工具调用限制**：
- Agent 只能操作项目目录内的文件
- 禁止系统级操作（如 rm -rf /）
- 关键操作需用户确认（如数据库迁移）

### 3.7 异常处理 [P0]

**场景 1：Agent 执行失败**
1. 任务标记为 `failed`
2. 收集错误日志和堆栈信息
3. Main Agent 分析失败原因
4. 提示用户：重试 / 跳过 / 修改任务后重试

**场景 2：依赖任务失败**
1. 后置任务自动进入 `blocked` 状态
2. 等待前置任务修复
3. 用户修复前置任务后，阻塞任务自动恢复

**场景 3：网络断开**
1. 检测到连接断开
2. 尝试重连（最多 3 次）
3. 重连失败 → 暂停所有任务，等待用户操作

**场景 4：超时**
1. 任务超时后标记为 `failed`
2. 可配置是否自动重试
3. 记录超时日志供后续分析

### 3.8 检查点机制 [P1]

**检查点创建时机**：
- 每个 Agent 完成后自动创建
- 用户手动创建（在关键节点）

**检查点内容**：
- 当前任务产物快照
- 数据库状态（migration 版本）
- Git commit hash
- 任务状态快照

**恢复检查点**：
```
用户选择检查点 →「恢复」
    ↓
系统验证检查点完整性
    ↓
执行恢复操作：
   - 代码恢复到指定 commit
   - 数据库回滚到指定 migration
   - 文件恢复快照
    ↓
任务状态恢复到检查点时刻
```

### 3.9 任务优先级调整 [P1]

**优先级定义**：
- P0：核心功能，阻塞其他任务
- P1：重要功能
- P2：次要功能

**调整规则**：
- 同优先级任务按依赖顺序执行
- 高优先级任务优先分配资源
- 用户可手动调整任务优先级

### 3.10 手动触发任务 [P1]

**场景**：
- 用户想重新执行某个已完成的任务
- 用户想强制执行某个失败的任务

**流程**：
1. 用户点击任务卡片 →「重新执行」
2. 系统重置任务状态为 `pending`
3. 重新分配 Agent 执行
4. 覆盖原产物（或生成新版本）

---

## 4. 数据模型

```sql
-- 任务表
CREATE TABLE tasks (
  id              TEXT PRIMARY KEY,          -- UUID
  project_id      TEXT NOT NULL,
  conversation_id TEXT NOT NULL,
  parent_id       TEXT,                      -- 父任务 ID
  title           TEXT NOT NULL,
  description     TEXT NOT NULL,
  agent_role      TEXT NOT NULL,             -- main | pm | designer | architect | coderA | coderB | dba | devops
  status          TEXT DEFAULT 'pending',     -- pending | assigned | in_progress | blocked | paused | done | failed | skipped
  priority        INTEGER DEFAULT 1,         -- 0=P0, 1=P1, 2=P2
  depends_on      TEXT DEFAULT '[]',         -- 依赖任务 ID 数组 JSON
  estimated_time  INTEGER,                   -- 预估时间（分钟）
  timeout         INTEGER DEFAULT 60,        -- 超时时间（分钟）
  progress        INTEGER DEFAULT 0,         -- 进度 0-100
  created_at      INTEGER NOT NULL,
  started_at      INTEGER,
  completed_at    INTEGER,
  FOREIGN KEY (project_id) REFERENCES projects(id),
  FOREIGN KEY (conversation_id) REFERENCES conversations(id),
  FOREIGN KEY (parent_id) REFERENCES tasks(id)
);

-- 产物表
CREATE TABLE artifacts (
  id          TEXT PRIMARY KEY,              -- UUID
  task_id     TEXT NOT NULL,
  type        TEXT NOT NULL,                 -- code | doc | design | config | db_schema
  path        TEXT NOT NULL,                 -- 文件路径
  version     INTEGER DEFAULT 1,             -- 版本号
  checksum    TEXT,                          -- 文件校验和
  created_at  INTEGER NOT NULL,
  FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- 检查点表
CREATE TABLE checkpoints (
  id          TEXT PRIMARY KEY,              -- UUID
  task_id     TEXT NOT NULL,
  name        TEXT NOT NULL,                 -- 检查点名称
  snapshot    TEXT NOT NULL,                 -- 快照数据 JSON
  git_commit  TEXT,                          -- Git commit hash
  db_version  INTEGER,                       -- 数据库版本
  created_at  INTEGER NOT NULL,
  FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- Agent 执行日志
CREATE TABLE agent_logs (
  id          TEXT PRIMARY KEY,              -- UUID
  task_id     TEXT NOT NULL,
  agent_role  TEXT NOT NULL,
  level       TEXT NOT NULL,                 -- info | warn | error | debug
  message     TEXT NOT NULL,
  created_at  INTEGER NOT NULL,
  FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- 待提问队列
CREATE TABLE pending_questions (
  id          TEXT PRIMARY KEY,              -- UUID
  task_id     TEXT NOT NULL,
  agent_role  TEXT NOT NULL,
  question    TEXT NOT NULL,
  category    TEXT,                          -- 分类：技术选型 | 功能确认 | 边界条件
  status      TEXT DEFAULT 'pending',       -- pending | asked | answered
  batch_id    TEXT,                          -- 批次 ID（同一批次的提问）
  created_at  INTEGER NOT NULL,
  answered_at INTEGER,
  FOREIGN KEY (task_id) REFERENCES tasks(id)
);
```

---

## 5. Tauri Commands 接口

```typescript
// DAG 管理
generate_task_dag(conversationId: string, prd: string): Promise<Task[]>
get_task_dag(conversationId: string): Promise<TaskDag>
update_task_dependencies(taskId: string, dependsOn: string[]): Promise<void>

// 任务执行
start_task(taskId: string): Promise<void>
pause_task(taskId: string): Promise<void>
resume_task(taskId: string): Promise<void>
cancel_task(taskId: string): Promise<void>
skip_task(taskId: string): Promise<void>

// 任务修改
update_task(taskId: string, payload: UpdateTaskInput): Promise<Task>
retry_task(taskId: string): Promise<void>

// 用户干预
rollback_to_checkpoint(checkpointId: string): Promise<void>
insert_task(parentId: string, payload: CreateTaskInput): Promise<Task>
send_agent_instruction(taskId: string, instruction: string): Promise<void>

// 进度监控
get_task_progress(taskId: string): Promise<TaskProgress>
subscribe_task_events(taskId: string): EventChannel<TaskEvent>
get_agent_logs(taskId: string, limit?: number): Promise<AgentLog[]>

// 检查点
create_checkpoint(taskId: string, name?: string): Promise<Checkpoint>
list_checkpoints(taskId: string): Promise<Checkpoint[]>
restore_checkpoint(checkpointId: string): Promise<void>

// 问题汇总
batch_questions(conversationId: string): Promise<QuestionBatch>
answer_question_batch(batchId: string, answers: Record<string, string>): Promise<void>
```

---

## 6. UI 交互流程

### 6.1 DAG 确认流程

```
[需求澄清完成]
    │
    ▼
[Main Agent 生成任务 DAG]
    │
    ▼
[DAG 可视化页面]
    ├─ 展示任务节点和依赖关系
    ├─ 点击节点查看任务详情
    ├─ 可拖拽调整节点位置
    │
    ▼
[用户确认]
    ├─ ✅ 确认 → 进入执行阶段
    └─ ✏️ 修改 → 调整任务后重新确认
```

### 6.2 执行监控流程

```
[DAG 执行页面]
    │
    ├─ 左侧：任务列表（看板）
    ├─ 中间：DAG 可视化（实时更新）
    └─ 右侧：当前任务详情 + 日志流
    │
    ├─ 点击任务卡片
    │   ▼
    │   [查看详细日志]
    │   [查看产物]
    │   [操作：暂停/修改/跳过/回滚]
    │
    ├─ 顶部控制栏
    │   [暂停全部] [恢复全部] [中止对话]
    │
    └─ 插入任务按钮
        ▼
        [插入任务弹窗]
        ├─ 选择插入位置（前置任务）
        ├─ 填写任务信息
        └─ 确认插入
```

### 6.3 提问汇总流程

```
[多个 Agent 提问]
    │
    ▼
[Main Agent 收集问题]
    │
    ▼
[触发汇总条件：3个问题或30秒]
    │
    ▼
[弹窗/卡片：汇总提问]
    ├─ 展示问题列表
    ├─ 分类整理
    ├─ 输入答案
    │
    ▼
[用户提交答案]
    │
    ▼
[分发答案给各 Agent]
    │
    ▼
[Agent 继续执行]
```

---

## 7. 边界条件与异常处理

| 场景 | 处理方式 |
|------|---------|
| DAG 有循环依赖 | 检测并提示，禁止生成 |
| 所有 Agent 都在运行，新任务需要调度 | 等待队列中，直到有 Agent 空闲 |
| Agent 持续失败（3次以上） | 标记为阻塞，提示用户检查 |
| 用户无响应超时（提问后 24 小时） | 自动暂停对话，发送通知 |
| 磁盘空间不足 | 检测并警告，禁止执行新任务 |
| OpenClaw 连接断开 | 重试 3 次，失败后暂停所有任务 |
| Git 操作失败（冲突、权限） | 提示错误，提供解决方案选项 |
| 任务产物文件被外部修改 | 检测到差异，提示用户确认 |

---

## 8. 性能与优化

| 指标 | 目标 | 优化措施 |
|------|------|---------|
| DAG 生成时间 | < 5 秒 | 缓存常用模板，并行分析 |
| Agent 启动时间 | < 3 秒 | 预热 Agent 实例池 |
| 进度更新延迟 | < 500 ms | 使用 WebSocket 推送 |
| 日志传输效率 | > 1000 行/秒 | 批量传输，压缩 |
| 并发任务数 | 最多 8 个 | 动态资源分配 |

---

## 9. 验收标准

### P0 验收（MVP）
- [ ] Main Agent 能自动生成任务 DAG
- [ ] DAG 可视化正确展示依赖关系
- [ ] 无依赖任务能并行执行
- [ ] 有依赖任务按顺序执行
- [ ] 7 种用户干预操作全部可用
- [ ] 并发提问能正确汇总
- [ ] 任务失败能正确处理
- [ ] Agent 日志能实时展示
- [ ] 超时机制生效
- [ ] OpenClaw 集成正常工作

### P1 验收
- [ ] 检查点机制可用
- [ ] 任务优先级可调整
- [ ] 手动触发任务执行
- [ ] 任务统计信息准确

---

*文档维护者：TeamClaw 项目组*
