# OpenClaw 事件体系与钩子体系深度解析：它到底有没有“对话结束钩子”？

> **封面**：covers/OpenClaw事件体系与钩子体系深度解析_cover.png

**OpenClaw 真正复杂的地方，不是它有没有钩子，而是它同时存在 runtime stream、internal hooks、plugin hooks 与 webhook 四层能力。只有把 `agent_end`、`session_end`、`message_sent` 和 ACP completion 的边界拆开，才不会把编排问题误解成单一的“结束回调”问题。**

很多人第一次接触 OpenClaw，会把 `event stream`、`internal hook`、`plugin hook`、`webhook` 这四套东西混成一层，最后问出一个看似简单、实际却很容易问偏的问题：**OpenClaw 到底有没有 agent 对话完毕之后触发的钩子？**

如果只给一句答案，这个问题会被回答成“有”或者“没有”；但如果真的要把系统理解透，就会发现这个问题至少要拆成三层：

- 你问的是 **一次 agent run 结束**，还是 **一个 session 结束**
- 你问的是 **运行时事件流**，还是 **HOOK.md 那套内部 hooks**
- 你问的是 **普通 agent 完成**，还是 **spawn 出来的子会话 / ACP session 完成**

OpenClaw 官方文档已经把 agent loop、hooks、plugin architecture 和 webhook ingress 分成了不同章节，这本身就说明：它不是一套单一的“统一钩子系统”，而是一个**多层事件面 + 多层扩展面**的架构 [[1]](https://docs.openclaw.ai/automation/hooks) [[2]](https://docs.openclaw.ai/concepts/agent-loop) [[3]](https://docs.openclaw.ai/plugins/architecture) [[4]](https://docs.openclaw.ai/automation/webhook)。

这篇文章想回答的不只是“有没有钩子”，而是四个更重要的问题：

1. OpenClaw 的事件到底分哪几层
2. 每层事件分别是“观察型”还是“干预型”
3. `agent_end`、`session_end`、`lifecycle.end`、`subagent_ended` 各自是什么意思
4. 为什么社区仍然在持续补 `session:end`、`acp:session:complete`、`agent:response:end` 这类事件

## 一、先把总图看清：OpenClaw 不是一套钩子，而是四套接口面

从官方文档看，OpenClaw 至少有四个彼此相关但语义不同的接口层。

### 1. 运行时事件流

在 `Agent Loop` 文档里，OpenClaw 把 agent 执行期间产生的流式事件拆成三类：

- `lifecycle`
- `assistant`
- `tool`

其中 `lifecycle` 又会区分 `start`、`end`、`error` 三个阶段。这一层最接近“运行时真相”，因为它直接对应 agent loop 的执行过程：接收请求、建立 session、组 prompt、调用模型、执行工具、流式返回、结束或报错 [[2]](https://docs.openclaw.ai/concepts/agent-loop)。

这意味着，如果你只是想知道“某次 agent run 结束了没有”，最原始、最不带解释的一层其实不是 hook，而是：

- 监听 `lifecycle phase=end`
- 或通过 `agent.wait` 等待 `ok | error | timeout`

这层更像**执行总线**，适合前端、stream watcher、外部编排器，而不是直接拿来做高阶业务语义。

### 2. Internal Hooks / Gateway Hooks

`automation/hooks` 里的 `HOOK.md + handler.ts`，是一套更偏本地自动化的 hook 体系。它的装载方式不是在代码里手动注册，而是：

- Gateway 启动时扫描目录
- 解析 `HOOK.md`
- 检查依赖、环境变量、平台、配置是否满足
- 再动态加载 handler，并按事件注册 [[1]](https://docs.openclaw.ai/automation/hooks)

这套体系的特点是：

- 声明式
- 自动发现
- 适合轻量工作流自动化
- 更偏 Gateway 侧事件，而不是 agent runtime 的所有细粒度事件

### 3. Plugin Hook API

真正意义上“能深入 agent 生命周期”的扩展点，主要在 Plugin Hook API。官方文档列出了完整的 plugin hook reference，包括：

- `before_model_resolve`
- `before_prompt_build`
- `before_agent_start`
- `before_agent_reply`
- `agent_end`
- `session_start`
- `session_end`
- `before_tool_call`
- `after_tool_call`
- `message_received`
- `message_sent`
- `subagent_spawned`
- `subagent_ended`

这一层不是简单“收到一个事件做点日志”，而是可以在不少节点真正改行为。比如：

- `before_tool_call` 可以改参数、阻断执行、要求审批
- `before_agent_reply` 可以直接接管这一轮回复
- `before_prompt_build` 可以往 prompt 前后注入上下文

所以，如果你问“OpenClaw 有没有能在 agent 完成后做事的正式扩展点”，最准确的答案其实是：**有，首选看 Plugin Hook API 的 `agent_end`。** [[1]](https://docs.openclaw.ai/automation/hooks) [[3]](https://docs.openclaw.ai/plugins/architecture)

### 4. Webhooks

`/hooks/wake`、`/hooks/agent`、`/hooks/<name>` 这组 HTTP 入口看起来名字里也有 `hooks`，但它们和前面三层不是一回事。它们的方向是：**外部系统把事件送进 OpenClaw**，而不是 OpenClaw 内部事件向外发散 [[4]](https://docs.openclaw.ai/automation/webhook)。

换句话说：

- Webhooks 是 **外部触发入口**
- Internal / Plugin hooks 是 **内部生命周期扩展点**
- Event stream 是 **运行时状态流**

很多人把这三件事混起来，最后就会在错误的层里找“结束钩子”。

## 二、为什么“有没有对话结束钩子”这个问题容易问错

表面上看，“对话结束”像是一件事；实际上在 OpenClaw 里至少有四种不同的“结束”。

### 1. 一次 agent run 结束

这最接近 `agent_end`，也最接近 `lifecycle phase=end`。

它描述的是：**这次 agent 执行完成了**。可能是一轮响应结束，可能包含若干工具调用，也可能因为超时或错误提前终止。`Agent Loop` 文档明确说明，OpenClaw 在执行过程中会桥接 pi-agent-core 的生命周期事件，并将其投递到 `lifecycle` stream；如果底层循环没有发出结束事件，上层还会补发 end/error，确保 `agent.wait` 能等到一个确定结果 [[2]](https://docs.openclaw.ai/concepts/agent-loop)。

所以对外部观察者来说，“这轮跑完了”这个事实是存在的。

### 2. 一个 session 结束

这件事和 `agent_end` 并不等价。OpenClaw 的 session 是更高一级的容器，里面会包含：

- 会话元数据
- 历史消息
- 工具执行痕迹
- 可能的 compaction 结果
- 子代理 / 子会话的关联信息

文档里已经有 plugin hook 级别的 `session_start` 和 `session_end`，但在 internal hook 那套事件名里，官方同时又写了一个很重要的注记：`session:start` 和 `session:end` 已经存在于 Plugin Hook API，但**尚未作为 internal hook event keys 完整进入那条内部 hook 流** [[1]](https://docs.openclaw.ai/automation/hooks)。

这意味着：

- 从 plugin 的角度看，session 生命周期已经被建模
- 从 HOOK.md 的内部事件名角度看，这组能力还没有完全对齐

后来社区又专门提了 `session:end internal hook event` 的 feature request，也侧面证明了这件事：**不是没有“结束”的概念，而是不同扩展层对“结束”的暴露不一致。** [[6]](https://github.com/openclaw/openclaw/issues/10142)

### 3. 一条消息发完

很多自动化场景里，开发者其实想要的是“回复已经发出”，不是“agent 整个 run 结束”。这时更适合看的不是 `agent_end`，而是消息流钩子，例如：

- `message_sending`
- `message_sent`

文档明确给了这组事件，还说明 `message_sending` 支持 `cancel` 语义，是一个可拦截点；而 `message_sent` 更偏观察型，适合审计和回执 [[1]](https://docs.openclaw.ai/automation/hooks)。

### 4. 一个 spawned child session / ACP session 完成

这是最容易和“agent 对话结束”混淆的一层。官方 issue `#57671` 明确提出：当 orchestrator 通过 `sessions_spawn` 拉起一个 spawned ACP session 后，**系统并没有一个足够可靠的一等事件** 来告诉父编排器：“子会话已经完成” [[5]](https://github.com/openclaw/openclaw/issues/57671)。

这件事之所以关键，是因为 orchestration 里的“完成”不是为了显示给用户看，而是为了驱动下一步：

- 更新任务状态
- 汇总多个子任务结果
- 做 post-completion protocol
- 失败时升级告警

issue 里列出的现有替代方案包括：

- 往父会话里注 system message
- 轮询 `sessions_list`
- 用外部脚本监听 stream，然后再手动 `openclaw message send`

这些方案都能用，但都不够优雅。也正因为如此，社区才提议新增 `acp:session:complete` 这样的事件。这个 issue 本身就是一个非常好的证据：**OpenClaw 的“普通 agent 完成”已经有一定支持，但“子会话完成可编排”这件事仍然是一个演进中的缺口。** [[5]](https://github.com/openclaw/openclaw/issues/57671)

## 三、Internal Hooks：适合做自动化，不等于拿到了全部生命周期

如果只看 `automation/hooks` 文档，OpenClaw 的内部 hooks 已经很像一个成熟的本地事件脚本系统。

它有清晰的 `HOOK.md` 结构：

- `name`
- `description`
- `homepage`
- `metadata.openclaw.events`
- `requires`
- `os`
- `env`
- `bins`
- `config`

它也有清晰的装载顺序和优先级：

- bundled
- plugin
- managed / extra dirs
- workspace

随后再按 eligibility 检查是否可用 [[1]](https://docs.openclaw.ai/automation/hooks)。

这套设计很实用，因为它让 hook 变成一个“可发现、可启停、可审查”的模块，而不是到处散落的回调函数。

但你不能因为它“像一个 hooks 系统”，就默认它等于“OpenClaw 所有 hook 能力的全集”。官方文档已经清楚地区分了：

- Internal hooks 偏 Gateway 事件
- Plugin hooks 偏 agent/tool 生命周期

所以内部 hooks 更适合的工作包括：

- `/new`、`/reset`、`/stop` 之类命令后触发一些动作
- 在 `agent:bootstrap` 时注入额外上下文文件
- 记录 `session:patch` 变化
- 在 `message:received`、`message:preprocessed`、`message:sent` 等节点做日志、过滤、派生逻辑

如果你的需求是“在一次回复结束时做后处理”，内部 hooks 并不是最佳入口；如果你的需求是“消息进来以后，做预处理或事件转发”，它又非常顺手。

## 四、Plugin Hook API：这才是 OpenClaw 真正的生命周期手术台

要理解 OpenClaw 的钩子体系，最重要的是把 Plugin Hook API 看成一个“可插刀的位置总表”。它比 internal hooks 更底层，也更贴近 agent loop 的实际运行。

### 1. Prompt 与模型阶段

这部分事件包括：

- `before_model_resolve`
- `before_prompt_build`
- `before_agent_start`
- `before_agent_reply`
- `llm_input`
- `llm_output`

这里最值得注意的是：OpenClaw 并不是只给你一个“最后通知一下”的事件，而是把从**选模型**、到**拼 prompt**、到**真正生成回复前**的关键节点都暴露出来了 [[1]](https://docs.openclaw.ai/automation/hooks)。

这背后的设计哲学其实很清楚：系统认为“agent 的行为”不是从第一 token 才开始，而是从模型解析、上下文组装、权限判断就已经开始。

### 2. Tool 执行阶段

`before_tool_call` 是整套体系里最有工程价值的钩子之一。因为它不只是通知你“要调用工具了”，而是允许你：

- 覆盖参数
- 阻断执行
- 给出阻断原因
- 插入人工审批

文档甚至直接给出了 `requireApproval` 结构，包含：

- `title`
- `description`
- `severity`
- `timeoutMs`
- `timeoutBehavior`
- `onResolution`

这说明 OpenClaw 在 hook 设计上并没有把“审批”当作外挂逻辑，而是把它内建成一种正式的控制分支 [[1]](https://docs.openclaw.ai/automation/hooks)。

### 3. 结束态阶段

对本文主题来说，最关键的是这组：

- `agent_end`
- `session_end`
- `subagent_ended`
- `message_sent`

这四个名字都和“结束”有关，但适用场景完全不同：

| 事件 | 更接近什么结束 | 适合干什么 |
|------|----------------|------------|
| `agent_end` | 一次 agent run 结束 | 收尾分析、审计、触发后续动作 |
| `session_end` | 一个 session 生命周期结束 | 会话级工作流、资源清理、回写状态 |
| `subagent_ended` | 子代理结束 | 多 agent 编排、子任务收敛 |
| `message_sent` | 对外消息已成功发出 | 渠道审计、回执、外部通知 |

很多误解都来自把这四个事件混成一个“完成钩子”。

## 五、OpenClaw 为什么还在持续补事件

如果文档里已经有不少事件，为什么 GitHub 上还不断有人提新的 hook request？原因不在于“原系统没有 hook”，而在于**不同层的语义颗粒度还没有完全补齐**。

### 1. `session:end` internal hook event

issue `#10142` 的诉求很直接：需要一个 internal hook 层的 `session:end`，用于跟 Temporal 这样的外部工作流系统对接 [[6]](https://github.com/openclaw/openclaw/issues/10142)。

这类需求不是“想多一个事件名”，而是因为：

- plugin 层有概念，不代表 internal hook 层就能直接消费
- workflow engine 想等的是“会话完成信号”，不是“让 agent 自己记得最后执行一个命令”

这个 issue 的存在本身说明，OpenClaw 已经在往“更强的编排友好性”推进，但目前不同层仍有能力错位。

### 2. `acp:session:complete`

issue `#57671` 的价值更大，因为它指出了 orchestration 里的一个真实缺口：**spawn child 和 ordinary agent end 不是同一件事** [[5]](https://github.com/openclaw/openclaw/issues/57671)。

如果你只有 `agent_end`，父编排器并不能天然知道“这个 child session 结束了，而且该触发收口协议了”。所以社区提出 `acp:session:complete`，本质上不是在重复造轮子，而是在补一条**编排级别的完成事件**。

### 3. 更细粒度的 agent lifecycle

issue `#7724` 和 `#5279` 讨论的，则是另外一类诉求：不是“有没有结束”，而是“结束之前有没有足够细的阶段事件” [[7]](https://github.com/openclaw/openclaw/issues/7724) [[8]](https://github.com/openclaw/openclaw/issues/5279)。

它们提到的事件包括：

- `agent:thinking:start`
- `agent:thinking:end`
- `agent:response:start`
- `agent:response:end`
- `agent:tool:start`
- `agent:tool:end`
- `agent:response`
- `tool:complete`

这说明社区已经不满足于“粗粒度生命周期点”。一旦开始做硬件联动、presence 指示灯、长链路编排、外部审计、成本统计，就会希望系统暴露更细的边界。

## 六、两个实际场景：你该用哪种钩子

### 场景一：给危险工具调用加审批门

假设你希望 OpenClaw 在执行高风险 shell 命令前，不是简单弹一条提示，而是正式进入审批流程。那么最合适的入口不是 `message_received`，也不是 `agent_end`，而是 `before_tool_call`。

原因很简单：

- 你想拦的是“工具执行前”
- 你需要的是“改参数 / 阻断 / 审批”能力
- 这是一个控制点，不是观察点

在这个场景里，OpenClaw 的 Plugin Hook API 已经足够成熟：它不仅能要求审批，还定义了 timeout 行为和回调处理逻辑。这种设计比“让 agent 自己在 prompt 里学会谨慎”稳定得多 [[1]](https://docs.openclaw.ai/automation/hooks)。

### 场景二：主编排器等待子任务全部完成后再收口

假设一个 orchestrator agent 会并行 spawn 三个子会话，分别生成代码、跑测试、整理变更摘要。主编排器真正关心的不是其中某条消息发出，而是：

- 哪个 child 完成了
- 成功还是失败
- 最终结果在哪里
- 是否已经到齐，能否进入汇总阶段

这时：

- `message_sent` 太表层
- `agent_end` 太偏当前执行体自身
- `session:patch` 太低层，需要自己解释 patch
- 轮询 `sessions_list` 又太脆弱

所以 `acp:session:complete` 这类事件的价值就会立刻凸显出来。它不是锦上添花，而是让编排系统从“靠约定和脚本 glue”升级成“靠正式事件驱动”的关键一步 [[5]](https://github.com/openclaw/openclaw/issues/57671)。

## 七、一个更实用的理解框架：观察、干预、编排

如果你准备真正使用 OpenClaw，而不是只停留在概念层，我建议用三个词来判断应该看哪种事件。

### 1. 观察

你只是想知道发生了什么，不打算改流程。

优先看：

- `lifecycle`
- `assistant`
- `tool`
- `message_sent`
- `agent_end`

### 2. 干预

你希望在执行中改行为。

优先看：

- `before_model_resolve`
- `before_prompt_build`
- `before_agent_reply`
- `before_tool_call`
- `message_sending`
- `before_message_write`

### 3. 编排

你希望系统把一次 agent 行为纳入更大的任务流。

优先看：

- `session_start`
- `session_end`
- `subagent_spawned`
- `subagent_ended`
- `agent.wait`
- 外部 workflow 协调机制
- 以及仍在补齐中的 `session:end` internal hook、`acp:session:complete` 之类能力

这个框架最大的好处是：它会逼着你先问“我到底想做什么”，而不是一上来就找一个名字最像“完成”的 hook。

## 八、三个最常见的误判

把 OpenClaw 的 hook 系统用错，往往不是因为文档太少，而是因为语义层次没有对齐。最常见的误判有三个。

### 1. 把 `agent_end` 当成“所有结束事件”的总开关

这是最常见的误判。`agent_end` 的确很重要，但它更偏向**一次 agent run 的收尾**。如果你的业务真正依赖的是：

- 某条消息已经送达用户
- 某个 session 生命周期已经结束
- 某个 child session 已完成且需要驱动父编排器继续

那直接把这些语义都压在 `agent_end` 上，后面一定会开始混乱。它能解决一部分问题，但解决不了全部“完成态”问题。

### 2. 把 Webhook 当成 Hook

`/hooks/agent`、`/hooks/wake` 这些入口是**把外部事件喂进 OpenClaw**，不是 OpenClaw 内部生命周期向外发射的回调接口 [[4]](https://docs.openclaw.ai/automation/webhook)。

如果一个团队把 webhook ingress 和 internal/plugin hooks 混为一谈，后面通常会发生两件事：

- 在 webhook 配置里寻找本不存在的“结束回调”
- 把所有外部系统集成都硬塞到 agent prompt 或 shell glue 里

这两种做法短期能跑，长期都很难维护。

### 3. 把 `session:patch` 当成 workflow 事件总线

`session:patch` 很有价值，因为它能告诉你 session 的哪些字段变了；但它本质上仍然是**状态变化通知**，不是高层语义已经解释好的编排事件 [[1]](https://docs.openclaw.ai/automation/hooks)。

所以它适合：

- 配置审计
- 调试状态流
- 观测 session 元数据变更

但如果你想做的是“任务结束后推进下一步 workflow”，你大概率会更希望拿到的是 `session_end`、`agent_end`、`subagent_ended` 或更明确的 `acp:session:complete` 这类事件，而不是自己再从 patch 里猜状态。

## 九、一个直接可用的选型表

如果把前面的分析压缩成工程决策，最实用的方式其实不是背事件名，而是先按问题类型选入口。

| 你的目标 | 优先看的能力 | 不建议先看 |
|------|--------------|--------------|
| 想知道一轮 agent 是否结束 | `lifecycle end`、`agent.wait`、`agent_end` | `message_sent` |
| 想在生成回复前改 prompt 或接管回复 | `before_prompt_build`、`before_agent_reply` | `agent_end` |
| 想在执行工具前拦截、审批、改参数 | `before_tool_call` | `message_received` |
| 想记录消息是否真的发出 | `message_sending`、`message_sent` | `agent_end` |
| 想知道 session 生命周期边界 | `session_start`、`session_end` | `agent_end` 单独承担全部语义 |
| 想做父子代理编排 | `subagent_spawned`、`subagent_ended`、外部协调机制 | 只靠 system message 注入 |
| 想对接外部业务系统触发 OpenClaw | `/hooks/agent`、`/hooks/wake`、`/hooks/<name>` | internal/plugin hooks |

这张表最核心的作用，是防止你在错误的层里找能力。很多“OpenClaw 这里是不是缺一个钩子”的问题，真正答案往往是：**钩子不一定缺，缺的是你把问题放到了不合适的层。**

## 十、我的判断：OpenClaw 的 hook 体系已经够强，但还没完全统一

如果让我给一个综合判断，我会说：OpenClaw 的事件体系已经具备了明显的工程味道，但它仍然处在**能力强、语义层次多、跨层一致性还在补齐**的阶段。

它已经做对了几件事：
- 把 agent runtime stream 和 hook system 分开
- 把 internal hook 和 plugin hook 分开
- 在 plugin hook 里提供足够多的干预点
- 把工具审批建模成正式能力，而不是约定俗成的旁路
- 明确暴露 session、message、subagent 这些不同生命周期面

但它也还存在很典型的演进期特征：
- 同名概念在不同层暴露不完全对称
- 对编排友好的“完成态事件”还在补齐
- 子会话 / ACP completion 与普通 agent end 之间仍需要明确区分
- 更细粒度的 turn lifecycle 事件仍在社区推进中

这并不意味着 OpenClaw 的设计有问题。恰恰相反，这通常是一个系统从“可用”走向“可编排、可审计、可工业化”的自然阶段。

## 十一、最后回到最初的问题

OpenClaw 有没有“agent 对话完毕触发的钩子”？

**有，但答案不能只说“有”。**

更准确的表述应该是：

- 如果你说的是 **一次 agent run 结束**，那么有：`agent_end`、`lifecycle phase=end`、`agent.wait` 都能构成结束信号 [[1]](https://docs.openclaw.ai/automation/hooks) [[2]](https://docs.openclaw.ai/concepts/agent-loop)。
- 如果你说的是 **一个 session 完成**，Plugin Hook API 层已经有 `session_end`，但 internal hook 层的对齐仍在演进，相关需求已经体现在 `session:end` feature request 中 [[1]](https://docs.openclaw.ai/automation/hooks) [[6]](https://github.com/openclaw/openclaw/issues/10142)。
- 如果你说的是 **spawn 出来的 child / ACP session 完成**，那目前至少从官方 issue 可以看出，这仍然是一个需要更正式事件支持的场景，因此才会出现 `acp:session:complete` 的提案 [[5]](https://github.com/openclaw/openclaw/issues/57671)。

所以真正的结论不是“OpenClaw 有没有结束钩子”，而是：**OpenClaw 已经有多层“结束”信号，但你必须先分清你需要的是 run 结束、message 发出、session 结束，还是 child session 完成。**

如果这个问题不分层，最后就会在 internal hook 里找 plugin event，在 runtime stream 里找 workflow callback，在 `agent_end` 上承载本该由 `acp:session:complete` 解决的编排语义。

这也是我看 OpenClaw 事件体系后最大的感受：它不是“钩子少”，而是**层次很多，因此必须按层理解。**

## 参考来源

| 编号 | 来源 | 用途 |
|------|------|------|
| [1] | [Hooks - OpenClaw](https://docs.openclaw.ai/automation/hooks) | 内部 hooks、plugin hooks、事件分类与 HOOK.md 结构 |
| [2] | [Agent Loop - OpenClaw](https://docs.openclaw.ai/concepts/agent-loop) | agent loop 执行流程、lifecycle/assistant/tool 三类 stream |
| [3] | [Plugin Internals - OpenClaw](https://docs.openclaw.ai/plugins/architecture) | 插件架构、注册模型、provider/runtime hook 背景 |
| [4] | [Webhooks - OpenClaw](https://docs.openclaw.ai/automation/webhook) | 外部 HTTP webhook 入口，与内部 hook 的边界 |
| [5] | [Issue #57671: acp:session:complete](https://github.com/openclaw/openclaw/issues/57671) | spawned ACP session completion 缺口与提案 |
| [6] | [Issue #10142: session:end internal hook event](https://github.com/openclaw/openclaw/issues/10142) | internal hook 层 session 结束事件需求 |
| [7] | [Issue #7724: Agent loop lifecycle hooks](https://github.com/openclaw/openclaw/issues/7724) | 更细粒度 agent lifecycle 事件诉求 |
| [8] | [Issue #5279: Agent Lifecycle Hook Events](https://github.com/openclaw/openclaw/issues/5279) | `agent:response`、`message:sent`、`tool:complete` 等事件提议 |
