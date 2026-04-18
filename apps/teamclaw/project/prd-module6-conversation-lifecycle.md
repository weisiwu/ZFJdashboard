# PRD — 模块6：对话生命周期

> 版本：V1.0  
> 最后更新：2026-04-17  
> 优先级：P1（增强功能）  
> 依赖：模块1（项目导入）、模块2（多 Agent 编排）、模块3（任务体系）

---

## 1. 功能概述

对话生命周期是 TeamClaw 的流程骨架。每一次项目协作都以「对话」为核心载体，从用户提出需求开始，经历 8 个阶段、9 种状态转换，最终交付产物并归档。本模块定义对话的完整状态机、阶段流转规则、用户干预点、上下文管理策略和归档/解冻机制，确保 Agent 在人类监督下按既定流程协作。

### 设计原则

- **人机协作，人不离场** — 关键决策点必须用户确认
- **状态可回溯** — 每次状态变更都有记录，支持回滚
- **一次一个活跃对话** — 同一项目同时只有一个活跃对话
- **归档可解冻** — 归档对话可恢复为活跃状态，保留完整上下文

### 与其他模块的关系

```
模块1（项目导入）
    │
    ▼
模块6（对话生命周期）  ←── 本模块
    │
    ├── 模块2（多 Agent 编排）：阶段④⑤⑥的核心执行引擎
    ├── 模块3（任务体系）：阶段③④的任务管理
    ├── 模块4（外围能力）：微信端消息适配
    └── 模块5（知识库）：上下文积累与 RAG 检索
```

---

## 2. 对话生命周期全景图

```
┌─────────────────────────────────────────────────────────────┐
│                     对话生命周期 8 阶段                       │
│                                                             │
│  ① 创建     ② 需求澄清   ③ 任务拆分   ④ Agent 编排执行      │
│  ┌────┐    ┌─────────┐   ┌────────┐   ┌──────────────┐    │
│  │新建 │───►│ 澄清需求  │──►│ 拆分任务 │──►│ Agent 并行   │    │
│  └────┘    └─────────┘   └────────┘   │ /串行执行    │    │
│                                        └──────┬───────┘    │
│                                               │             │
│  ⑧ 归档     ⑦ 最终交付    ⑥ 迭代修改   ⑤ 中间审核           │
│  ┌────┐    ┌─────────┐   ┌────────┐   ┌──────▼───────┐    │
│  │归档 │◄───│  交付确认  │◄──│ 修改迭代 │◄──│  审核中间产物  │    │
│  └────┘    └─────────┘   └────────┘   └──────────────┘    │
│       ▲                                                    │
│       └── 解冻：archived → reviewing（保留完整上下文）        │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 用户故事

| 编号 | 用户故事 | 优先级 |
|------|---------|--------|
| US-01 | 作为用户，我想在项目中发起新对话并描述我的需求 | P1 |
| US-02 | 作为用户，我想看到对话当前处于哪个阶段，一目了然 | P1 |
| US-03 | 作为用户，我想在 Agent 提问时统一回答，而不是被逐个轰炸 | P1 |
| US-04 | 作为用户，我想确认 PRD 后再进入任务拆分，确保方向正确 | P1 |
| US-05 | 作为用户，我想在对话执行过程中随时中止 | P1 |
| US-06 | 作为用户，我想查看对话的完整历史记录和状态变更日志 | P1 |
| US-07 | 作为用户，我想在同一项目中同时只能有一个活跃对话，避免混乱 | P1 |
| US-08 | 作为用户，我想对话完成后归档，释放资源并保持项目整洁 | P1 |
| US-09 | 作为用户，我想从归档列表恢复某个对话并继续工作 | P1 |
| US-10 | 作为用户，我想在对话列表中筛选活跃/归档对话 | P1 |
| US-11 | 作为用户，我想通过微信端参与对话的关键确认环节 | P1 |
| US-12 | 作为用户，我想看到对话的阶段进度条，了解整体完成度 | P1 |
| US-13 | 作为用户，我想限制同一问题的迭代次数，避免无限循环 | P1 |
| US-14 | 作为用户，我想搜索历史对话内容 | P2 |
| US-15 | 作为用户，我想导出对话记录（Markdown/JSON） | P2 |
| US-16 | 作为用户，我想设置对话的上下文长度上限 | P2 |
| US-17 | 作为用户，我想对话超时未响应时自动暂停并通知我 | P2 |

---

## 4. 功能需求清单

### 4.1 对话状态机 [P1]

**状态定义**：

| 状态 | 标识 | 所属阶段 | 说明 |
|------|------|---------|------|
| 创建中 | `creating` | ① 创建 | 对话刚建立，等待初始需求输入 |
| 澄清中 | `clarifying` | ② 需求澄清 | Agent 追问细节，明确需求边界 |
| 拆分中 | `splitting` | ③ 任务拆分 | Main Agent 将需求拆解为任务 DAG |
| 执行中 | `executing` | ④ Agent 编排执行 | Agent 团队并行/串行工作 |
| 审核中 | `reviewing` | ⑤ 中间审核 | 等待用户审核中间产物 |
| 迭代中 | `iterating` | ⑥ 迭代修改 | 根据用户反馈修改产物 |
| 交付中 | `delivering` | ⑦ 最终交付 | 最终产物确认与交付 |
| 已归档 | `archived` | ⑧ 归档 | 对话完成，归档保存 |
| 已中止 | `aborted` | 异常 | 用户主动中止对话 |

**状态流转规则**：

```
                    ┌──────────────────────────────────────────────┐
                    │              对话状态机                       │
                    │                                              │
                    │  creating ──────► clarifying                  │
                    │                    │                          │
                    │                    ▼                          │
                    │               splitting                       │
                    │                    │                          │
                    │                    ▼                          │
                    │               executing ◄─────► reviewing     │
                    │                    │              │  │        │
                    │                    │              │  ▼        │
                    │                    │           iterating      │
                    │                    │                            │
                    │                    ▼                            │
                    │               delivering                        │
                    │                    │                            │
                    │                    ▼                            │
                    │               archived ────► reviewing（解冻）  │
                    │                                              │
                    │  任意状态 ──────► aborted                     │
                    └──────────────────────────────────────────────┘
```

**状态转换矩阵**：

| 从 → 到 | 触发条件 | 执行者 | 是否可逆 |
|---------|---------|--------|---------|
| creating → clarifying | 系统自动创建对话记录后 | 系统 | 否 |
| clarifying → splitting | 用户确认 PRD | 用户 | 是（↩️ 退回澄清） |
| splitting → executing | 用户确认任务 DAG | 用户 | 是（↩️ 退回拆分） |
| executing → reviewing | 里程碑完成 | 系统 | 否（但可⏸️暂停） |
| reviewing → iterating | 用户驳回（附修改意见） | 用户 | 否 |
| iterating → reviewing | Agent 修改完成，重新提交 | 系统 | 否 |
| reviewing → delivering | 所有审核通过 | 用户 | 是（↩️ 退回审核） |
| delivering → archived | 用户确认交付 | 用户 | 是（解冻） |
| archived → reviewing | 用户主动解冻 | 用户 | 是（可再次归档） |
| 任意 → aborted | 用户主动中止 | 用户 | 否 |

### 4.2 阶段 ①：创建（creating）[P1]

**触发**：用户在桌面端或微信端发起新对话

**前置条件**：
- 项目已存在且状态为 `active`
- 当前项目无其他活跃对话

**流程**：
1. 用户选择项目（或从项目详情页点击「新对话」）
2. 输入初始需求描述
3. 系统校验：项目是否存在、是否有活跃对话
4. 创建对话记录，分配对话 ID
5. 自动进入阶段 ②（clarifying）

**输入**：
```typescript
interface CreateConversationInput {
  project_id: string;
  initial_requirement: string;  // 初始需求描述
}
```

**输出**：对话创建成功，进入对话界面

### 4.3 阶段 ②：需求澄清（clarifying）[P1]

**目标**：充分理解需求，消除歧义，明确边界

**流程**：
1. PM Agent 分析初始需求
2. 生成澄清问题列表
3. **Main Agent 汇总所有问题，统一向用户提问**
4. 用户回答（可补充/修改需求）
5. PM Agent 确认需求理解，生成 PRD 草稿
6. 用户确认 PRD → 进入阶段 ③

**用户干预点**：

| 操作 | 说明 |
|------|------|
| ✏️ 修改 PRD | 用户可编辑 PRD 草稿的任意内容 |
| ❓ 补充信息 | 用户主动补充额外需求或约束 |
| ↩️ 重写需求 | 回到澄清阶段起点，重新提问 |
| ↩️ 退回创建 | 删除当前对话，重新创建 |

**输出物**：确认的 PRD 文档（Markdown 格式，存储于对话上下文中）

### 4.4 阶段 ③：任务拆分（splitting）[P1]

**目标**：将 PRD 拆解为可执行的任务 DAG

**流程**：
1. Architect Agent 分析 PRD，设计技术方案
2. Main Agent 将方案拆解为具体任务
3. 为每个任务分配 Agent 角色
4. 建立任务间依赖关系（DAG）
5. 展示任务清单和执行顺序给用户
6. 用户确认 → 进入阶段 ④

**用户干预点**：

| 操作 | 说明 |
|------|------|
| ✏️ 调整优先级 | 拖拽或手动修改任务优先级 |
| ✏️ 修改分配 | 更改任务的 Agent 角色 |
| ✏️ 增删任务 | 新增或删除任务节点 |
| ✏️ 修改依赖 | 调整任务间的依赖关系 |
| ↩️ 退回澄清 | 返回阶段 ② 重新确认需求 |

**输出物**：任务 DAG（含依赖关系、Agent 分配、预估时间）

### 4.5 阶段 ④：Agent 编排执行（executing）[P1]

**目标**：Agent 团队按 DAG 执行任务

**流程**：
1. Main Agent 按 DAG 调度 Agent
2. 无依赖的任务并行执行
3. 有依赖的任务等待前置完成
4. Agent 实时上报进度
5. 遇到问题 → Main Agent 汇总后统一提问用户
6. 关键里程碑完成 → 进入阶段 ⑤

**用户干预操作**（7 种，详见模块2 PRD）：

| 操作 | 图标 | 说明 |
|------|------|------|
| 暂停 | ⏸️ | 暂停当前所有 Agent 执行 |
| 修改 | ✏️ | 修改当前任务的参数或方向 |
| 跳过 | ⏭️ | 跳过当前任务，继续后续 |
| 回滚 | ↩️ | 回滚到上一个检查点 |
| 中止 | 🛑 | 终止整个对话 |
| 插入 | 📝 | 插入一个新任务到 DAG |
| 提问 | 💬 | 向执行中的 Agent 发送补充指令 |

**并发提问汇总规则**：
- 每累积 **3 个问题**或每隔 **30 秒**（取先到），统一向用户提问
- 相关问题归类：技术选型、功能确认、边界条件等
- 避免重复问题：相似问题合并提问

### 4.6 阶段 ⑤：中间审核（reviewing）[P1]

**目标**：确保阶段性产物符合预期

**流程**：
1. Agent 提交中间产物（代码、文档、设计稿等）
2. 系统展示产物预览（diff、截图、文档摘要）
3. 用户审核：
   - ✅ 通过 → 继续后续任务（回到 ④）或所有任务完成则进入 ⑦
   - ❌ 不通过 → 进入阶段 ⑥

**用户干预点**：

| 操作 | 说明 |
|------|------|
| ✅ 批准 | 确认当前产物符合预期，继续执行 |
| ❌ 驳回 | 附修改意见，退回修改 |
| 💬 追加评论 | 对产物添加评论或建议 |

**审核触发时机**：
- 单个任务完成时（默认）
- 里程碑节点（用户可配置）
- 用户主动触发审核

### 4.7 阶段 ⑥：迭代修改（iterating）[P1]

**目标**：根据审核反馈修改产物

**流程**：
1. Main Agent 分配修改任务给对应 Agent
2. Agent 根据反馈修改
3. 重新提交审核 → 回到阶段 ⑤
4. 达到迭代上限 → 提示用户考虑重写需求

**迭代限制**：
- 同一问题最多迭代 **5 轮**
- 每轮修改必须标注变更范围
- 超出迭代限制时提示：`⚠️ 此问题已迭代 5 轮仍未解决，建议重新评估需求或调整方向。是否继续迭代？`

**迭代计数规则**：
```typescript
interface IterationRecord {
  review_id: string;
  task_id: string;
  issue_description: string;   // 原始问题描述
  iteration_count: number;     // 当前迭代轮次
  change_summary: string;      // 本轮变更摘要
}
```

### 4.8 阶段 ⑦：最终交付（delivering）[P1]

**目标**：确认最终产物，完成交付

**流程**：
1. 所有任务完成，Main Agent 汇总最终产物
2. 生成交付清单（文件列表、变更摘要、测试报告）
3. 用户最终确认：
   - ✅ 确认交付 → 进入阶段 ⑧（归档）
   - ❌ 需要修改 → 回到阶段 ⑥

**交付清单内容**：

| 项目 | 说明 |
|------|------|
| 产物文件列表 | 所有生成的代码、文档、配置文件路径 |
| 变更摘要 | 相对于项目原始状态的变更说明 |
| 测试报告 | 单元测试/集成测试结果（如有） |
| 使用说明 | 产物使用指南、注意事项 |
| 对话摘要 | 本次对话的需求、决策、关键信息记录 |

### 4.9 阶段 ⑧：归档（archived）[P1]

**目标**：归档对话，释放资源

**流程**：
1. 对话状态标记为 `archived`
2. 完整上下文压缩存储
3. 对话从活跃列表移至归档列表
4. **该项目可创建新对话**

**归档操作**：

| 操作 | 说明 |
|------|------|
| 归档 | 对话完成后自动归档，或用户手动归档 |
| 删除 | 用户可永久删除已归档对话（需二次确认） |
| 导出 | 导出对话记录为 Markdown/JSON |

**解冻规则**：
- 用户可从归档列表选择对话「解冻」
- 解冻后该对话恢复为 `reviewing` 状态
- **同时自动冻结该项目其他活跃对话**（如有）
- 保留完整上下文，可继续工作
- 解冻后可重新进入 executing / iterating 等阶段

**解冻流程**：
```
用户选择归档对话 → 点击「解冻」
    ↓
系统检查：该项目是否有其他活跃对话
    │
    ├─ 有活跃对话 → 提示用户：「解冻此对话将暂停当前活跃对话『XXX』，是否继续？」
    │   ├─ 确认 → 暂停当前活跃对话 → 解冻目标对话
    │   └─ 取消 → 不操作
    │
    └─ 无活跃对话 → 直接解冻
    ↓
目标对话状态 → reviewing
项目活跃对话 → 已暂停对话
```

### 4.10 活跃对话唯一性约束 [P1]

**规则**：同一项目同时只有一个活跃对话

**校验时机**：
- 创建新对话时：检查项目是否有 `非 archived/aborted` 状态的对话
- 解冻归档对话时：检查项目是否有其他活跃对话

**违反时的提示**：
```
⚠️ 当前项目已有活跃对话「对话标题」
请先完成或归档当前对话，再创建新对话。
[查看当前对话] [归档当前对话]
```

### 4.11 对话上下文管理 [P1]

**上下文组成**：

| 组件 | 说明 | 存储 |
|------|------|------|
| 消息记录 | 所有 user/agent/system 消息 | SQLite |
| PRD 文档 | 阶段②产出的需求文档 | SQLite + 文件系统 |
| 任务 DAG | 阶段③产出的任务计划 | SQLite |
| 状态变更日志 | 每次状态转换的审计记录 | SQLite |
| Agent 执行日志 | Agent 的运行日志 | SQLite |
| 产物引用 | 关联的所有文件产物 | SQLite（引用） |

**上下文长度管理**：
- 对话上下文有长度上限（默认 **128K tokens**，可配置）
- 超出上限时：
  1. 将最早的消息摘要后压缩存储
  2. 摘要信息写入知识库（ChromaDB），保留检索能力
  3. 通知用户：「对话上下文已接近上限，早期消息已压缩归档」

**数据保留策略**：

| 数据类型 | 保留时长 | 存储方式 |
|---------|---------|---------|
| 活跃对话上下文 | 对话期间 | SQLite |
| 归档对话上下文 | 永久（压缩） | SQLite + 文件系统 |
| Agent 执行日志 | 90 天 | SQLite |
| 产物文件 | 永久 | 文件系统 + Git |
| 向量索引 | 跟随对话 | ChromaDB |

### 4.12 对话列表与管理 [P1]

**视图结构**：
- 活跃对话列表（默认视图）
- 归档对话列表（可切换）

**对话卡片信息**：
```
┌─────────────────────────────────────┐
│ 📋 对话标题                    状态标签 │
│ 📁 所属项目名                        │
│ 🕐 创建时间 · 最后活跃时间            │
│ 📝 需求摘要（首 50 字）               │
│                                     │
│ ████████░░░░░  阶段进度 4/8          │
│ 任务完成 12/18 · Agent 执行 2.3h     │
└─────────────────────────────────────┘
```

**筛选与搜索**：
- 按状态筛选：活跃 / 归档 / 已中止
- 按项目筛选
- 按时间范围筛选
- 按标题或内容搜索

**排序**：
- 最后活跃时间（默认）
- 创建时间
- 阶段进度

### 4.13 对话阶段进度展示 [P1]

**进度条设计**：

```
  ① 创建  ② 澄清  ③ 拆分  ④ 执行  ⑤ 审核  ⑥ 迭代  ⑦ 交付  ⑧ 归档
  ┌──┐    ┌──┐    ┌──┐    ┌────┐   ┌──┐    ┌──┐    ┌──┐    ┌──┐
  │✅│───►│✅│───►│✅│───►│████│──►│  │    │  │    │  │    │  │
  └──┘    └──┘    └──┘    └────┘   └──┘    └──┘    └──┘    └──┘

  ✅ 已完成   ████ 当前阶段   ○ 待执行
```

**进度计算规则**：
- 已完成阶段 = 当前阶段序号 - 1
- 总进度 = (已完成阶段数 / 8) × 100%
- 迭代阶段不计入总进度（视为审核阶段的子流程）

### 4.14 微信端适配 [P1]

**消息格式**：
```
📋 阶段：需求澄清
━━━━━━━━━━━━━━━━
PM Agent 有 3 个问题：

1️⃣ 这个功能面向什么用户群？
2️⃣ 预计并发量是多少？
3️⃣ 是否需要移动端适配？

━━━━━━━━━━━━━━━━
回复编号+答案，如"1 C端用户 2 约1000 3 需要"
```

**审核确认消息**：
```
⚠️ 需要确认操作

操作：执行数据库迁移
影响：新增 3 张表，修改 2 张表

确认请回复「确认」
取消请回复「取消」
```

**阶段进度消息**：
```
📊 对话进度
━━━━━━━━━━━━━━━━
当前阶段：④ Agent 编排执行
总体进度：████████░░░░ 50%
任务完成：9/18
Agent 执行时间：1.5 小时

正在执行：
🖥️ CoderA - 实现用户认证模块 (████░░ 60%)
🗄️ DBA - 设计数据库 Schema (██░░░░ 30%)
━━━━━━━━━━━━━━━━
```

**微信端约束**：

| 约束 | 说明 |
|------|------|
| 仅文字交互 | 不支持语音消息 |
| 二次确认 | 所有需确认操作必须二次确认 |
| 消息长度 | 单条不超过 2000 字，超出自动分段 |
| 图片展示 | 以缩略图 + 链接形式展示 |
| 实时性 | 消息推送延迟 ≤ 3 秒 |

### 4.15 状态变更审计日志 [P1]

**记录内容**：
```typescript
interface ConversationStateLog {
  id: string;
  conversation_id: string;
  from_state: ConversationState;
  to_state: ConversationState;
  trigger: 'system' | 'user' | 'agent';
  trigger_detail: string;    // 触发详情
  metadata: Record<string, any>;  // 附加信息
  created_at: number;
}
```

**审计日志查询**：
- 按对话查询完整状态变更历史
- 按时间范围筛选
- 支持导出

### 4.16 对话搜索 [P2]

**搜索范围**：
- 对话标题
- 消息内容（用户消息 + Agent 消息）
- PRD 文档内容
- 需求描述

**搜索方式**：
- 关键词搜索（模糊匹配）
- 全文检索（SQLite FTS5）

### 4.17 对话导出 [P2]

**导出格式**：

| 格式 | 内容 |
|------|------|
| Markdown | 对话记录、PRD、任务清单、产物摘要 |
| JSON | 完整数据（消息、状态日志、任务、产物引用） |

**导出流程**：
1. 用户选择对话 →「导出」
2. 选择导出格式
3. 选择存储位置（Tauri 文件选择器）
4. 生成导出文件

### 4.18 对话超时与自动暂停 [P2]

**规则**：
- 用户在需要确认的节点超过 **24 小时**未响应 → 自动暂停对话
- 自动暂停时发送通知（桌面端 + 微信端）
- 暂停后用户可随时恢复

**通知内容**：
```
⏸️ 对话「对话标题」已自动暂停
原因：等待确认超过 24 小时
暂停阶段：⑤ 中间审核

点击恢复以继续工作。
```

---

## 5. 数据模型

```sql
-- 对话表
CREATE TABLE conversations (
  id              TEXT PRIMARY KEY,          -- UUID
  project_id      TEXT NOT NULL,             -- 所属项目
  title           TEXT NOT NULL,             -- 对话标题
  status          TEXT DEFAULT 'creating',   -- creating | clarifying | splitting | executing | reviewing | iterating | delivering | archived | aborted
  current_phase   INTEGER DEFAULT 1,         -- 当前阶段 1-8
  prd_content     TEXT,                      -- PRD 文档内容（阶段②产出）
  requirement     TEXT DEFAULT '',           -- 初始需求描述
  context_tokens  INTEGER DEFAULT 0,         -- 当前上下文 token 数
  max_tokens      INTEGER DEFAULT 131072,    -- 上下文长度上限（128K）
  iteration_count INTEGER DEFAULT 0,         -- 当前问题迭代轮次
  summary         TEXT DEFAULT '',           -- 对话摘要
  created_at      INTEGER NOT NULL,          -- Unix timestamp
  updated_at      INTEGER NOT NULL,          -- Unix timestamp
  archived_at     INTEGER,                   -- 归档时间
  FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- 状态变更日志表
CREATE TABLE conversation_state_logs (
  id              TEXT PRIMARY KEY,          -- UUID
  conversation_id TEXT NOT NULL,
  from_state      TEXT NOT NULL,
  to_state        TEXT NOT NULL,
  trigger         TEXT NOT NULL,             -- system | user | agent
  trigger_detail  TEXT DEFAULT '',           -- 触发详情
  metadata        TEXT DEFAULT '{}',         -- 附加信息 JSON
  created_at      INTEGER NOT NULL,
  FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

-- 迭代记录表
CREATE TABLE iteration_records (
  id                TEXT PRIMARY KEY,        -- UUID
  conversation_id   TEXT NOT NULL,
  review_id         TEXT NOT NULL,           -- 关联的审核记录
  task_id           TEXT NOT NULL,           -- 关联的任务
  issue_description TEXT NOT NULL,           -- 原始问题描述
  iteration_count   INTEGER DEFAULT 1,       -- 当前迭代轮次
  change_summary    TEXT DEFAULT '',         -- 本轮变更摘要
  created_at        INTEGER NOT NULL,
  FOREIGN KEY (conversation_id) REFERENCES conversations(id),
  FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- 交付清单表
CREATE TABLE delivery_manifests (
  id              TEXT PRIMARY KEY,          -- UUID
  conversation_id TEXT NOT NULL,
  file_list       TEXT DEFAULT '[]',         -- 产物文件列表 JSON
  change_summary  TEXT DEFAULT '',           -- 变更摘要
  test_report     TEXT DEFAULT '',           -- 测试报告
  usage_guide     TEXT DEFAULT '',           -- 使用说明
  created_at      INTEGER NOT NULL,
  FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

-- 对话上下文压缩记录表
CREATE TABLE context_snapshots (
  id              TEXT PRIMARY KEY,          -- UUID
  conversation_id TEXT NOT NULL,
  snapshot_type   TEXT NOT NULL,             -- archived | compressed
  message_range   TEXT NOT NULL,             -- 压缩的消息范围 "1-50"
  summary         TEXT NOT NULL,             -- 压缩摘要
  token_count     INTEGER NOT NULL,          -- 原始 token 数
  created_at      INTEGER NOT NULL,
  FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

-- 索引
CREATE INDEX idx_conversations_project_status ON conversations(project_id, status);
CREATE INDEX idx_conversations_project_active ON conversations(project_id) 
  WHERE status NOT IN ('archived', 'aborted');
CREATE INDEX idx_conversation_state_logs_conv ON conversation_state_logs(conversation_id);
CREATE INDEX idx_conversation_state_logs_time ON conversation_state_logs(created_at);
CREATE INDEX idx_iteration_records_conv ON iteration_records(conversation_id);
CREATE INDEX idx_iteration_records_task ON iteration_records(task_id);
CREATE INDEX idx_context_snapshots_conv ON context_snapshots(conversation_id);
```

---

## 6. Tauri Commands 接口

```typescript
// ==================== 对话 CRUD ====================

// 创建对话
create_conversation(payload: CreateConversationInput): Promise<Conversation>
// 输入：{ project_id: string, initial_requirement: string }

// 获取对话详情
get_conversation(conversationId: string): Promise<ConversationDetail>

// 获取对话列表
list_conversations(filter: ConversationFilter): Promise<Conversation[]>

// 删除对话（仅归档/中止状态可删除）
delete_conversation(conversationId: string): Promise<void>

// 更新对话标题
update_conversation_title(conversationId: string, title: string): Promise<void>

// ==================== 状态流转 ====================

// 推进到下一阶段
advance_phase(conversationId: string, payload?: PhaseAdvancePayload): Promise<void>

// 退回上一阶段
rollback_phase(conversationId: string, targetPhase: ConversationPhase): Promise<void>

// 中止对话
abort_conversation(conversationId: string, reason?: string): Promise<void>

// ==================== 归档与解冻 ====================

// 归档对话
archive_conversation(conversationId: string): Promise<void>

// 解冻对话
unfreeze_conversation(conversationId: string): Promise<UnfreezeResult>
// 返回：{ success: boolean, frozen_conversation_id?: string, warning?: string }

// ==================== 上下文管理 ====================

// 获取对话上下文统计
get_context_stats(conversationId: string): Promise<ContextStats>
// 返回：{ total_tokens: number, max_tokens: number, message_count: number, compression_count: number }

// 设置上下文长度上限
set_context_limit(conversationId: string, maxTokens: number): Promise<void>

// 手动触发上下文压缩
compress_context(conversationId: string): Promise<ContextSnapshot>

// ==================== 迭代管理 ====================

// 获取迭代记录
get_iteration_records(conversationId: string, taskId?: string): Promise<IterationRecord[]>

// 检查迭代限制
check_iteration_limit(conversationId: string, taskId: string): Promise<IterationCheckResult>
// 返回：{ count: number, limit: number, exceeded: boolean }

// ==================== 审计日志 ====================

// 获取状态变更日志
get_state_logs(conversationId: string, options?: { limit?: number; offset?: number }): Promise<ConversationStateLog[]>

// ==================== 交付 ====================

// 生成交付清单
generate_delivery_manifest(conversationId: string): Promise<DeliveryManifest>

// 确认交付
confirm_delivery(conversationId: string): Promise<void>

// ==================== 导出 ====================

// 导出对话
export_conversation(conversationId: string, format: 'markdown' | 'json'): Promise<string>

// ==================== 搜索 ====================

// 搜索对话
search_conversations(query: string, options?: SearchOptions): Promise<SearchResult[]>

// ==================== 类型定义 ====================

type ConversationStatus = 
  | 'creating' | 'clarifying' | 'splitting' 
  | 'executing' | 'reviewing' | 'iterating' 
  | 'delivering' | 'archived' | 'aborted';

type ConversationPhase = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;

interface ConversationFilter {
  project_id?: string;
  status?: ConversationStatus[];
  keyword?: string;
  time_range?: { start: number; end: number };
  sort_by?: 'last_active' | 'created_at' | 'phase_progress';
}

interface ConversationDetail {
  id: string;
  project_id: string;
  title: string;
  status: ConversationStatus;
  current_phase: number;
  prd_content: string | null;
  requirement: string;
  context_tokens: number;
  max_tokens: number;
  iteration_count: number;
  summary: string;
  created_at: number;
  updated_at: number;
  // 关联数据
  messages: Message[];
  tasks: Task[];
  state_logs: ConversationStateLog[];
  phase_progress: {
    completed_phases: number;
    total_phases: number;
    percentage: number;
  };
}
```

---

## 7. UI 交互流程

### 7.1 创建对话流程

```
[项目详情页 → 对话 Tab]
    │
    ├─ 点击「新对话」
    │
    ▼
[活跃对话唯一性校验]
    ├─ 有活跃对话 → 提示：请先完成或归档当前对话
    └─ 无活跃对话 → 继续
    │
    ▼
[对话创建界面]
    ├─ 输入对话标题（必填）
    ├─ 输入需求描述（必填，文本区域）
    ├─ 可选：上传参考文件
    │
    ▼
[点击「创建」]
    │
    ▼
[对话界面] ← 状态：creating → 自动进入 clarifying
    ├─ PM Agent 开始分析需求
    └─ 展示阶段进度条
```

### 7.2 对话主界面布局

```
┌─────────────────────────────────────────────────────────────┐
│  ← 返回项目    对话标题                    状态标签           │
├─────────────────────────────────────────────────────────────┤
│  ①  ②  ③  ④  ⑤  ⑥  ⑦  ⑧                                  │
│  ✅→✅→✅→████→○→○→○→○     阶段进度条                       │
├────────────────────────────┬────────────────────────────────┤
│                            │                                │
│  💬 对话消息区域            │  📋 侧边面板（可折叠）         │
│  ┌──────────────────────┐  │                                │
│  │ 👤 用户：            │  │  ┌──────────────────────────┐  │
│  │ 我需要一个用户管理... │  │  │ PRD 文档                │  │
│  │                      │  │  │ [查看] [编辑]            │  │
│  │ 🤖 PM Agent：        │  │  ├──────────────────────────┤  │
│  │ 我有几个问题需要确认...│  │  │ 任务 DAG                │  │
│  │                      │  │  │ [查看] [编辑]            │  │
│  │ 🤖 Main Agent：      │  │  ├──────────────────────────┤  │
│  │ 汇总 3 个问题：       │  │  │ 任务看板                │  │
│  │ 1. ...               │  │  │ [展开]                   │  │
│  │ 2. ...               │  │  ├──────────────────────────┤  │
│  │ 3. ...               │  │  │ 状态日志                │  │
│  │                      │  │  │ creating → clarifying   │  │
│  ├──────────────────────┤  │  │ clarifying → splitting  │  │
│  │ ✏️ 输入回复...   [发送]│  │  └──────────────────────────┘  │
│  └──────────────────────┘  │                                │
├────────────────────────────┴────────────────────────────────┤
│  [⏸️暂停] [⏭️跳过] [↩️回滚] [📝插入任务] [🛑中止对话]      │
└─────────────────────────────────────────────────────────────┘
```

### 7.3 PRD 确认流程

```
[阶段 ②：需求澄清]
    │
    ├─ PM Agent 生成 PRD 草稿
    │
    ▼
[PRD 预览面板]
    ├─ 展示 PRD 完整内容（Markdown 渲染）
    ├─ 支持编辑（点击「编辑」切换编辑模式）
    │
    ▼
[用户操作]
    ├─ ✅ 确认 PRD → 进入阶段 ③（任务拆分）
    ├─ ✏️ 修改 PRD → 编辑后重新预览
    ├─ ❓ 补充信息 → 回复消息，PM Agent 更新 PRD
    └─ ↩️ 重写需求 → 回到澄清起点
```

### 7.4 任务 DAG 确认流程

```
[阶段 ③：任务拆分]
    │
    ├─ Main Agent 生成任务 DAG
    │
    ▼
[DAG 可视化面板]
    ├─ 展示任务节点和依赖关系
    ├─ 每个节点显示：任务名、Agent 角色、预估时间
    ├─ 可拖拽调整节点位置
    │
    ▼
[用户操作]
    ├─ ✅ 确认 DAG → 进入阶段 ④（执行）
    ├─ ✏️ 调整任务 → 增删改任务/依赖 → 重新预览
    └─ ↩️ 退回需求澄清 → 返回阶段 ②
```

### 7.5 审核流程

```
[阶段 ⑤：中间审核]
    │
    ├─ Agent 提交中间产物
    │
    ▼
[审核面板]
    ├─ 展示产物列表
    ├─ 每个产物可预览（代码高亮 / 文档渲染）
    ├─ 展示 diff 对比（如有变更）
    │
    ▼
[用户操作]
    ├─ ✅ 批准 → 继续后续任务 / 进入交付
    ├─ ❌ 驳回 → 附修改意见 → 进入阶段 ⑥
    └─ 💬 评论 → 添加评论（不改变状态）
```

### 7.6 交付确认流程

```
[阶段 ⑦：最终交付]
    │
    ├─ Main Agent 生成交付清单
    │
    ▼
[交付清单面板]
    ├─ 📦 产物文件列表（可点击查看/下载）
    ├─ 📝 变更摘要
    ├─ 🧪 测试报告
    ├─ 📖 使用说明
    ├─ 📊 对话摘要
    │
    ▼
[用户操作]
    ├─ ✅ 确认交付 → 进入阶段 ⑧（归档）
    └─ ❌ 需要修改 → 回到阶段 ⑥
```

### 7.7 归档与解冻流程

```
[对话列表页]
    │
    ├─ 切换 Tab：活跃 / 归档
    │
    ├─ 活跃 Tab
    │   ├─ 查看对话详情
    │   ├─ 继续对话
    │   └─ 中止对话（需确认）
    │
    └─ 归档 Tab
        ├─ 查看对话记录
        ├─ 点击「解冻」
        │   ├─ 检查活跃对话唯一性
        │   ├─ 如有活跃对话 → 提示确认
        │   └─ 解冻成功 → 进入对话界面
        ├─ 导出对话记录
        └─ 删除对话（需二次确认）
```

---

## 8. 事件定义

对话生命周期中的关键事件，通过 Tauri 事件总线推送：

```typescript
// 对话状态变更事件
interface ConversationStateEvent {
  conversation_id: string;
  from_state: ConversationStatus;
  to_state: ConversationStatus;
  phase: number;
  timestamp: number;
}

// 阶段推进事件
interface PhaseAdvanceEvent {
  conversation_id: string;
  from_phase: number;
  to_phase: number;
  output_summary: string;  // 本阶段产出摘要
  timestamp: number;
}

// 等待用户确认事件
interface UserConfirmationEvent {
  conversation_id: string;
  phase: number;
  confirmation_type: 'prd_confirm' | 'dag_confirm' | 'review_approve' | 'delivery_confirm';
  payload: any;
  timeout_seconds: number;  // 超时时间（24h = 86400）
  timestamp: number;
}

// 迭代警告事件
interface IterationWarningEvent {
  conversation_id: string;
  task_id: string;
  current_count: number;
  max_count: number;
  message: string;
  timestamp: number;
}

// 上下文压缩事件
interface ContextCompressEvent {
  conversation_id: string;
  compressed_range: string;
  remaining_tokens: number;
  total_tokens: number;
  timestamp: number;
}

// 自动暂停事件
interface AutoPauseEvent {
  conversation_id: string;
  reason: string;
  paused_at_phase: number;
  timestamp: number;
}
```

---

## 9. 边界条件与异常处理

| 场景 | 处理方式 |
|------|---------|
| 项目有活跃对话时创建新对话 | 拒绝创建，提示先完成或归档当前对话 |
| 解冻归档对话时项目有活跃对话 | 提示用户，确认后自动暂停当前活跃对话 |
| 非法状态转换 | 拒绝操作，提示合法的下一步操作 |
| 迭代超过 5 轮 | 弹窗警告，用户可选择继续或重新评估需求 |
| 对话上下文超出上限 | 自动压缩早期消息，摘要写入知识库，通知用户 |
| Agent 提问后用户 24 小时未响应 | 自动暂停对话，发送通知 |
| 归档对话的产物文件被外部删除 | 检测到缺失，标记为「产物丢失」，提示用户 |
| 删除已归档对话 | 需二次确认，提示「此操作不可撤销」 |
| 网络断开时微信端无法接收消息 | 消息队列缓存，恢复后补发 |
| 多端同时操作同一对话（桌面 + 微信） | 以后到的操作为准，冲突时提示 |
| PRD 内容为空时尝试进入任务拆分 | 拦截，提示「请先确认 PRD」 |
| 任务 DAG 为空时尝试进入执行 | 拦截，提示「任务列表不能为空」 |
| 并发提问汇总过程中 Agent 继续提交问题 | 加入下一批次，不阻塞当前批次 |
| 数据库写入失败（磁盘满等） | 错误日志记录，提示用户检查磁盘空间 |

---

## 10. 性能与优化

| 指标 | 目标 | 优化措施 |
|------|------|---------|
| 对话创建响应 | < 200 ms | SQLite 插入优化 |
| 状态变更响应 | < 100 ms | 事件总线异步推送 |
| 对话列表加载 | < 500 ms（100 条） | 分页加载 + 索引优化 |
| 状态日志查询 | < 300 ms | 复合索引 |
| 上下文压缩 | < 2 秒 | 后台异步执行 |
| 微信消息推送延迟 | < 3 秒 | 消息队列 + 心跳检测 |
| 归档操作 | < 1 秒 | 标记删除 + 延迟压缩 |
| 解冻操作 | < 2 秒 | 状态恢复 + 上下文重建 |

---

## 11. 验收标准

### P1 验收

- [ ] 能在项目中创建新对话，活跃对话唯一性约束生效
- [ ] 对话从 creating 自动进入 clarifying
- [ ] PM Agent 能生成澄清问题和 PRD 草稿
- [ ] 用户能确认/修改/重写 PRD
- [ ] 确认 PRD 后进入任务拆分阶段
- [ ] 用户能确认/修改任务 DAG
- [ ] 确认 DAG 后进入 Agent 执行阶段
- [ ] 执行过程中用户可暂停/修改/跳过/回滚/中止/插入任务/提问
- [ ] 里程碑完成进入审核阶段
- [ ] 用户能批准/驳回/评论审核产物
- [ ] 驳回后进入迭代阶段，迭代计数正确
- [ ] 同一问题迭代 5 轮后弹出警告
- [ ] 所有任务完成进入交付阶段
- [ ] 交付清单完整（文件列表、变更摘要、测试报告、使用说明）
- [ ] 用户确认交付后自动归档
- [ ] 归档对话可从归档列表查看
- [ ] 解冻归档对话成功，状态恢复为 reviewing
- [ ] 解冻时如有活跃对话，提示并自动暂停
- [ ] 阶段进度条正确展示当前阶段和已完成阶段
- [ ] 状态变更审计日志完整记录
- [ ] 并发提问正确汇总，避免轰炸用户
- [ ] 微信端消息格式正确，支持确认操作
- [ ] 微信端单条消息超 2000 字自动分段
- [ ] 对话列表支持筛选（活跃/归档）和搜索
- [ ] 对话上下文接近上限时自动压缩

### P2 验收

- [ ] 对话搜索功能可用
- [ ] 对话导出（Markdown/JSON）功能可用
- [ ] 对话上下文长度上限可配置
- [ ] 24 小时未响应自动暂停并发送通知
- [ ] 上下文压缩后仍可通过知识库检索历史信息

---

*文档维护者：TeamClaw 项目组*
