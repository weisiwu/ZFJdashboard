# ACP是什么：从协议定义到OpenClaw中的两种用法

> **封面**：covers/ACP是什么：从协议定义到OpenClaw中的两种用法_cover.png

**ACP 本质上是 Agent Client Protocol：一套让编辑器、IDE 与智能体标准化通信的协议。放到 OpenClaw 里，它同时承担两种角色：既可以让 IDE 通过 `openclaw acp` 连进 OpenClaw，也可以让 OpenClaw 通过 `/acp spawn` 调起 Codex、Claude Code、Gemini CLI 这类外部执行器。**

很多人第一次看到 `ACP`，会本能地把它理解成 OpenClaw 里的某个单独功能开关。但如果你顺着 OpenClaw 的文档往下读，会发现这其实不是一个简单功能名，而是一层协议与运行时接入方式。

先给一句最短答案：**ACP 是 Agent Client Protocol，用来标准化“编辑器 / IDE / 客户端”和“智能体”之间的通信方式。** 它的目标很像 LSP 对编辑器生态做的事：减少每个 agent 和每个编辑器之间都要单独做一套适配的集成成本 [[1]](https://agentclientprotocol.com/)。

但在 OpenClaw 里，`ACP` 至少有两种很容易混淆的用法：

1. `openclaw acp`：让 OpenClaw 作为一个 **ACP bridge / ACP agent server**，被 IDE 或 ACP client 连上来 [[2]](https://docs.openclaw.ai/cli/acp) [[3]](https://raw.githubusercontent.com/openclaw/openclaw/main/docs.acp.md)
2. `/acp spawn` 或 `sessions_spawn({ runtime: "acp" })`：让 OpenClaw 去拉起 **外部 ACP harness**，例如 Codex、Claude Code、Gemini CLI 等 [[4]](https://docs.openclaw.ai/tools/acp-agents) [[5]](https://docs.openclaw.ai/concepts/session-tool)

如果不先把这两层分清楚，后面几乎一定会把文档读乱：你会分不清到底是谁在当 server，谁在当 client，谁在驱动谁，谁又只是被 OpenClaw 当执行器调用。

## 一、先看协议本身：ACP 到底是为了解决什么问题

ACP 全称是 **Agent Client Protocol**。它试图解决的是今天 AI coding agent 生态里一个很现实的问题：

- 同一个 editor 接一个新 agent，往往要重新集成一次
- 同一个 agent 想进入多个 editor，又要重复适配多次
- 用户一旦选了某个 agent，很多时候也被它支持的界面和入口绑定住了 [[1]](https://agentclientprotocol.com/)

ACP 的思路，就是把“客户端如何发起会话、发送 prompt、取消任务、列出 session、收流式结果”这类接口抽成一套协议层。官方介绍把它描述为：

- 本地 agent 可以作为 editor 的子进程运行，通过 stdio 通信
- 远程 agent 也可以跑在云端或独立基础设施上，通过 HTTP 或 WebSocket 通信 [[1]](https://agentclientprotocol.com/)

所以从抽象上说，ACP 不是某个具体 agent，也不是 OpenClaw 发明的一套私有聊天命令，而是一种 **“让不同客户端和不同 agent 更容易互通”的标准协议**。

## 二、ACP 在 OpenClaw 里，为什么会看起来像两套东西

这是最关键的地方。

如果你只看命令名，你会看到：

- `openclaw acp`
- `/acp spawn`
- `/acp status`
- `/acp steer`
- `/acp close`

表面上它们都带 `acp`，但职责并不一样。

### 1. `openclaw acp`：OpenClaw 作为 ACP bridge

官方 `acp` CLI 文档讲得很明确：`openclaw acp` 会通过 **stdio 暴露 ACP 接口**，然后把收到的 prompt 转发给一个运行中的 OpenClaw Gateway，会话层面再映射到 Gateway 的 session key [[2]](https://docs.openclaw.ai/cli/acp) [[3]](https://raw.githubusercontent.com/openclaw/openclaw/main/docs.acp.md)。

它的本质是：

- ACP client 启动 `openclaw acp`
- 双方通过 ACP 消息对话
- `openclaw acp` 再去连 OpenClaw Gateway
- ACP 的 `prompt` 被翻译成 Gateway 的 `chat.send`
- ACP 的 `cancel` 被映射到 Gateway 的 `chat.abort`
- 最终结果再由 Gateway stream 翻回 ACP stream [[3]](https://raw.githubusercontent.com/openclaw/openclaw/main/docs.acp.md)

所以这一路里，OpenClaw 扮演的更像：**“把现有 Gateway session 暴露成一个可被 ACP 客户端访问的 agent 入口”。**

你可以把它想成：

- 前面是 IDE / editor / ACP client
- 中间是 `openclaw acp` 这层 bridge
- 后面是真正的 OpenClaw Gateway session

这也是为什么文档会强调：**`openclaw acp` 不是完整 ACP-native editor runtime，而是一个 Gateway-backed ACP bridge。** [[2]](https://docs.openclaw.ai/cli/acp) [[3]](https://raw.githubusercontent.com/openclaw/openclaw/main/docs.acp.md)

### 2. `/acp spawn`：OpenClaw 反过来去调用外部 ACP harness

另一套则正好反过来。

`ACP Agents` 文档说明，OpenClaw 可以通过 `/acp spawn` 或 `sessions_spawn({ runtime: "acp" })` 拉起一个外部 ACP harness。这里的 harness 可以是 Codex、Claude、Gemini、Copilot、Cursor CLI 等 [[4]](https://docs.openclaw.ai/tools/acp-agents) [[5]](https://docs.openclaw.ai/concepts/session-tool)。

这时的角色关系变成：

- OpenClaw 是编排者 / 会话宿主
- 外部 ACP harness 是执行器
- ACP session 被绑定到一个 OpenClaw session 或 thread
- 后续消息可以继续路由回这个外部 harness [[4]](https://docs.openclaw.ai/tools/acp-agents)

也就是说：

- `openclaw acp` 是 **外部客户端连进 OpenClaw**
- `/acp spawn` 是 **OpenClaw 连出去调用外部 agent**

这两者都和 ACP 有关，但方向完全相反。

## 三、为什么很多人会把 ACP 和 MCP、subagent 混在一起

这是第二个高频误区。

### 1. ACP 不等于 MCP

虽然它们都在解决“互操作”问题，但两者面向的层不一样：

- **ACP** 更像“客户端和 agent 之间怎么说话”
- **MCP** 更像“agent 如何访问外部工具或服务”

在 OpenClaw 里，`openclaw acp` 是把 Gateway session 以 ACP 方式暴露给 IDE 或 ACP client；而 `openclaw mcp serve` 则是把 OpenClaw conversation / routing / approval 能力作为 MCP server 暴露给 Claude Code、Codex 等 MCP client。两者不是替代关系，而是针对不同互操作面的接口 [[2]](https://docs.openclaw.ai/cli/acp) [[6]](https://docs.openclaw.ai/cli/mcp)。

### 2. ACP session 不等于普通 subagent

`Session Tools` 文档明确写了：`sessions_spawn` 可以创建两类 child runtime：

- `runtime: "subagent"`，这是默认值
- `runtime: "acp"`，这是外部 harness agent [[5]](https://docs.openclaw.ai/concepts/session-tool)

这就说明 ACP session 和普通 subagent 虽然都可能表现成“从父会话里再拉起一个执行单元”，但底层不是一回事：

- 普通 subagent 还是 OpenClaw 自己的 agent runtime
- ACP session 是把任务交给外部 coding harness 执行 [[4]](https://docs.openclaw.ai/tools/acp-agents)

所以如果你的目标是：

- 在 OpenClaw 内部拆多 agent 协作，用 subagent 更自然
- 把 repo 操作、编码、外部持续会话交给 Codex / Claude Code / Gemini CLI，更像 ACP 的适用场景

## 四、`openclaw acp` 到底怎么工作

如果你把 `openclaw acp` 理解成“IDE 到 OpenClaw 的协议桥”，很多设计就好理解了。

### 1. 它不是直接选 agent，而是先选 Gateway session

OpenClaw ACP Bridge 文档里有一个特别重要的点：**ACP 不直接选 agent，而是通过 Gateway session key 路由。** [[3]](https://raw.githubusercontent.com/openclaw/openclaw/main/docs.acp.md)

例如：

- `openclaw acp --session agent:main:main`
- `openclaw acp --session agent:design:main`
- `openclaw acp --session agent:qa:bug-123` [[3]](https://raw.githubusercontent.com/openclaw/openclaw/main/docs.acp.md)

这意味着 ACP bridge 不是“把 IDE 连到一个抽象 agent 名称”，而是把 IDE 的 ACP session 绑定到 OpenClaw 现有的 session key 上。

### 2. 默认会话键为什么是 `acp:<uuid>`

文档还提到，默认每个 ACP session 会映射到一个独立的 Gateway session key，例如 `acp:<uuid>` [[2]](https://docs.openclaw.ai/cli/acp) [[3]](https://raw.githubusercontent.com/openclaw/openclaw/main/docs.acp.md)。

它的目的很现实：

- 避免多个 ACP client 共用一个 session 时互相串流
- 让 editor-local turn 有更干净的隔离
- 允许重连时继续映射回原来的 Gateway transcript

如果你显式指定 `--session` 或 `--session-label`，那就是你主动选择把 ACP 客户端挂到某个已有 OpenClaw session 上。

### 3. 它更像 bridge，而不是完整原生 runtime

官方同时也很坦率地写了限制：

- `loadSession` 回放的是历史 user / assistant text，不会完整重建历史 tool calls 和更丰富的 ACP-native 事件
- `session_info_update` 和 `usage_update` 是从 Gateway snapshot 推导的，数据是近似值
- 目前不会发出完整 ACP terminal 或结构化 diff 事件
- 模型选择、exec-host 控制等能力还没有完整暴露成 ACP 配置选项 [[2]](https://docs.openclaw.ai/cli/acp) [[3]](https://raw.githubusercontent.com/openclaw/openclaw/main/docs.acp.md)

所以如果有人问：“OpenClaw ACP 是不是已经把 OpenClaw 彻底变成一个完整 ACP-native agent runtime 了？”

更准确的回答是：**还不是。它现在更像一层协议桥，把已有 Gateway 能力投射成 ACP 能消费的那一部分。**

## 五、`/acp spawn` 这条线，真正解决了什么问题

相比 `openclaw acp`，`ACP Agents` 更像另一种能力：**让 OpenClaw 直接驱动外部 coding harness。**

文档里给出的典型目标包括：

- `claude`
- `codex`
- `copilot`
- `cursor`
- `gemini`
- `openclaw`
- `opencode`
- `pi`
- `qwen` 等 [[4]](https://docs.openclaw.ai/tools/acp-agents)

而操作层面，文档提供的是一整套 `/acp` 控制面：

- `/acp spawn`
- `/acp cancel`
- `/acp steer`
- `/acp close`
- `/acp status`
- `/acp set-mode`
- `/acp cwd`
- `/acp permissions`
- `/acp timeout`
- `/acp model`
- `/acp sessions`
- `/acp doctor`
- `/acp install` [[4]](https://docs.openclaw.ai/tools/acp-agents)

你会发现这已经不是“发一个请求给外部 agent”这么简单，而是：

- 可以启一个持续 session
- 可以把当前 channel 或 thread 绑定给它
- 可以调整 model、cwd、permissions、timeout
- 可以在运行中 `steer`
- 可以在需要时 `close` 或 `cancel`

这说明 ACP 在这里承担的是：**外部编码执行器的会话宿主层**。

## 六、一个最有用的理解方式：ACP 是 OpenClaw 的“外部 agent 接口层”

如果只用一句工程化的话来概括，我会这么说：

**在 OpenClaw 里，ACP 不是单一功能，而是一层把“外部 agent 客户端”和“外部 agent 执行器”都纳入进来的接口层。**

它至少覆盖两个方向：

### 1. 北向接口：让 IDE / ACP client 接进 OpenClaw

这一层对应 `openclaw acp`。

适合场景：

- 你在用支持 ACP 的 editor
- 你想把它接到现有 OpenClaw Gateway
- 你希望 IDE 驱动的是 OpenClaw session，而不是另起一套孤立代理 [[2]](https://docs.openclaw.ai/cli/acp)

 ### 2. 南向接口：让 OpenClaw 调外部 harness
 
 这一层对应 `/acp spawn` 与 `runtime: "acp"`。
 
 适合场景：
 
 - 你希望 OpenClaw 把一段 coding 任务下发给 Codex / Claude Code / Gemini CLI
 - 你希望这些外部 agent 运行在自己的 harness 环境里
 - 你又希望它们仍然被 OpenClaw 的 session、thread、routing 和控制面统一管理 [[4]](https://docs.openclaw.ai/tools/acp-agents) [[5]](https://docs.openclaw.ai/concepts/session-tool)
 
 这也是为什么我更愿意把 ACP 看成一种 **边界层能力**：它处理的是 OpenClaw 与外部 agent 生态之间的接缝。

### 3. 一个最实用的选型表：你现在到底该用哪种 ACP

| 你的目标 | 更适合的入口 | 原因 |
|------|------|------|
| 想让 IDE 直接和 OpenClaw 会话对话 | `openclaw acp` | 这是北向 bridge，适合 editor 接入 |
| 想让 OpenClaw 把代码任务交给 Codex / Claude Code | `/acp spawn` | 这是南向外部 harness 接入 |
| 想让 OpenClaw 暴露 tools / conversations 给外部 agent | `openclaw mcp serve` | 这是 MCP 互操作，不是 ACP client bridge |
| 想在 OpenClaw 内部拆一个普通子 agent | `subagent` / `runtime: "subagent"` | 不需要外部 harness，就别走 ACP |

这个表背后的核心判断很简单：**ACP 解决的是 agent 客户端和外部执行器的接缝，不是所有跨 agent 场景都该走 ACP。**

## 七、两个最容易看懂 ACP 的例子

### 1. 例子一：让 Zed 或 acpx 把 OpenClaw 当作一个 ACP agent 来连

这个例子对应 `openclaw acp`。

假设你的目标不是让 OpenClaw 去调用外部 agent，而是想让一个支持 ACP 的客户端直接驱动 OpenClaw Gateway，会更像下面这条链路：

1. 本地先跑好 OpenClaw Gateway
2. 客户端启动 `openclaw acp`
3. `openclaw acp` 连接 Gateway
4. ACP 的 prompt 被转成 OpenClaw session 的消息 [[2]](https://docs.openclaw.ai/cli/acp) [[3]](https://raw.githubusercontent.com/openclaw/openclaw/main/docs.acp.md)

典型命令会像：

```bash
openclaw acp --session agent:main:main
```

或者在 `~/.acpx/config.json` 里把 `openclaw acp` 配成一个 agent command，让 `acpx openclaw` 直接打到指定的 Gateway session [[2]](https://docs.openclaw.ai/cli/acp)。

这个场景里，OpenClaw 不是 orchestrator 去调别人，而是**被 IDE 当成一个 ACP-compatible agent 入口消费**。

### 2. 例子二：让 OpenClaw 把当前会话绑定给 Codex 持续处理

这个例子对应 `/acp spawn`。

如果你的目标是“把当前频道或线程交给 Codex 持续处理代码任务”，那更自然的路径是：

```text
/acp spawn codex --bind here
/acp status
/acp steer prioritize failing tests and keep logs concise
```

如果你想让它变成 thread-bound 的持续会话，也可以走：

```text
/acp spawn codex --mode persistent --thread auto
```

这条链路里，OpenClaw 是会话宿主；Codex 是外部 harness；后续消息会继续打到这个 ACP session 上 [[4]](https://docs.openclaw.ai/tools/acp-agents)。

也正因为它是持续会话，所以后续你往往还会配合：

- `/acp cwd`
- `/acp model`
- `/acp permissions`
- `/acp close`

这已经不是“一次性调用外部工具”，而是在 OpenClaw 里挂了一个可持续 steering 的外部执行器。

## 八、ACP 真正难的地方，不是“能不能跑”，而是“怎么编排完成态”

如果你只看 happy path，会觉得 ACP 已经很完整了：spawn、status、steer、close，看起来都齐全。

但从编排角度看，一个更难的问题是：**外部 ACP session 完成后，父编排器如何可靠接到“完成事件”？**

现有资料里已经能看到这个缺口。社区 issue 提到：当 orchestrator 通过 `sessions_spawn` 拉起 spawned ACP session 时，系统还缺少一个足够可靠的一等完成事件，导致父任务往往需要通过这些替代办法兜底：

- 轮询 `sessions_list`
- 监听 stream 再自己补消息
- 往父会话手工注 system message [[7]](https://github.com/openclaw/openclaw/issues/57671)

这说明 ACP 在 OpenClaw 里的成熟度，不该只看“能不能拉起外部 agent”，还要看：

- 会话完成态是否好编排
- 流式事件是否够细
- 状态与 usage 是否足够原生
- session 恢复和多 client 共用时是否足够稳定

这部分恰恰是协议桥和会话编排交叉后最复杂的地方。

## 九、如果你只是想回答“ACP 是什么”，最短可用答案应该怎么说

如果是给同事或朋友解释，我会建议用下面这个版本：

> ACP 是 Agent Client Protocol，一套让编辑器 / IDE 和智能体标准化通信的协议。放到 OpenClaw 里，它主要有两种用法：一是 `openclaw acp`，让 OpenClaw 作为 ACP bridge 被 IDE 连入；二是 `/acp spawn`，让 OpenClaw 通过 ACP backend 拉起外部 coding harness，比如 Codex、Claude Code、Gemini CLI。前者是“外部连进 OpenClaw”，后者是“OpenClaw 连出去调用外部 agent”。

这个回答虽然短，但已经把最容易混淆的地方拆开了。

## 十、我的最终判断

如果只问“ACP 是什么”，答案当然是 Agent Client Protocol。

但如果你问“ACP 在 OpenClaw 里意味着什么”，我会给一个更工程化的结论：

**ACP 是 OpenClaw 接入外部 agent 生态的重要边界层。**

它一头把支持 ACP 的 IDE / editor 接进 OpenClaw Gateway，另一头又把外部 coding harness 接进 OpenClaw 的 session 编排面。它不是单一工具，也不是单一命令，而是一个同时覆盖 **协议桥接、会话映射、外部执行器接入、运行时控制** 的能力集合。

也正因为如此，理解 ACP 最重要的不是记住 `openclaw acp` 或 `/acp spawn` 这些命令，而是先分清楚：**到底是谁在驱动谁，谁是会话宿主，谁是协议桥，谁又是真正干活的外部 agent。**

## 参考来源

| 编号 | 来源 | 用途 |
|------|------|------|
| [1] | [Introduction - Agent Client Protocol](https://agentclientprotocol.com/) | ACP 的协议目标与标准背景 |
| [2] | [acp - OpenClaw](https://docs.openclaw.ai/cli/acp) | `openclaw acp` 的 CLI 语义、限制与用法 |
| [3] | [OpenClaw ACP Bridge](https://raw.githubusercontent.com/openclaw/openclaw/main/docs.acp.md) | ACP bridge 的执行模型、session 映射与限制 |
| [4] | [ACP Agents - OpenClaw](https://docs.openclaw.ai/tools/acp-agents) | `/acp spawn`、外部 harness、控制命令与配置 |
| [5] | [Session Tools - OpenClaw](https://docs.openclaw.ai/concepts/session-tool) | `sessions_spawn` 中 `runtime: "acp"` 的定位 |
| [6] | [mcp - OpenClaw](https://docs.openclaw.ai/cli/mcp) | 与 ACP 对比，澄清 MCP 的不同职责 |
| [7] | [Feature: fired event/hook when spawned ACP session completes](https://github.com/openclaw/openclaw/issues/57671) | ACP 编排完成态的现实缺口 |
