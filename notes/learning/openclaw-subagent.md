# OpenClaw Subagent 体系与并发任务能力深度调研：它到底擅长哪种“任务拆分”？

> **封面**：covers/OpenClaw Subagent体系与并发任务能力深度调研_cover.png

**OpenClaw 真正擅长的不是无限并行，而是建立在 session、announce、queue lane、task ledger 和 flow state 之上的受控并发。理解 `sessions_spawn`、`runtime:"acp"`、`sessions_send`、`TaskFlow` 各自解决哪一层问题，才知道它到底适合哪种任务拆分。**

如果只看 OpenClaw 的宣传或零散用法，你很容易把它理解成一个“可以随时拉起多个 agent 并行跑活”的通用多智能体框架。但把官方文档和相关 issue 连起来看之后，会发现更准确的理解应该是：**OpenClaw 确实支持把任务拆给子代理、ACP harness、后台任务和不同 agent 去执行，但它的并发模型不是无限并行，而是“带队列、带会话隔离、带可见性边界、带资源阈值”的受控并发。**

这点非常关键。因为你如果把 OpenClaw 当成一个随便 fan-out、随便共享上下文、随便跨线程恢复的任务图执行器，后面一定会撞到各种边界；反过来，如果你把它理解成“围绕 session 管理、消息路由、受控队列与背景任务账本构建起来的多层执行系统”，它的设计就会变得非常清晰 [[1]](https://docs.openclaw.ai/tools/subagents) [[2]](https://docs.openclaw.ai/concepts/session-tool) [[3]](https://docs.openclaw.ai/concepts/queue) [[4]](https://docs.openclaw.ai/gateway/configuration-reference) [[5]](https://docs.openclaw.ai/concepts/multi-agent) [[6]](https://docs.openclaw.ai/tools/acp-agents) [[7]](https://docs.openclaw.ai/automation/tasks) [[8]](https://docs.openclaw.ai/automation/taskflow)。

这篇文章重点回答五个问题：

1. OpenClaw 的 `subagent` 到底是什么，不是什么
2. `sessions_spawn` 怎么构成它的子任务拆分基础设施
3. OpenClaw 的并发到底发生在哪几层
4. 除了 subagent，它还有哪些拆分/并发执行能力
5. 这套体系的真实边界和当前缺口是什么

## 一、先校准一个前提：OpenClaw 里的“一个 agent”不是一个函数，而是一套独立运行面

`Multi-Agent Routing` 文档先把最基础的一件事说清楚了：在 OpenClaw 里，一个 agent 不是单纯的 prompt 名称，也不是一个模型 alias，而是一套完整运行面，至少包含：

- 独立 workspace
- 独立 `agentDir`
- 独立的认证配置
- 独立的 session 存储
- 独立的技能、规则和工具策略

文档甚至直接指出，session store 会保存在 `~/.openclaw/agents/<agentId>/sessions` 下面 [[5]](https://docs.openclaw.ai/concepts/multi-agent)。这意味着 OpenClaw 的多 agent 能力，从底层就不是“一个进程里起几个 prompt 角色”这么轻，而是有明显的**工作区、状态和权限隔离**。

这个前提决定了后面所有并发能力的边界：OpenClaw 不是先有“并发”，再勉强补隔离；而是先有 session/agent 隔离，再在隔离之上允许某些并发。

## 二、Subagent 的真正核心：不是“第二个模型”，而是“被 spawn 出来的子 session”

OpenClaw 的 subagent 体系，真正的核心入口不是某个抽象的 multi-agent planner，而是 `sessions_spawn`。`Session Tools` 文档已经把它和 `sessions_list`、`sessions_history`、`sessions_send` 放在同一组能力里，说明 OpenClaw 认为子代理本质上是**session 操作的一种延伸** [[2]](https://docs.openclaw.ai/concepts/session-tool)。

### 1. `sessions_spawn` 的基本语义

`sessions_spawn` 的关键参数包括：

- `task`
- `agentId`
- `model`
- `thinking`
- `runTimeoutSeconds`
- `thread`
- `mode`
- `cleanup`
- `sandbox`
- `runtime`

其中最关键的是三个：

- `runtime`
- `mode`
- `thread`

`runtime` 默认是 `subagent`，也可以显式设成 `acp`，把执行目标换成外部 coding harness [[2]](https://docs.openclaw.ai/concepts/session-tool) [[6]](https://docs.openclaw.ai/tools/acp-agents)。

`mode` 则区分：

- `run`：一次性运行
- `session`：保持成一个持久会话

而 `thread` 决定的是是否请求线程绑定。文档写得很明确：

- 默认是 `run`
- 如果 `thread: true` 且没显式写 `mode`，会偏向 `session`
- `mode: "session"` 需要 `thread: true` [[1]](https://docs.openclaw.ai/tools/subagents)

这已经说明一个核心事实：**OpenClaw 的 subagent 不是简单“平行再跑一个 LLM 调用”，而是显式创建一个 child session。**

### 2. `subagent` 的完成回传机制

`/subagents spawn` 和 `sessions_spawn` 都是非阻塞的，会立刻返回 `runId`，真正的结果通过一个后续 announce 步骤回传。官方文档说明，完成后子代理会向 requester 回传一段内部上下文，里面带：

- 结果正文
- 运行状态（success / error / timeout / unknown）
- 运行时长和 token 统计
- 供上层 agent 重写成正常用户口吻的交付指令

也就是说，OpenClaw 的子代理完成机制并不是“父代理同步 await 子代理”，而是：

- 先 spawn
- 子代理异步运行
- 运行结束后进行 announce
- 父层再根据 announce 继续组织结果 [[1]](https://docs.openclaw.ai/tools/subagents)

这是一种非常典型的**事件回传式 fan-out / fan-in** 结构，而不是同步 RPC 结构。

## 三、`run` 和 `session`：这是理解 OpenClaw subagent 的第一道分水岭

很多人以为 subagent 就是“后台跑一轮”；但真正决定它能不能做编排的，是 `run` 和 `session` 两种模式。

### 1. `run` 模式

这是最适合一次性任务切分的模式。比如：

- “去搜索这三个候选方案”
- “单独跑一轮长任务”
- “用另一个模型去生成备选答案”

`run` 模式的优点是简单：

- 不需要长期保持 child session
- 完成后直接 announce 回来
- 更适合 one-shot fan-out

但它的问题也很明确：**子 session 自己不会继续活着等后续消息。**

### 2. `session` 模式

如果你要做 orchestrator 模式，比如：

1. 主代理拉起一个 orchestrator subagent
2. orchestrator 再分批拉起多个 worker
3. worker 完成后逐个 announce 给 orchestrator
4. orchestrator 汇总后再回传主代理

那这时候光有 `run` 不够，因为 orchestrator 必须活着，才能继续接住 child announces。官方文档在 `Nested Sub-Agents` 里给出了明确的 announce chain：

1. depth-2 worker 完成，回传给 depth-1 orchestrator
2. depth-1 orchestrator 汇总后结束，再回传主代理
3. 主代理再把最终结果交付给用户 [[1]](https://docs.openclaw.ai/tools/subagents)

这本质上要求 depth-1 orchestrator 是一个**会继续存在的 session**，而不是一次性 run。

也正因为如此，`mode: "session"` 才是 OpenClaw 里真正支持编排链条的关键。

## 四、嵌套 subagent：OpenClaw 支持，但它不是无限树，而是受控深度

OpenClaw 并不是放任 session 无限递归 spawn。官方给了明确的层级和阈值控制：

- `maxSpawnDepth`
- `maxChildrenPerAgent`
- `maxConcurrent`
- `runTimeoutSeconds`

默认 `maxSpawnDepth` 是 1，也就是子代理默认不能再 spawn 孩子；如果你要让 subagent 继续担任 orchestrator，得显式把它调到 2 或更高 [[1]](https://docs.openclaw.ai/tools/subagents)。

### 1. 层级语义

文档对不同深度的工具权限给得非常清楚：

- **Depth 1 orchestrator**：当 `maxSpawnDepth >= 2` 时，可以拿到 `sessions_spawn`、`subagents`、`sessions_list`、`sessions_history`
- **Depth 1 leaf**：如果 `maxSpawnDepth == 1`，那就不拿 session tools
- **Depth 2 leaf worker**：永远没有 session tools，不能继续 spawn

这个设计非常值得注意。它说明 OpenClaw 并不是把“多 agent”做成一个任何节点都能继续裂变的自由系统，而是默认更倾向于：

- 一层 orchestrator
- 一层 worker
- 到此为止

这其实是一种非常工程化的保守设计：**允许分工，但不鼓励失控递归。**

### 2. Cascade stop

文档还定义了级联停止：

- 主会话里 `/stop` 会停止所有 depth-1 subagents，并继续 cascade 到 depth-2
- `/subagents kill <id>` 会停掉指定子代理，并级联停止它的孩子
- `/subagents kill all` 会停掉当前 requester 的全部 subagents [[1]](https://docs.openclaw.ai/tools/subagents)

这说明 OpenClaw 把 subagent 体系视为一个**可回收的子树**，不是一批完全失控的 detached 进程。

## 五、OpenClaw 的“并发”到底发生在哪几层

用户一提并发，最容易想象成“多个 agent 同时跑”。但在 OpenClaw 里，并发其实至少有四层。

### 1. 每个 session 内部：严格串行

`Command Queue` 文档说明得非常明确：同一个 session key 对应的 agent run 会进入 `session:<key>` 这条 lane，从而保证**同一 session 同时只有一个 active run** [[3]](https://docs.openclaw.ai/concepts/queue)。

这是 OpenClaw 最重要的安全前提之一。因为它要保护：

- session 文件
- 日志
- CLI stdin
- 工具调用状态

所以如果你在同一 session 上幻想“多轮并发写入上下文”，OpenClaw 的设计就是明确反对这件事的。

### 2. 主代理层：受全局 lane 控制的并行

不同 session 可以并行，但还要受到全局 lane 的限制。官方文档给出的模型是：

- 每个 session 自己有一条 session lane
- 然后还会进入一个 global lane
- `main` lane 默认并发上限是 4
- `subagent` lane 默认并发上限是 8

所以 OpenClaw 的并发不是“每个 session 自由跑”，而是：

- 同 session 串行
- 不同 session 可并行
- 全局再限流一次 [[3]](https://docs.openclaw.ai/concepts/queue)

### 3. Subagent 层：单独的 `subagent` lane

官方文档明确说，subagent 的 lane 名就是 `subagent`，并发上限由 `agents.defaults.subagents.maxConcurrent` 控制，默认是 8 [[1]](https://docs.openclaw.ai/tools/subagents) [[4]](https://docs.openclaw.ai/gateway/configuration-reference)。

这很重要，因为它意味着 subagent 并不是和主聊天流完全混在一起，而是有自己独立的一条背景并发车道。

但问题也正出在这里：它目前仍然是**单一一条 `subagent` lane**。issue `#10467` 就指出，所有 subagent 都被挤进同一个全局子代理车道里，结果容易出现：

- 研究类慢任务把车道占满
- 高优先级监控类任务被阻塞
- 复杂多路径编排难以隔离不同任务支路

所以社区才提议给 `sessions_spawn` 增加可选 `lane` 参数，让不同类型的 subagent 进入不同的 queue lane [[9]](https://github.com/openclaw/openclaw/issues/10467)。

这说明一个非常现实的结论：**OpenClaw 现在已经支持 subagent 并发，但它更接近“共享一个受限池”的并发，不是“按任务类别隔离 lane”的高级并发。**

### 4. 背景任务层：任务记录与通知层的并行

`Background Tasks` 文档又补上了另一个重要事实：ACP、subagent、cron jobs、CLI operations 都会创建 task record。任务有自己的生命周期：

- `queued`
- `running`
- `succeeded`
- `failed`
- `timed_out`
- `cancelled`
- `lost`

但文档强调得非常清楚：**tasks 是记录，不是调度器。** 它不决定什么时候运行，而是负责记录 detached work 的状态、通知和审计 [[7]](https://docs.openclaw.ai/automation/tasks)。

这意味着 OpenClaw 的并发还有一个账本层：

- 队列层解决“谁先跑、并发上限多少”
- tasks 层解决“跑过没有、结果怎样、怎么通知”

很多系统只有队列，没有 task ledger；OpenClaw 在这点上明显更工程化。

## 六、除了 subagent，OpenClaw 还有哪些拆分并发执行能力

如果把范围放宽到“拆分并发执行任务”，OpenClaw 至少还有四套能力，不应该都算到 subagent 头上。

### 1. `sessions_send`：跨 session 发消息

`Session Tools` 文档里，`sessions_send` 支持：

- `timeoutSeconds: 0`，即 fire-and-forget
- 设置 timeout，等待对方 inline reply

这意味着如果你已经有一个存在中的 session，不一定非要再 `spawn` 一个新的。你也可以：

- 先保留一个长期 session
- 后续用 `sessions_send` 往里投递任务
- 按需选择异步或等待结果 [[2]](https://docs.openclaw.ai/concepts/session-tool)

这其实是 OpenClaw 里非常容易被低估的一种能力：不是每一次任务拆分都需要 spawn，一个已存在 session 的 message-based steering 本身就是一种任务分派能力。

### 2. ACP sessions：把任务拆给外部 coding harness

`ACP Agents` 文档说明，OpenClaw 可以通过 `sessions_spawn` 配合 `runtime: "acp"` 拉起外部 harness，比如 Codex、Claude Code、Gemini CLI 等 [[6]](https://docs.openclaw.ai/tools/acp-agents)。

这和普通 subagent 的本质区别是：

- 普通 subagent 仍然是 OpenClaw 自己的 agent runtime
- ACP session 则是交给外部 harness 执行

这让 OpenClaw 的“任务拆分”不只是内部多 agent，而是可以把 coding、repo 操作、持续会话交给专门的外部代理环境。

而且 ACP 还支持：

- `resumeSessionId`
- `streamTo: "parent"`
- `/acp steer`
- `/acp close`
- `/acp status`

也就是说，ACP 更像是 OpenClaw 内建的一种**外部执行器接入层**，而不是单纯的 subagent 变体 [[6]](https://docs.openclaw.ai/tools/acp-agents)。

### 3. Queue modes：不是并行，但能改变任务拆解方式

`Command Queue` 文档给出的几种 queue mode 其实也会影响任务拆分策略：

- `steer`
- `followup`
- `collect`
- `steer-backlog`
- `interrupt`

它们不直接创建新的 subagent，但会改变一连串消息在当前 session 中如何进入后续执行。比如：

- `collect` 适合把多个短消息合并成一次 follow-up turn
- `steer` 适合把新指令直接插入当前执行流
- `followup` 适合等待当前任务结束后再做下一轮

这说明 OpenClaw 的“任务拆分”并不只发生在 `spawn` 上；有些任务拆分其实是通过**排队策略**完成的 [[3]](https://docs.openclaw.ai/concepts/queue)。
### 4. TaskFlow：更高层的流程编排视图

`TaskFlow` 文档不是在教你怎么开更多子代理，而是在说明：OpenClaw 可以把 detached tasks 组织成 flow，并支持：
- `Managed` 模式：TaskFlow 自己拥有生命周期
- `Mirrored` 模式：TaskFlow 观察外部创建的 task，并同步 flow 状态

这意味着如果你真正想构建的是“多步骤流程”，那么 subagent 只是执行单元之一，tasks 是状态账本，而 flows 则是更高一层的流程视图 [[8]](https://docs.openclaw.ai/automation/taskflow)。

从系统结构上看，OpenClaw 更像：
- `sessions_spawn` / ACP：执行单元
- queue lanes：并发控制
- tasks：任务账本
- flows：流程状态机

如果只盯着 subagent，就会把整套能力看扁。

## 七、一个直接可用的能力选型表

如果把 OpenClaw 的这些能力放在一起比较，你会发现它们并不是彼此替代，而是分别解决不同层面的任务拆分问题。

| 你的目标 | 更适合的能力 | 为什么 |
|------|--------------|--------|
| 把一个大任务拆成几个独立子问题并行做完再汇总 | `sessions_spawn` + `runtime:"subagent"` + `mode:"run"` | 最自然的 one-shot fan-out |
| 需要一个中间 orchestrator 持续接收 worker 结果 | `sessions_spawn` + `mode:"session"` + `maxSpawnDepth >= 2` | 需要持久 child session 承接 announce chain |
| 需要长期 coding worker，并支持恢复、steer、状态检查 | `runtime:"acp"` | ACP 自带 resume、status、steer、close 能力 |
| 已经有一个存在中的 session，只想继续塞新任务进去 | `sessions_send` | 不必反复 spawn 新 session |
| 需要记录 detached work 的状态、通知和取消 | `tasks` | task 是账本和通知层，不是调度器 |
| 需要把多个任务组织成更上层的流程 | `TaskFlow` | flow 负责步骤和同步模式，不直接替代执行单元 |
| 只想在当前会话里控制多条消息如何进入执行 | queue modes | 这是调度入口，不是新的子执行器 |

这个对照表背后其实有一个很重要的判断：**不要拿 `subagent` 去替代所有 detached work，也不要拿 `TaskFlow` 去替代具体执行器。** 在 OpenClaw 里，这些能力是分层设计的。

## 八、一个完整案例：主代理、orchestrator 与 worker 是怎么协作的

假设你要做一个“代码问题定位 + 方案比较 + 风险摘要”的复杂任务。比较合理的拆法是：

1. 主代理接到用户请求
2. 主代理 spawn 一个 `mode:"session"` 的 orchestrator
3. orchestrator 再 spawn 三个 worker：
   - Worker A：定位报错链路
   - Worker B：对比两个修复方案
   - Worker C：评估潜在回归风险
4. 三个 worker 完成后分别 announce 给 orchestrator
5. orchestrator 汇总三份结果，再 announce 给主代理
6. 主代理把最终结果改写成用户可读的交付

这个流程里，四类能力分别负责不同事情：

- `sessions_spawn`：负责真正把执行单元拆出来
- `mode:"session"`：保证 orchestrator 在等待期间不会自己结束
- `subagent` lane：控制后台子任务并发上限
- `tasks`：记录每个 detached run 的状态

如果你把这个案例换成普通 `mode:"run"`，orchestrator 很可能会在第一轮结束后就退出，后续 child announces 就没有稳定落点了。这也是为什么文档里的嵌套模型，不是“开更多 agent”这么简单，而是**必须把 session 生命周期设计进去** [[1]](https://docs.openclaw.ai/tools/subagents) [[7]](https://docs.openclaw.ai/automation/tasks)。

再换一个场景，如果这三个 worker 中有一个是“让 Codex 直接改 repo 并跑测试”，那它就未必适合普通 subagent，更适合改成 `runtime:"acp"`。因为这时候你更需要：

- `resumeSessionId`
- `/acp status`
- `/acp steer`
- `cwd` 和 runtime option 控制

这说明 OpenClaw 的“并发任务拆分”真正难的地方，不是能不能拆，而是**拆完以后每一块应该落到哪种执行器上。**

## 九、这套体系真正擅长的几种任务拆分模式

### 1. One-shot fan-out

最适合的场景是：

- 多个独立研究子问题
- 多个候选方案并行生成
- 慢工具任务后台执行，不阻塞主对话

这时最适合：

- 主代理保持当前用户交互
- 多个 subagent 作为一次性 `run` 去后台执行
- 结束后 announce 回来，再由主代理汇总

这是 OpenClaw 当前最成熟、最自然的并发模式。

### 2. 两层 orchestrator-worker

如果你愿意显式配置：

- `maxSpawnDepth >= 2`
- 合理的 `maxChildrenPerAgent`
- 合理的 `maxConcurrent`

那 OpenClaw 也能支持一个比较克制的 orchestrator-worker 模式：

- 主代理只做用户交互和总调度
- depth-1 subagent 做 orchestrator
- depth-2 workers 跑具体任务

但这里要清楚，OpenClaw 的设计并不鼓励无限深层多 agent 树；它支持的是一个**相对保守的两层拆分模型** [[1]](https://docs.openclaw.ai/tools/subagents)。

### 3. 外部编码执行器并行

如果任务本质是 coding harness 驱动，比如：

- 让 Codex 跑一套改代码流程
- 让 Claude Code 继续修测试
- 让 Gemini CLI 在另一条线程里做独立实验

那更适合走 ACP，而不是普通 subagent。因为 ACP 自带：

- 外部 runtime
- session resume
- steer/status/close 控制
- thread/current-conversation binding [[6]](https://docs.openclaw.ai/tools/acp-agents)

这类能力明显更适合“长期 coding worker”而不是轻量级内部 fan-out。

## 十、真实边界：OpenClaw 现在还不是什么

如果只看 happy path，很容易高估 OpenClaw 的 subagent 能力。但几个文档和 issue 合起来，其实已经把当前边界暴露得很清楚。

### 1. `mode: "session"` 现实里并不是全平台等价可用

issue `#23414` 指出，`mode: "session"` 目前要求 `thread: true`；而 thread binding 在实践上又依赖特定 channel 的 `subagent_spawning` 支持，所以在非 Discord 渠道上，官方文档里那个嵌套 orchestrator 模式会遇到现实阻碍 [[10]](https://github.com/openclaw/openclaw/issues/23414)。

这意味着文档层面的“支持 nested subagents”，和所有渠道上“都能跑通 persistent orchestrator”，目前并不完全等价。

### 2. announce 是 best-effort，不是 durable callback

官方文档直接写了：sub-agent announce 是 best-effort；如果 gateway 重启，pending announce back work 会丢失 [[1]](https://docs.openclaw.ai/tools/subagents)。

这句话非常重要，因为它直接限制了 subagent 在强工作流场景里的可靠性。你可以拿它做工程工具，但不能默认它已经是一个像 Durable Workflow 那样的严格持久编排引擎。

### 3. subagent 目前还是 UUID 会话，不是持久命名线程

issue `#19780` 直接点出了这个问题：subagent 的 session key 是 `agent:<id>:subagent:<uuid>`，如果 gateway 重启，没办法按稳定名字把这类 topic-oriented 子线程重新接起来 [[11]](https://github.com/openclaw/openclaw/issues/19780)。

这意味着 OpenClaw 当前对“长期存在的研究线程、监控线程、规划线程”支持得还不够自然。你能做，但往往要靠：

- 单独 agent 配置
- 状态文件
- resume prompt
- 或外部流程系统

### 4. 并发是共享池，不是多 lane 调度系统

issue `#10467` 提醒了另一个经常被忽视的问题：所有 subagent 都挤在单一 `subagent` lane 里 [[9]](https://github.com/openclaw/openclaw/issues/10467)。

这说明 OpenClaw 当前的并发更像：

- 有背景 lane
- 有上限
- 有会话隔离
- 但还没有足够细的 lane-level QoS

所以它适合“适度并发”，还不算“精细资源调度”。

## 十一、一个更准确的总结：OpenClaw 更像“会话化的并发系统”，不是通用 DAG 引擎

如果让我给一个总判断，我会说：OpenClaw 的 subagent 体系最强的地方，不是它能 spawn 很多 agent，而是它把任务拆分建立在**session、announce、queue lane、task ledger、flow state** 这些一致的系统概念上。

它做对了几件非常重要的事：

- 用 `sessions_spawn` 把子任务拆分做成显式能力
- 用 `run/session` 区分 one-shot 和持久会话
- 用 `maxSpawnDepth`、`maxChildrenPerAgent`、`maxConcurrent` 控制复杂度
- 用 `tasks` 记录 detached work 的状态
- 用 `flows` 承接更高层流程同步
- 用 ACP 把外部 coding harness 纳入同一套调度外壳

但它目前也明显不是：

- 任意深度、任意平台都一致可用的持久多 agent 编排系统
- 支持多 lane QoS 的高阶子任务调度器
- 拥有强持久完成回调和严格重放语义的 durable workflow engine

所以如果你问：“OpenClaw 里的 subagent 体系成熟吗？”

更准确的回答应该是：**它已经足够支撑一批非常实用的 fan-out / fan-in 和两层 orchestrator 模式，但它当前最适合的是“受控并发 + 会话化编排”，而不是无限扩张的自治 agent 网络。**

这也是为什么在 OpenClaw 里讨论并发，不能只看 `sessions_spawn`，还必须一起看：

- queue
- session visibility
- ACP
- background tasks
- TaskFlow
- 以及几条直接暴露现实瓶颈的 issue

只有把这些拼起来，你才会知道 OpenClaw 擅长拆什么任务，不擅长拆什么任务。

## 参考来源

| 编号 | 来源 | 用途 |
|------|------|------|
| [1] | [Sub-Agents - OpenClaw](https://docs.openclaw.ai/tools/subagents) | subagent 的 spawn、announce、嵌套、并发和限制 |
| [2] | [Session Tools - OpenClaw](https://docs.openclaw.ai/concepts/session-tool) | `sessions_list` / `sessions_history` / `sessions_send` / `sessions_spawn` |
| [3] | [Command Queue - OpenClaw](https://docs.openclaw.ai/concepts/queue) | lane、session 串行、全局并发与 queue mode |
| [4] | [Configuration Reference - OpenClaw](https://docs.openclaw.ai/gateway/configuration-reference) | `tools.sessions`、`tools.sessions_spawn`、`agents.defaults.subagents` 等配置 |
| [5] | [Multi-Agent Routing - OpenClaw](https://docs.openclaw.ai/concepts/multi-agent) | agent/workspace/session 的基础隔离模型 |
| [6] | [ACP Agents - OpenClaw](https://docs.openclaw.ai/tools/acp-agents) | `runtime:"acp"`、resume、binding、ACP 控制面 |
| [7] | [Background Tasks - OpenClaw](https://docs.openclaw.ai/automation/tasks) | task ledger、任务状态、通知与 detached work |
| [8] | [TaskFlow - OpenClaw](https://docs.openclaw.ai/automation/taskflow) | flow 的托管/镜像模式，以及和 tasks 的关系 |
| [9] | [Issue #10467: Multi-lane concurrency support for sub-agents](https://github.com/openclaw/openclaw/issues/10467) | 单一 subagent lane 的并发瓶颈 |
| [10] | [Issue #23414: mode="session" requires thread=true](https://github.com/openclaw/openclaw/issues/23414) | persistent orchestrator 在非 Discord 渠道上的现实限制 |
| [11] | [Issue #19780: Persistent named sessions for sub-agents](https://github.com/openclaw/openclaw/issues/19780) | 持久命名 subagent session 的缺口 |
