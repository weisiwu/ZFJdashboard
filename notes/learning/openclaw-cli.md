# 如何用OpenClaw CLI强化Agent：从能力接入到自我进化

> **封面**：covers/如何用OpenClaw CLI强化Agent：从能力接入到自我进化_cover.png

**真正让 OpenClaw agent 变强的，不是多记几个命令，而是把 OpenClaw CLI 当成 agent 的控制平面：用它重做 agent 结构、分发 skills、接入 plugins、配置模型与权限、启用 hooks，并通过 MCP 接入更大的 agent 网络。**

先说结论：如果把 OpenClaw CLI 只理解成“启动 gateway、查个状态、配个模型”的运维入口，那你其实只用了它很小的一部分。更准确的理解是：**OpenClaw CLI 是 OpenClaw agent 的装配台、分发面、控制面和桥接面。** 你不仅可以用它给 agent 加技能、加工具、加模型、加自动化，还可以用它把 OpenClaw 自己暴露给 Claude Code / Codex 之类的外部 agent。

这也是为什么你问“如何利用 opencli 去强化 openclaw 的 agent”，我会先把 `opencli` 按 **OpenClaw CLI** 来理解。因为目前官方文档里并没有一个独立叫 `opencli` 的能力面，真正存在的是：

- `openclaw agents`
- `openclaw models`
- `openclaw skills`
- `openclaw plugins`
- `openclaw hooks`
- `openclaw approvals`
- `openclaw mcp`
- 配套的 `clawhub` CLI [[1]](https://docs.openclaw.ai/cli) [[2]](https://docs.openclaw.ai/tools/clawhub)

所以这篇文章重点回答两个问题：

1. 如何用 OpenClaw CLI 去强化现有 agent
2. 如果你想让自己的“opencli 能力”持续变强，应该往哪几个方向演进

## 一、先给一个总判断：OpenClaw CLI 强化 agent，本质上有六条路

如果把官方 CLI、Skills、Plugins、MCP、Hooks 文档连起来看，OpenClaw CLI 对 agent 的增强大致可以拆成六条路径：

1. **重做 agent 拓扑**：新增 agent、绑定路由、设置 identity
2. **补知识与流程**：给 agent 安装 / 筛选 skills
3. **补执行能力**：安装 plugin 或注册自定义 tool
4. **补模型与路由**：设置默认模型、alias、fallback、auth profile
5. **补自动化与记忆**：启用 hooks，把固定动作自动化
6. **补外部互操作**：接入 MCP，或者把 OpenClaw 反向暴露给别的 agent [[1]](https://docs.openclaw.ai/cli) [[3]](https://docs.openclaw.ai/cli/agents) [[4]](https://docs.openclaw.ai/cli/mcp)

如果你不按这六类去理解，很容易出现一个常见误区：明明是“缺技能”，却跑去写插件；明明是“缺工具”，却只是加了个 prompt；明明是“缺控制面”，却去堆更多 agent。

## 二、第一层强化：先把 agent 本身组织对

很多人一上来就想“怎么让 agent 更聪明”，但 OpenClaw 里第一个更该优化的，往往不是 prompt，而是 **agent 的组织结构**。

官方 `openclaw agents` 文档说明，你可以直接用 CLI 做这些事情：

- `openclaw agents list`
- `openclaw agents add [name] --workspace <dir> --model <id>`
- `openclaw agents bind --agent <id> --bind <channel[:accountId]>`
- `openclaw agents unbind --agent <id> --bind <channel[:accountId]>`
- `openclaw agents set-identity --agent <id> --from-identity` [[3]](https://docs.openclaw.ai/cli/agents)

这意味着 CLI 不是只会“操作一个默认 agent”，而是可以直接管理一个 **多 agent 编排面**。

### 1. 新增专职 agent，而不是把所有能力塞给一个主 agent

如果你现在的 OpenClaw 只有一个总管型 agent，那它通常会有两个问题：

- 上下文太杂
- 能力边界不清

更合理的做法是把高频能力拆开，例如：

- `research`：只负责检索、归纳、对比
- `writer`：只负责结构化输出
- `ops`：只负责运维和执行
- `dev`：只负责代码操作和验证

OpenClaw CLI 允许你为每个 agent 指定独立 workspace、模型和 channel 绑定 [[3]](https://docs.openclaw.ai/cli/agents)。这本质上是在做一件很重要的事：**把能力分层变成运行时实体，而不是停留在 prompt 描述里。**

### 2. 用 identity 而不是长 prompt 去稳定 agent 个性

`openclaw agents set-identity` 支持通过 `IDENTITY.md` 或显式字段给 agent 设置 identity [[3]](https://docs.openclaw.ai/cli/agents)。

这件事的价值在于：

- identity 比临时系统提示更稳定
- 可以和独立 workspace 一起形成“角色环境”
- 更适合长期运行的专职 agent

如果你想让某个 agent 长期扮演“产品研究员”“代码审计员”“自动化运营助手”，优先级应该是：

1. 先给它单独 workspace
2. 再给它 identity
3. 再给它技能和工具

而不是反过来先堆工具。

## 三、第二层强化：给 agent 加 skills，而不是只加 prompt

OpenClaw 最被低估的一层，是 skills。

官方文档明确说明，skills 支持：

- 多级加载位置
- per-agent 与 shared skills
- `agents.defaults.skills`
- `agents.list[].skills`
- ClawHub 安装与更新 [[5]](https://docs.openclaw.ai/tools/skills)

这说明 skill 不是一个“聊天模板”，而是一种真正影响 agent 行为选择的运行时能力描述。

### 1. 为什么 skill 比临时 prompt 更适合强化 agent

prompt 当然能教 agent 做事，但 prompt 有三个天然问题：

- 难复用
- 难版本化
- 难做 per-agent 管理

而 skill 的优势在于：

- 可以装到 `~/.openclaw/skills`、`~/.agents/skills`、`<workspace>/skills` 等不同层级
- 可以通过 `agents.defaults.skills` 和 `agents.list[].skills` 控制哪些 agent 能看到哪些 skill
- 可以通过 `openclaw skills install <skill-slug>`、`openclaw skills update --all` 持续更新 [[5]](https://docs.openclaw.ai/tools/skills)

换句话说，**skill 是“可安装的行为增强包”**，这比把经验写死在某个 prompt 文件里高级很多。

### 2. 最适合用 skill 强化的能力是什么

我会把最适合 skill 化的能力分成三类：

- **稳定流程**：如写周报、竞品分析、PRD 拆解、复盘模板
- **知识域**：如某个产品线、某套 API、某个业务术语体系
- **命令封装**：把一套步骤做成 slash command 或工具分发入口

如果你的目标是“让 agent 更会做某类任务”，skill 往往是成本最低、收益最高的一层。

### 3. 利用 ClawHub 给 agent 快速补能力

OpenClaw 官方把 ClawHub 作为 skill 和 plugin 的分发入口。你可以：

- `openclaw skills search "calendar"`
- `openclaw skills install <skill-slug>`
- `openclaw skills update --all` [[2]](https://docs.openclaw.ai/tools/clawhub)

这意味着强化 agent 不一定要自己从零写能力。有些增强可以直接通过现成 skill 安装获得。

对个人用户来说，一个很有效的套路是：

1. 先用 `openclaw skills search` 找现成能力
2. 装进某个 workspace 或 shared skill 目录
3. 用 `agents.list[].skills` 精确收敛到目标 agent
4. 再根据自己的任务流做二次改写

## 四、第三层强化：给 agent 补模型能力，而不是只换一个默认模型

很多人说“提升 agent 能力”，第一反应是换更强模型。但 OpenClaw CLI 的模型面比“选模型”复杂得多。

`openclaw models` 支持：

- `openclaw models status`
- `openclaw models list`
- `openclaw models set <model-or-alias>`
- `openclaw models scan`
- `openclaw models aliases list`
- `openclaw models fallbacks list`
- `openclaw models auth login --provider <id>`
- `openclaw models auth paste-token --provider <id>` [[6]](https://docs.openclaw.ai/cli/models)

### 1. 提升 agent，不只是升级主模型，而是设计模型路由

官方文档强调了 alias、fallback、provider/model 解析和 auth profile [[6]](https://docs.openclaw.ai/cli/models)。这意味着更成熟的做法不是“永远用最贵模型”，而是：

- 主模型负责复杂推理
- 备用模型负责兜底
- 不同 agent 用不同模型档位
- 特定场景用特定 provider

比如：

- `research` 用长上下文、强检索协同模型
- `writer` 用表达稳定、成本适中的模型
- `ops` 用响应快、低延迟模型
- `dev` 用代码理解更稳的模型

真正让 agent 变强的，是 **能力与成本的匹配**，不是单点堆料。

### 2. OpenClaw CLI 的价值在于把 auth 和模型管理做成正式控制面

文档还提到 OpenClaw 支持多种 provider 登录与 token 管理方式，包括 Claude CLI reuse、`claude -p`、token setup / paste 等 [[6]](https://docs.openclaw.ai/cli/models)。

这让 CLI 具备一个很现实的价值：**你可以把“模型接入”从手工环境变量时代，升级成可检查、可轮换、可切换的正式配置面。**

如果你的 agent 老是“能力忽高忽低”，很多时候问题根本不在 prompt，而在：

- provider auth 不稳定
- fallback 没配
- alias 不统一
- 某个 agent 用了不合适的默认模型

## 五、第四层强化：给 agent 加工具，真正扩执行面

如果 skill 解决的是“会不会做”，那 plugin / tool 解决的是“能不能做”。

官方 plugin 文档说明，你可以通过 `definePluginEntry` 和 `api.registerTool(...)` 注册自定义工具，甚至把某些工具标记成 `optional: true`，由用户决定是否加入 allowlist [[7]](https://docs.openclaw.ai/plugins/building-plugins)。

### 1. 什么情况下应该写 tool plugin

当你遇到这些需求时，基本就应该进入 tool plugin 层了：

- 访问企业内部 API
- 调用自定义工作流 / pipeline
- 跑某种带副作用的业务动作
- 查询私有数据库或服务
- 将第三方系统能力正式接入 agent

因为这些需求不是“教 agent 一套话术”能解决的，而是必须真的给它新增一个能力面。

### 2. 最小可行路径是什么

官方给出的最小工具插件路径大致是：

1. 准备插件包与 manifest
2. 写 `index.ts`
3. `definePluginEntry({... register(api) { api.registerTool(...) }})`
4. 本地测试
5. `openclaw plugins install` 安装，或通过 ClawHub 分发 [[7]](https://docs.openclaw.ai/plugins/building-plugins) [[2]](https://docs.openclaw.ai/tools/clawhub)

文档还特别说明：

- 工具名不能与 core tools 冲突
- 有副作用的工具更适合 `optional: true`
- 用户可以通过 `tools.allow` 或插件 id 控制工具开放 [[7]](https://docs.openclaw.ai/plugins/building-plugins)

这背后有个很值得学的设计：**OpenClaw 把“注册能力”和“开放权限”分开了。**

### 3. 一个很实用的判断标准

如果你的需求是下面这样：

- “让 agent 学会更稳定地写竞品分析” → 用 skill
- “让 agent 能调用公司 CRM 查客户数据” → 用 tool plugin
- “让 agent 在执行前加一道审批” → 用 hooks / approvals

不要把所有东西都做成 skill，也不要把所有东西都做成插件。

### 4. 一个更好用的判断表：你缺的到底是哪一层

很多团队在强化 agent 时浪费时间，不是因为不会写，而是因为一开始就选错了扩展层。

| 你遇到的问题 | 更适合补哪层 | 原因 |
|------|------|------|
| agent 回答风格不稳定 | `identity` + skills | 这是角色定义问题，不是工具问题 |
| agent 不会某类固定工作流 | skills | 重点是流程与知识封装 |
| agent 不能访问某个内部系统 | tool plugin | 需要新增执行能力 |
| agent 执行动作太危险 | approvals | 重点是权限边界与放行规则 |
| agent 需要自动记忆、自动注入上下文 | hooks | 重点是生命周期自动化 |
| agent 需要和外部 agent 协作 | MCP | 重点是桥接和互操作 |

这个表的价值在于，它能帮你避免一个高频误区：**把“能力建设”误做成“prompt 堆砌”。**

## 六、第五层强化：用 hooks 和 approvals 把 agent 从“会做”变成“可控”

OpenClaw CLI 另一个很强的点，是把 hooks 和 approvals 做成了日常可操作的命令面。

### 1. 用 hooks 把稳定动作自动化

`openclaw hooks` 支持：

- `openclaw hooks list`
- `openclaw hooks info <name>`
- `openclaw hooks check`
- `openclaw hooks enable <name>`
- `openclaw hooks disable <name>` [[8]](https://docs.openclaw.ai/cli/hooks)

官方还给了几个内建 hook：

- `session-memory`
- `bootstrap-extra-files`
- `command-logger`
- `boot-md` [[8]](https://docs.openclaw.ai/cli/hooks)

这几个 hook 对强化 agent 特别实用：

- `session-memory`：把 `/new`、`/reset` 的上下文沉淀成记忆
- `bootstrap-extra-files`：在 agent bootstrap 时注入额外文件，如 `AGENTS.md`、`TOOLS.md`
- `command-logger`：记录命令行为，方便审计和复盘
- `boot-md`：在 gateway 启动时执行固定 bootstrap 动作 [[8]](https://docs.openclaw.ai/cli/hooks)

如果你想让 agent 更稳定、更像一个“系统”，而不是一次性聊天机器人，hooks 非常关键。

### 2. 用 approvals 管住高风险执行面

`openclaw approvals` 支持：

- `openclaw approvals get`
- `openclaw approvals set --file ...`
- `openclaw approvals allowlist add ...`
- `openclaw approvals allowlist remove ...` [[9]](https://docs.openclaw.ai/cli/approvals)

文档里强调，effective result 最终仍然由 host approvals file 决定；CLI 只是帮助你查看和更新这个控制面 [[9]](https://docs.openclaw.ai/cli/approvals)。

这点非常重要，因为一个 agent 真正强，不只是“什么都能做”，而是：

- 能做的边界清楚
- 高风险动作需要审批
- 低风险动作能顺畅执行
- 常用命令能通过 allowlist 放行

所以 approvals 的意义不是“限制 agent”，而是**让 agent 从危险的万能助手，变成可上线的生产助手。**

## 七、第六层强化：用 MCP 让 OpenClaw agent 接进更大的 agent 网络

如果你想进一步强化 OpenClaw agent，最值得关注的一层其实是 MCP。

官方文档说明：`openclaw mcp serve` 可以把 OpenClaw 暴露成一个 MCP server，让 Claude Code、Codex 或其他 MCP client 直接连接 OpenClaw 的 routed conversations [[4]](https://docs.openclaw.ai/cli/mcp)。

它暴露的 bridge tools 包括：

- `conversations_list`
- `conversation_get`
- `messages_read`
- `attachments_fetch`
- `events_poll`
- `events_wait`
- `messages_send`
- `permissions_list_open`
- `permissions_respond` [[4]](https://docs.openclaw.ai/cli/mcp)

### 1. 这为什么能强化 OpenClaw agent

因为这不是“加一个外部工具”这么简单，而是：

- 让外部 agent 能把 OpenClaw 当作对话和路由后端
- 让 OpenClaw 已有的 channel / session / approval 能力对外开放
- 让 Claude Code / Codex 可以复用 OpenClaw 的会话面，而不是重搭一套桥

这会带来一个非常有意思的结果：**OpenClaw 不只是一个 agent app，而是可以变成其他 agent 的中枢。**

### 2. 什么时候最适合用这层

以下场景特别适合：

- 你已经在用 Claude Code / Codex，但想复用 OpenClaw 的多 channel 会话
- 你想让一个外部 coding agent 处理 OpenClaw 路由过来的任务
- 你想把 OpenClaw 接进更大的 agent workflow，而不是只在自家 UI 内使用

这层能力，往往是“让 OpenClaw 从一个好用工具变成一个平台”的关键分水岭。

## 八、那“如何提升自己的 opencli 能力”？本质上是把自己从使用者升级成能力装配者

如果前面讲的是“怎么用 CLI 强化 agent”，那后半句“怎么提升自己的 opencli 能力”，我理解的是：**怎么让你自己越来越会用这套 CLI，把它变成一套可扩展的个人能力系统。**

我会建议往五个方向升级。

### 1. 从会用命令，升级到会设计 agent 结构

初级阶段的人，会这些：

- 看状态
- 切模型
- 发消息

更成熟的阶段，是会做这些：

- 什么时候该拆新 agent
- 什么时候该独立 workspace
- 什么时候该单独 identity
- 什么时候该重新做 route binding

也就是说，你不只是“操作 agent”，而是在 **设计 agent 编排结构**。

### 2. 从会装 skill，升级到会维护自己的 skill pack

真正拉开差距的，不是你装了多少 skill，而是你有没有形成自己的 skill 系统。

一个很实用的成长路径是：

1. 先从 ClawHub 安装 5-10 个高频 skill
2. 把真正常用的整理进自己的 shared skill 目录
3. 把只属于某类 agent 的放进 `~/.agents/skills` 或项目级 `<workspace>/.agents/skills`
4. 定期清理低价值 skill，避免 prompt 污染和 token 膨胀

官方还给出了 skills 对 prompt 的字符与 token 开销估算，这提醒我们：**skill 不是越多越强，而是越聚焦越强。** [[5]](https://docs.openclaw.ai/tools/skills)

### 3. 从会装 plugin，升级到会写自己的 tool plugin

如果你只会安装别人写好的插件，你的 OpenClaw 能力上限最终会受别人影响。

真正能显著提升“你自己的 opencli 能力”的一步，是开始写自己的插件，至少是：

- 会写最小工具插件
- 会注册一个内部 API tool
- 会把高频工作流做成 optional tool
- 会通过 ClawHub 发布 / 更新自己的插件 [[7]](https://docs.openclaw.ai/plugins/building-plugins) [[2]](https://docs.openclaw.ai/tools/clawhub)

一旦走到这一步，你就不再是“使用 OpenClaw 的人”，而是开始 **定义 OpenClaw 能做什么的人**。

### 4. 从会启用 hook，升级到会设计自动化控制面

很多人的自动化停留在 cron 或脚本，但 OpenClaw 的 hook 系统给了更细的生命周期插入点。

更成熟的能力是：

- 哪些动作适合在 bootstrap 阶段做
- 哪些动作适合在 session reset 时记忆化
- 哪些命令应该被审计记录
- 哪些高风险工具调用应该被拦截审批

这类设计能力，决定了你的 OpenClaw 是不是一个能长期跑的系统。

### 5. 从会本地使用，升级到会做生态桥接

如果你能熟练使用：

- `openclaw mcp serve`
- `openclaw mcp list / set / show`
- `openclaw plugins install`
- `clawhub package publish`

那你其实已经具备了一种更高级的能力：**把 OpenClaw 接入更大生态，而不是只把它当单点工具。**

这也是我理解的“提升自己的 opencli 能力”的最高价值方向。

## 九、两个最实用的落地路线

为了避免只讲概念，我给两个很实际的落地路线。

### 路线一：把现有 OpenClaw 升级成“研究型 agent 系统”

目标：让 OpenClaw 更适合做研究、信息整理、学习笔记。

建议顺序：

1. `openclaw agents add research --workspace ...`
2. 给 `research` 设置 identity
3. 安装检索、文档分析、写作相关 skills
4. 给 `writer` 单独配置表达更稳定的模型
5. 启用 `session-memory` 和 `command-logger`
6. 用 approvals 收紧高风险 exec
7. 如有需要，再接 MCP 让 Claude Code 参与复杂处理

这套路线的重点不是“堆更多工具”，而是把研究流程拆成稳定角色。

### 路线二：把 OpenClaw 升级成“企业内部自动化助手”

目标：让 agent 不只是会聊天，而是能调用内部系统。

建议顺序：

1. 保留一个 `ops` 或 `assistant` agent
2. 写一个最小 tool plugin，接企业 API
3. 将高风险工具设为 `optional: true`
4. 用 approvals 和 allowlist 收敛权限
5. 用 hooks 记录关键执行日志
6. 必要时通过 ClawHub 或私有分发同步插件版本

这套路线的核心不是“模型更强”，而是 **工具面真正长出来了**。

## 十、把两条路线翻成真正可执行的命令

如果你今天就想开始做，而不是只停留在文章层面，下面这两组命令最值得直接照着改。

### 1. 研究型 agent 路线的最小命令集

第一步，建一个独立 agent：

```bash
openclaw agents add research --workspace ~/.openclaw/workspace-research --model openai/gpt-5.4
```

第二步，补 identity：

```bash
openclaw agents set-identity --agent research --from-identity
```

第三步，装技能：

```bash
openclaw skills search "research"
openclaw skills install <skill-slug>
openclaw skills update --all
```

第四步，检查模型与 fallback：

```bash
openclaw models status --agent research
openclaw models aliases list
openclaw models fallbacks list
```

第五步，启用更适合研究型工作流的 hooks：

```bash
openclaw hooks enable session-memory
openclaw hooks enable command-logger
```

这一套命令的真正价值，不是把 `research` 变成“另一个聊天窗口”，而是把它变成一个有独立 workspace、独立角色、独立知识增强、独立记忆策略的专职 agent [[3]](https://docs.openclaw.ai/cli/agents) [[5]](https://docs.openclaw.ai/tools/skills) [[8]](https://docs.openclaw.ai/cli/hooks)。

### 2. 企业自动化路线的最小命令集

如果你的目标是让 OpenClaw 真正去调用内部系统，更可行的起点通常是：

第一步，先把执行权限面看清楚：

```bash
openclaw approvals get
openclaw approvals get --gateway
```

第二步，给常见安全命令做 allowlist：

```bash
openclaw approvals allowlist add "/usr/bin/uname"
openclaw approvals allowlist add "/usr/bin/uptime"
```

第三步，安装或分发自己的插件：

```bash
openclaw plugins install clawhub:@myorg/openclaw-my-plugin
```

第四步，必要时再把 OpenClaw 暴露给外部 agent：

```bash
openclaw mcp serve --claude-channel-mode auto
```

这条路线的核心不是“先把所有东西接进来”，而是先把控制面立住：**先权限，再工具，再桥接。** 否则 agent 虽然看起来“能力更强”，但很容易变成不可控的执行器 [[4]](https://docs.openclaw.ai/cli/mcp) [[7]](https://docs.openclaw.ai/plugins/building-plugins) [[9]](https://docs.openclaw.ai/cli/approvals)。

## 十一、我的最终判断

如果你问我：“如何利用 opencli 去强化 OpenClaw 的 agent？如何提升自己的 opencli 能力？”

我会给出一个非常明确的结论：

**不要把 OpenClaw CLI 当成一个命令行入口，而要把它当成 agent 的控制平面。**

它至少同时负责：

- agent 拓扑管理
- skill 分发与筛选
- plugin / tool 接入
- 模型与认证配置
- hooks 与审批控制
- MCP 桥接与生态互操作 [[1]](https://docs.openclaw.ai/cli) [[4]](https://docs.openclaw.ai/cli/mcp) [[7]](https://docs.openclaw.ai/plugins/building-plugins)

所以真正的提升路径不是“多记几个命令”，而是分三步：

1. **先会装配**：会加 agent、加 skill、加模型、加 hook
2. **再会控制**：会做 approvals、allowlist、日志和自动化
3. **最后会扩展**：会写 plugin、会发 skill、会做 MCP bridge

走到第三步时，你的“opencli 能力”才真正从使用能力，变成平台能力。

## 参考来源

| 编号 | 来源 | 用途 |
|------|------|------|
| [1] | [CLI Reference - OpenClaw](https://docs.openclaw.ai/cli) | CLI 总入口与命令树 |
| [2] | [ClawHub - OpenClaw](https://docs.openclaw.ai/tools/clawhub) | skills / plugins 的分发与安装能力 |
| [3] | [agents - OpenClaw](https://docs.openclaw.ai/cli/agents) | agent 管理、workspace、bindings、identity |
| [4] | [mcp - OpenClaw](https://docs.openclaw.ai/cli/mcp) | OpenClaw 作为 MCP server 与 registry 的桥接能力 |
| [5] | [Skills - OpenClaw](https://docs.openclaw.ai/tools/skills) | skill 加载层级、allowlist、环境注入、token 开销 |
| [6] | [models - OpenClaw](https://docs.openclaw.ai/cli/models) | 模型、auth profile、alias 与 fallback |
| [7] | [Building Plugins - OpenClaw](https://docs.openclaw.ai/plugins/building-plugins) | 自定义 tool plugin 的最小路径 |
| [8] | [hooks - OpenClaw](https://docs.openclaw.ai/cli/hooks) | hooks 的查看、启用、内建 hook 能力 |
| [9] | [approvals - OpenClaw](https://docs.openclaw.ai/cli/approvals) | exec approvals、allowlist 与安全策略 |
