# PRD — 模块3：任务体系

> 版本：V1.0  
> 最后更新：2026-04-16  
> 优先级：P0（MVP 核心）

---

## 1. 功能概述

任务体系是 TeamClaw 的骨架。它将用户需求具象化为可追踪、可管理的任务单元，贯穿整个对话生命周期。任务从 DAG 生成到最终完成，经历多种状态流转，关联产物、依赖关系和执行日志。本模块定义任务的数据结构、状态机、依赖管理、产物关联和看板视图。

---

## 2. 用户故事

| 编号 | 用户故事 | 优先级 |
|------|---------|--------|
| US-01 | 作为用户，我想看到所有任务的状态一目了然（看板视图） | P0 |
| US-02 | 作为用户，我想点击任务查看详情（描述、Agent、产物、日志） | P0 |
| US-03 | 作为用户，我想看到任务之间的依赖关系 | P0 |
| US-04 | 作为用户，我想看到任务状态实时更新，无需刷新 | P0 |
| US-05 | 作为用户，我想在任务完成后查看生成的产物（代码、文档、配置等） | P0 |
| US-06 | 作为用户，我想筛选任务（按状态、Agent、优先级） | P0 |
| US-07 | 作为用户，我想重新执行失败的任务 | P0 |
| US-08 | 作为用户，我想查看任务的执行时间统计 | P1 |
| US-09 | 作为用户，我想为任务添加备注或标签 | P1 |
| US-10 | 作为用户，我想导出任务报告（Markdown/JSON） | P2 |
| US-11 | 作为用户，我想对比不同版本的产物（diff） | P2 |
| US-12 | 作为用户，我想批量操作任务（批量暂停、批量取消） | P2 |

---

## 3. 功能需求清单

### 3.1 任务状态机 [P0]

**状态定义**：

| 状态 | 标识 | 说明 |
|------|------|------|
| 待办 | `pending` | 任务已创建，等待调度 |
| 已分配 | `assigned` | 已分配 Agent，等待启动 |
| 执行中 | `in_progress` | Agent 正在执行 |
| 已暂停 | `paused` | 用户暂停或系统挂起 |
| 被阻塞 | `blocked` | 前置依赖未完成 |
| 审核中 | `reviewing` | 任务完成，等待用户审核 |
| 已完成 | `done` | 审核通过，任务结束 |
| 已失败 | `failed` | 执行失败 |
| 已跳过 | `skipped` | 用户主动跳过 |
| 已取消 | `cancelled` | 用户取消任务 |

**状态流转规则**：

```
                    ┌──────────────────────────────────────────────┐
                    │              任务状态机                       │
                    │                                              │
                    │   pending ──────► assigned ──────► in_progress
                    │     │                │                  │  │
                    │     │                │          ┌───────┘  └──────┐
                    │     │                │          ▼                 ▼
                    │     │                │       paused          reviewing
                    │     │                │          │              │  │
                    │     │                │          │         ┌────┘  └──┐
                    │     │                │          │         ▼         ▼
                    │     ▼                ▼          │      done    iterating
                    │  cancelled ◄──── cancelled      │               │
                    │                             resumed              │
                    │                              │                   │
                    │                              ▼                   │
                    │                         in_progress ◄────────────┘
                    │                              │
                    │                    ┌─────────┼─────────┐
                    │                    ▼         ▼         ▼
                    │                done      failed    skipped
                    │                              │
                    │                          retry
                    │                              │
                    │                              ▼
                    │                          pending
                    └──────────────────────────────────────────────┘
```

**触发条件**：

| 从 → 到 | 触发条件 | 执行者 |
|---------|---------|--------|
| pending → assigned | DAG 调度分配 Agent | 系统 |
| assigned → in_progress | Agent 开始执行 | 系统 |
| in_progress → paused | 用户暂停 | 用户 |
| paused → in_progress | 用户恢复 | 用户 |
| in_progress → reviewing | Agent 完成执行 | 系统 |
| reviewing → done | 用户审核通过 | 用户 |
| reviewing → iterating | 用户驳回（附修改意见） | 用户 |
| iterating → in_progress | Agent 重新执行 | 系统 |
| in_progress → failed | Agent 执行异常或超时 | 系统 |
| failed → pending | 用户重试 | 用户 |
| in_progress → skipped | 用户跳过 | 用户 |
| 任意 → cancelled | 用户取消 | 用户 |

### 3.2 任务依赖管理 [P0]

**依赖类型**：

| 类型 | 标识 | 说明 |
|------|------|------|
| 完成依赖 | `finish_to_start` | 前置任务完成后才能开始（默认） |
| 产物依赖 | `artifact_dependency` | 当前任务需要前置任务的产物作为输入 |

**依赖规则**：
1. **禁止循环依赖**：DAG 生成时检测，有环则拒绝并提示
2. **阻塞传播**：前置任务失败 → 后置任务自动进入 `blocked`
3. **解除阻塞**：前置任务重试成功 → 后置任务自动恢复为 `pending`
4. **跳过传播**：前置任务被跳过 → 提示用户确认后置任务处理方式（跳过/强制执行/取消）

**依赖变更**：
- 用户可在 DAG 确认阶段修改依赖关系
- 执行过程中插入新任务时，自动计算依赖
- 不允许删除已执行任务的依赖

### 3.3 任务看板 [P0]

**视图模式**：

#### 看板视图（默认）
```
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│   待办    │ │  进行中   │ │  审核中   │ │  已完成   │ │  失败/跳过 │
│          │ │          │ │          │ │          │ │          │
│ ┌──────┐ │ │ ┌──────┐ │ │ ┌──────┐ │ │ ┌──────┐ │ │ ┌──────┐ │
│ │任务A │ │ │ │任务C │ │ │ │任务D │ │ │ │任务E │ │ │ │任务G │ │
│ │PM    │ │ │ │CoderA│ │ │ │Architect│ │ │DBA   │ │ │ │DevOps│ │
│ │⏱ 5min│ │ │ │████░░│ │ │ │审核中  │ │ │ ✅    │ │ │ │❌    │ │
│ └──────┘ │ │ └──────┘ │ │ └──────┘ │ │ └──────┘ │ │ └──────┘ │
│ ┌──────┐ │ │ ┌──────┐ │ │          │ │          │ │          │
│ │任务B │ │ │ │任务F │ │ │          │ │          │ │          │
│ │Designer│ │ │CoderB│ │ │          │ │          │ │          │
│ │⏱ 8min│ │ │ │██░░░░│ │ │          │ │          │ │          │
│ └──────┘ │ │ └──────┘ │ │          │ │          │ │          │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

**任务卡片信息**：
- 任务标题
- 分配的 Agent 角色（图标 + 名称）
- 进度条（执行中任务）
- 预估/已用时间
- 状态标签
- 优先级标记（P0 红色、P1 黄色、P2 灰色）

#### 列表视图
- 紧凑表格展示
- 列：状态、标题、Agent、优先级、耗时、操作
- 支持排序和筛选

#### DAG 图视图
- 节点为任务，边为依赖关系
- 实时更新节点颜色反映状态
- 可缩放、拖拽、点击查看详情

### 3.4 任务详情页 [P0]

**布局**：
```
┌─────────────────────────────────────────────────────┐
│  ← 返回    任务标题                    状态标签      │
├─────────────────────────────────────────────────────┤
│                                                     │
│  📋 基本信息                                        │
│  ┌─────────────────────────────────────────────┐    │
│  │ 描述：根据 PRD 设计数据库 Schema...          │    │
│  │ Agent：DBA                                   │    │
│  │ 优先级：P0                                   │    │
│  │ 依赖：[任务A] → 本任务                       │    │
│  │ 预估时间：15 分钟                            │    │
│  │ 实际耗时：12 分钟                            │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  📦 产物                                            │
│  ┌─────────────────────────────────────────────┐    │
│  │ schema.sql  (v1)  📥  👁️  📝               │    │
│  │ migration_001.sql (v1)  📥  👁️  📝          │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  📝 执行日志                                        │
│  ┌─────────────────────────────────────────────┐    │
│  │ [10:32:01] 开始分析 PRD...                   │    │
│  │ [10:32:05] 识别到 5 个实体...                │    │
│  │ [10:32:12] 生成 Schema 草案...               │    │
│  │ [10:32:18] 创建迁移脚本...                   │    │
│  │ [10:32:20] ✅ 任务完成                       │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  ⚡ 操作                                            │
│  [暂停] [修改] [跳过] [回滚] [重新执行]            │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 3.5 产物管理 [P0]

**产物类型**：

| 类型 | 标识 | 文件示例 |
|------|------|---------|
| 代码 | `code` | `*.ts`, `*.py`, `*.rs` |
| 文档 | `doc` | `*.md`, `*.txt` |
| 设计 | `design` | `*.html`, `*.css` |
| 配置 | `config` | `*.yaml`, `*.json`, `*.toml` |
| 数据库 | `db_schema` | `*.sql` |
| 脚本 | `script` | `*.sh`, `*.bat` |

**产物生命周期**：
```
Agent 生成产物 → 自动保存到项目目录 → 记录版本 → 用户可预览/下载/对比
```

**产物操作**：

| 操作 | 说明 |
|------|------|
| 预览 | 在详情页内直接查看文件内容（代码高亮） |
| 下载 | 导出单个文件或打包下载 |
| 对比 | 查看不同版本的 diff（P2） |
| 编辑 | 用户手动微调产物内容 |

**产物版本规则**：
- 同一任务重新执行时，产物版本号递增
- 旧版本不删除，可在版本历史中查看
- 回滚时恢复到指定版本

### 3.6 任务筛选与搜索 [P0]

**筛选条件**：
- 状态：多选（pending / in_progress / done / failed / ...）
- Agent 角色：多选
- 优先级：多选（P0 / P1 / P2）
- 时间范围：创建时间 / 完成时间

**搜索**：
- 按任务标题搜索（模糊匹配）
- 按任务描述搜索（全文检索）

**排序**：
- 创建时间（默认）
- 优先级
- 状态
- 预估时间

### 3.7 任务统计 [P1]

**项目级统计**：
```
┌──────────────────────────────────────┐
│  📊 项目统计                         │
│                                      │
│  总任务数：23                         │
│  ████████████░░░░  完成 65% (15/23)  │
│                                      │
│  按 Agent：                          │
│  CoderA   ████████░░  8 个           │
│  CoderB   ██████░░░░  6 个           │
│  Architect ████░░░░░░  4 个           │
│  DBA      ██░░░░░░░░  2 个           │
│                                      │
│  平均耗时：12 分钟                    │
│  总 Agent 执行时间：4.6 小时          │
│  产物数量：34 个文件                  │
└──────────────────────────────────────┘
```

### 3.8 任务备注与标签 [P1]

**备注**：
- 用户可为任务添加文字备注
- 支持多条备注，按时间排列
- Agent 不可见，仅供用户记录

**标签**：
- 预设标签：`bug`、`enhancement`、`refactor`、`docs`
- 支持自定义标签
- 可按标签筛选

### 3.9 任务导出 [P2]

**导出格式**：
- **Markdown**：任务清单，含标题、状态、Agent、描述
- **JSON**：完整数据，含依赖关系、产物路径
- **PDF**：格式化报告（调用系统打印）

### 3.10 批量操作 [P2]

**支持操作**：
- 批量暂停
- 批量取消
- 批量修改优先级
- 批量重新分配 Agent

**操作流程**：
1. 用户多选任务（复选框或 Shift+点击）
2. 选择操作类型
3. 确认操作（二次确认）
4. 批量执行

---

## 4. 数据模型

```sql
-- 任务表（补充模块2中的定义）
-- 与模块2共用同一张 tasks 表，这里补充查询索引

CREATE INDEX idx_tasks_project_status ON tasks(project_id, status);
CREATE INDEX idx_tasks_conversation ON tasks(conversation_id);
CREATE INDEX idx_tasks_agent_role ON tasks(agent_role);
CREATE INDEX idx_tasks_priority ON tasks(priority);

-- 任务备注表
CREATE TABLE task_notes (
  id          TEXT PRIMARY KEY,
  task_id     TEXT NOT NULL,
  content     TEXT NOT NULL,
  created_at  INTEGER NOT NULL,
  FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- 任务标签关联表
CREATE TABLE task_tags (
  id          TEXT PRIMARY KEY,
  task_id     TEXT NOT NULL,
  tag         TEXT NOT NULL,
  created_at  INTEGER NOT NULL,
  FOREIGN KEY (task_id) REFERENCES tasks(id),
  UNIQUE(task_id, tag)
);

-- 任务时间记录表
CREATE TABLE task_time_logs (
  id          TEXT PRIMARY KEY,
  task_id     TEXT NOT NULL,
  action      TEXT NOT NULL,           -- started | paused | resumed | completed | failed
  timestamp   INTEGER NOT NULL,
  FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- 任务操作记录表（审计日志）
CREATE TABLE task_audit_log (
  id          TEXT PRIMARY KEY,
  task_id     TEXT NOT NULL,
  action      TEXT NOT NULL,           -- status_change | priority_change | agent_reassign | note_added
  old_value   TEXT,
  new_value   TEXT,
  operator    TEXT NOT NULL,           -- user | system | agent:{role}
  created_at  INTEGER NOT NULL,
  FOREIGN KEY (task_id) REFERENCES tasks(id)
);
```

---

## 5. Tauri Commands 接口

```typescript
// 任务查询
get_task(taskId: string): Promise<TaskDetail>
list_tasks(filter: TaskFilter): Promise<Task[]>
get_task_stats(projectId: string): Promise<TaskStats>

// 任务操作
retry_task(taskId: string): Promise<void>
cancel_task(taskId: string): Promise<void>
skip_task(taskId: string): Promise<void>
update_task_priority(taskId: string, priority: number): Promise<void>
reassign_task(taskId: string, agentRole: AgentRole): Promise<void>

// 任务备注
add_task_note(taskId: string, content: string): Promise<TaskNote>
list_task_notes(taskId: string): Promise<TaskNote[]>
delete_task_note(noteId: string): Promise<void>

// 任务标签
add_task_tag(taskId: string, tag: string): Promise<void>
remove_task_tag(taskId: string, tag: string): Promise<void>
list_all_tags(projectId: string): Promise<string[]>

// 产物管理
list_artifacts(taskId: string): Promise<Artifact[]>
get_artifact_content(artifactId: string): Promise<string>
download_artifact(artifactId: string, targetPath: string): Promise<void>
get_artifact_versions(taskId: string): Promise<ArtifactVersion[]>

// 任务时间线
get_task_timeline(taskId: string): Promise<TaskTimeLog[]>
get_task_audit_log(taskId: string): Promise<TaskAuditEntry[]>

// 导出
export_tasks(projectId: string, format: 'markdown' | 'json'): Promise<string>

// 批量操作
batch_update_tasks(taskIds: string[], action: BatchAction): Promise<BatchResult>
```

---

## 6. UI 交互流程

### 6.1 看板操作流程

```
[项目详情页 → 任务 Tab]
    │
    ├─ 看板视图（默认）
    │   ├─ 拖拽任务卡片到其他列 → 更新状态
    │   ├─ 点击卡片 → 打开任务详情
    │   └─ 右键卡片 → 快捷操作菜单
    │
    ├─ 列表视图
    │   ├─ 表头点击排序
    │   ├─ 复选框多选 → 批量操作
    │   └─ 行点击 → 打开任务详情
    │
    ├─ DAG 视图
    │   ├─ 节点点击 → 弹出任务摘要
    │   ├─ 双击节点 → 打开任务详情
    │   └─ 缩放/拖拽/居中
    │
    └─ 筛选栏
        ├─ 状态筛选（多选）
        ├─ Agent 筛选（多选）
        ├─ 搜索框
        └─ 排序切换
```

### 6.2 任务详情操作流程

```
[任务详情页]
    │
    ├─ 产物区域
    │   ├─ 点击文件 → 内联预览（代码高亮）
    │   ├─ 点击版本号 → 版本历史列表
    │   ├─ 点击 📥 → 下载文件
    │   └─ 点击 📝 → 编辑产物（弹出编辑器）
    │
    ├─ 日志区域
    │   ├─ 自动滚动到底部（最新日志）
    │   ├─ 支持搜索日志内容
    │   └─ 支持按级别筛选（info/warn/error）
    │
    └─ 操作区域
        ├─ ⏸️ 暂停 → 确认弹窗 → 暂停
        ├─ ✏️ 修改 → 修改弹窗 → 重新执行
        ├─ ⏭️ 跳过 → 确认弹窗 → 跳过
        ├─ ↩️ 回滚 → 选择检查点 → 回滚
        ├─ 🔄 重试 → 确认弹窗 → 重新执行
        └─ 💬 指令 → 输入框 → 发送给 Agent
```

---

## 7. 边界条件与异常处理

| 场景 | 处理方式 |
|------|---------|
| 任务 DAG 有环 | 生成时检测，提示用户修正 |
| 删除有后置依赖的任务 | 提示影响范围，确认后级联处理 |
| 产物文件被外部删除 | 检测到缺失，标记为「产物丢失」，支持重新生成 |
| 任务卡片拖拽到非法列 | 拒绝操作，提示合法的状态转换 |
| 同时打开多个任务详情 | 支持 Tab 切换 |
| 大量任务（100+）渲染卡顿 | 虚拟滚动，懒加载 |
| 搜索结果为空 | 提示无匹配，建议放宽条件 |
| Agent 执行超时 | 自动标记 failed，通知用户 |

---

## 8. 验收标准

### P0 验收（MVP）
- [ ] 看板视图正确展示任务状态（5 列）
- [ ] 任务卡片展示完整信息（标题、Agent、进度、时间）
- [ ] 任务状态按状态机正确流转
- [ ] 任务依赖关系正确阻断/解锁
- [ ] 任务详情页展示描述、产物、日志
- [ ] 产物可预览和下载
- [ ] 支持按状态、Agent 筛选
- [ ] 支持按标题搜索
- [ ] 失败任务可重试
- [ ] 任务可跳过和取消

### P1 验收
- [ ] 列表视图可用
- [ ] DAG 图视图可用
- [ ] 任务统计信息准确
- [ ] 任务备注和标签功能可用
- [ ] 任务时间线记录完整

### P2 验收
- [ ] 任务导出（Markdown/JSON）
- [ ] 产物版本 diff 对比
- [ ] 批量操作功能

---

*文档维护者：TeamClaw 项目组*
