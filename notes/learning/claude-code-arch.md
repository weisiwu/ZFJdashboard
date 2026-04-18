# Claude Code源码架构观察：最近最值得学习的3个设计

> **封面**：covers/Claude Code源码架构观察：最近最值得学习的3个设计_cover.png

**如果只看 Claude Code 最近的源码热度，最容易被带偏到“它暴露了多少内部实现”；但真正值得学的，不是八卦，而是它已经把 agent 产品收敛到了三个稳定骨架：可复用内核、分层策略链、统一能力面。对任何要做长期 agent 产品的人，这三件事都比功能清单更重要。**

最近 Claude Code 的源码再次成为开发者圈的高热话题，一个直接原因是 2026 年 4 月的意外源码暴露事件，让大量人第一次有机会从更接近实现的角度观察这款产品的内部结构 [[1]](https://techcrunch.com/2026/04/01/anthropic-took-down-thousands-of-github-repos-trying-to-yank-its-leaked-source-code-a-move-the-company-says-was-an-accident/) [[2]](https://www.theguardian.com/technology/2026/apr/01/anthropic-claudes-code-leaks-ai)。

但如果只是围着“泄露了什么”看热闹，其实收获不大。更有价值的问题是：**Claude Code 这种已经被大量真实开发者使用的 agentic coding 产品，到底把哪些架构设计做成了长期可积累的工程资产？**

我这次不想泛泛讲 Claude Code 有哪些功能，也不想把整套系统摊成几十个模块逐个点名。基于 Anthropic 官方仓库、Claude Agent SDK 文档，以及几份最近的源码分析资料，我更想收敛出**不超过 3 个**真正值得学习的设计点。因为真正有价值的架构学习，不是把 feature list 抄一遍，而是抓住那几个能迁移到自己系统里的骨架。

这篇文章最后只讲三件事：

1. **把 agent 内核从产品外壳里剥离出来**
2. **把工具调用变成一条有明确优先级的策略执行链**
3. **把扩展能力做成文件系统原生、可委派、可组合的能力面**

## 一、为什么现在重新看 Claude Code 架构有意义

Claude Code 不是一个“实验室 demo 型 agent”，而是已经被 Anthropic 长期迭代、持续产品化的 coding assistant。官方仓库对它的定义非常直接：它是一个 living in your terminal 的 agentic coding tool，能理解代码库、执行例行任务、解释复杂代码并处理 git workflow [[3]](https://github.com/anthropics/claude-code)。

但真正让我觉得值得研究的，不是它能不能“写代码”，而是它明显已经跨过了很多 agent 产品经常卡住的阶段：

- 不再只是 prompt + tool call 的薄封装
- 不再只是 CLI 皮相上的小工具
- 也不再只是某个模型特性的演示器

最近几份源码分析资料给出的结构也很能说明问题：整个系统里既有 `main.tsx` 这种 CLI/REPL 启动入口，也有 `query.ts` 这样的主 agent loop，还有 `QueryEngine.ts` 这种更偏 headless lifecycle 的引擎层；同时还存在 commands、tools、components、services、state、tasks、plugins、coordinator 等明确分层 [[4]](https://github.com/chauncygu/collection-claude-code-source-code) [[5]](https://github.com/ComeOnOliver/claude-code-analysis)。

这意味着 Claude Code 值得学的地方，不是“它模块很多”，而是：**它已经把一个 agent 产品从单进程脚本，做成了带内核、策略、扩展层和多种交互表面的系统。**

## 二、重点一：把 agent 内核从 CLI / SDK / UI 外壳里剥离出来

如果只能选一个我最想学的点，我会选这个：**Claude Code 明显不是“先做 CLI，再硬凑 SDK”，而是在往一个可复用 agent kernel 的方向走。**

### 1. 源码层面的信号：入口层和执行层是分开的

最近的源码结构分析里，一个特别关键的信息是：

- `main.tsx` 负责 CLI entry 和 REPL bootstrap
- `query.ts` 是主 agent loop
- `QueryEngine.ts` 是 SDK / headless query lifecycle engine [[4]](https://github.com/chauncygu/collection-claude-code-source-code)

这三个名字放在一起，其实已经说明了一个架构意图：

- CLI 只是交互壳层
- 主查询循环是执行层
- 还有一层更抽象的 engine 可以脱离 UI 运行

如果一个系统只有 `main.tsx` 和一堆直接耦合的 side effects，那你很难把它变成 SDK，也很难把它接到别的宿主环境里。

### 2. 官方文档层面的信号：SDK 和 Claude Code 共享同一能力核心

Anthropic 的 Agent SDK overview 直接写了：Claude Code 强大的那些能力，在 SDK 里都可用 [[6]](https://platform.claude.com/docs/en/agent-sdk/overview)。这句话听起来像营销，但它背后对应的是一个很硬的工程事实：

- 如果 CLI 和 SDK 不是共享同一条核心能力链
- 那么“同一能力在不同表面可用”这件事很快就会变成维护灾难

官方示例里的 `query()` 本身就很能说明问题：调用方不是在操作某个 CLI 进程，而是在消费一个 agent 查询流，并通过 `ClaudeAgentOptions` 配置允许的工具、settings source、hooks、MCP servers、subagents 等 [[6]](https://platform.claude.com/docs/en/agent-sdk/overview)。

这更像是：

- 一个可嵌入的 agent runtime
- 再套多个 product shell

而不是：

- 一个 terminal 工具
- 再勉强暴露一些 API

### 3. 为什么这个设计特别值得学

很多团队做 agent 产品时，第一版很容易写成：

- 一个 CLI
- 一堆命令分支
- 一坨状态变量
- 直接绑死在终端输入输出上

这种做法前期快，但后面会立刻遇到几个问题：

- 想加 API server 时重写一遍
- 想接 GUI 时重写一遍
- 想做批处理/后台任务时又重写一遍
- 想开放 SDK 时发现没有稳定内核可抽

Claude Code 的做法至少给了一个更成熟的方向：**先把 agent loop、tool orchestration、session lifecycle、context management 这类东西沉成内核，再让 CLI、SDK、插件和其他宿主界面共享这套内核。**

### 4. 这对我们最直接的启发

如果你在做任何 agentic product，不管是 coding agent、workflow agent 还是企业助手，都应该尽量避免把以下几样东西写死在 UI 层：

- 会话生命周期
- 工具调用调度
- 上下文压缩
- 权限决策
- 事件流

这些应该尽量沉到 headless engine 里。界面只是：

- 终端
- Web
- IDE 面板
- API
- 自动化作业

中的一种外壳。

**Claude Code 最值得学的第一点，不是它用了 Ink 或 TypeScript，而是它明显在把 agent 做成“内核先行”的产品。**

## 三、重点二：把工具调用变成一条有优先级的策略执行链

如果说第一点是“结构怎么拆”，那第二点就是“风险怎么控”。我认为 Claude Code 很成熟的一点是：它没有把工具调用权限做成一个单独的 yes/no 开关，而是做成了一条**分层决策流水线**。

### 1. 官方权限文档已经把优先级写得很清楚

Claude 的 permissions 文档明确给出了权限评估顺序 [[7]](https://platform.claude.com/docs/en/agent-sdk/permissions)：

1. Hooks
2. Deny rules
3. Permission mode
4. Allow rules
5. `canUseTool` callback

这个顺序非常有意思，因为它不是“先看全局模式，再看细则”，而是：

- 先给 hooks 一个最早拦截/修改机会
- 再执行硬 deny
- 再应用全局 permission mode
- 再补 allow
- 最后再交给 runtime callback 做兜底

这说明 Claude Code 的权限系统不是一个布尔值，而是一条**可插入、可声明、可交互、可兜底**的决策链。

### 2. Hooks 不是观察器，而是执行控制点

Claude hooks 文档更进一步说明，hook 在事件发生后不是只能记录日志，而是可以：

- allow
- deny
- modify input
- inject context [[8]](https://platform.claude.com/docs/en/agent-sdk/hooks)

比如官方示例里：

- 可以拦截 `Write` 工具，把 `file_path` 自动改写到 `/sandbox`
- 可以阻止写 `/etc`
- 可以对只读工具自动批准
- 可以追踪 subagent stop 事件 [[8]](https://platform.claude.com/docs/en/agent-sdk/hooks)

这说明 Claude Code 把 hooks 放在了真正有权力的位置上：不是“事件发完你自己看着办”，而是“工具真正执行前，我允许你改流程”。

### 3. 这套设计为什么比单一 permission mode 更成熟

很多 agent 系统的权限设计停留在三档：

- 全部询问
- 全部放行
- 全部拒绝

这对 demo 足够，但对生产系统远远不够。因为现实里的策略通常是混合的：

- 读文件可以自动过
- 写文件要看路径
- shell 里 `git status` 可以放
- `rm -rf` 必须拦
- 某些 MCP server 允许，另一些必须审计

Claude Code 的设计把这些需求拆到了不同层：

- Hooks 适合做动态策略和上下文注入
- Allow / deny rules 适合做声明式规则
- Permission mode 适合做全局姿态
- Callback 适合做人机交互审批

这是一种非常典型的**policy stack** 思路，而不是一个 permission flag。

### 4. 为什么这很值得学

只要你的 agent 能：

- 读写文件
- 跑 shell
- 调 MCP
- 发请求
- 生成代码并修改仓库

那权限系统就绝对不该只是“要不要弹窗”。真正成熟的设计应该至少回答：

- 这次调用能不能被静态规则挡住
- 能不能被动态 hook 改写
- 全局模式是什么
- 最后谁来拍板

**Claude Code 第二个最值得学的点，就是它把工具使用的风险控制设计成了多层策略链，而不是单一审批开关。**

## 四、重点三：把扩展能力做成文件系统原生、可委派、可组合的能力面

很多 agent 产品的扩展性做法是：

- 写死一堆内置命令
- 再开放一个插件 API
- 再另外做一套 prompt 模板机制
- 再另外搞一个 tools registry

结果就是：扩展能力很多，但彼此完全不像同一个系统。

Claude Code 更值得学的地方在于：**它在努力把“扩展能力”收敛成一组可以被统一发现、统一加载、统一委派的能力面。**

### 1. 文件系统不是配置角落，而是产品表面的一部分

Agent SDK overview 已经明确写了 Claude Code 的 filesystem-based configuration 可以把这些能力加载进来 [[6]](https://platform.claude.com/docs/en/agent-sdk/overview)：

- `.claude/skills/*/SKILL.md`
- `.claude/commands/*.md`
- `CLAUDE.md`
- plugins

也就是说：

- 技能是文件
- 命令是文件
- memory / system prompt 也是文件
- project-level behavior 也是文件系统的一部分

这不是“小配置项”，而是一种产品设计立场：**把 agent 的很多可定制能力变成可版本化、可跟仓库一起走的 artifact。**

### 2. Skills、Plugins、Slash Commands 在往同一套能力模型收敛

技能文档里写得很清楚：Skills 是以 `SKILL.md` 形式存在的 filesystem artifact，Claude 会自动发现，并在合适时自主调用 [[9]](https://platform.claude.com/docs/en/agent-sdk/skills)。

Slash Commands 文档则明确表示，`.claude/commands/` 是 legacy format，而推荐格式已经转向 `.claude/skills/<name>/SKILL.md`，既支持 `/name` 调用，也支持 Claude 自主触发 [[10]](https://platform.claude.com/docs/en/agent-sdk/slash-commands)。

Plugins 文档进一步把插件定义成可以打包这些能力的容器：

- Skills
- Agents
- Hooks
- MCP servers [[11]](https://platform.claude.com/docs/en/agent-sdk/plugins)

这个方向特别值得注意，因为它说明 Claude Code 不是在无限增加“不同种类的扩展点”，而是在把这些扩展点收敛到一个更统一的能力模型里。

### 3. Subagents 和 MCP 不是散装 feature，而是能力委派机制

Subagents 文档里，Anthropic 直接写出它们的价值：

- context isolation
- parallelization
- specialized instructions and knowledge
- tool restrictions [[12]](https://platform.claude.com/docs/en/agent-sdk/subagents)

MCP 文档则把外部工具能力纳入统一命名规则：

- `mcp__<server-name>__<tool-name>`
- 用 `allowedTools` 精确授权
- 默认启用 tool search，在工具很多时只按需加载定义，减少上下文消耗 [[13]](https://platform.claude.com/docs/en/agent-sdk/mcp)

这意味着 Claude Code 的“能力扩展”不是单一机制，而是至少有两类委派：

- **委派给另一个 agent**：subagent
- **委派给外部工具服务器**：MCP

两者再和 skills / plugins / hook 体系拼起来，最终形成的是一个统一的能力网络。

### 4. 为什么这个设计特别值得学

很多团队做到后面都会遇到一个问题：

- prompt 模板是一套
- 命令系统是一套
- agent 角色是一套
- tool 集成是一套
- 项目级自定义又是一套

然后这些能力互相不兼容，最后系统越来越像补丁拼盘。

Claude Code 的思路更像是：

- 让能力以 artifact 存在
- 让能力可被发现
- 让能力可被自主调用
- 让能力既能本地存在，也能被打包进 plugin
- 让能力既可以是 skill，也可以是 subagent，也可以是 MCP server

这带来的最大好处不是“功能多”，而是**系统的长期演化成本会更低**。因为你不是每加一种能力就发明一个新机制，而是在现有能力面上继续扩展。

**Claude Code 第三个最值得学的点，就是它在把扩展性做成一个统一的、文件系统原生的、可委派的能力模型。**

## 五、为什么我只挑这 3 个，不讲更多

如果硬要继续拆，Claude Code 当然还有很多可讲的地方：

- 上下文压缩与会话管理
- React/Ink 终端 UI
- 并行工具执行
- 成本跟踪
- 任务系统
- 多 agent 协调

最近的源码结构分析里，这些信号都能看到 [[4]](https://github.com/chauncygu/collection-claude-code-source-code) [[5]](https://github.com/ComeOnOliver/claude-code-analysis)。

但如果目标是“从最近源码里找出最值得我们学习的架构”，我反而更愿意收敛。因为真正能迁移到自己系统里的，往往不是某个具体 feature，而是这些更底层的设计原则：

- **先有内核，再有壳层**
- **先有策略链，再谈工具自治**
- **先把扩展面统一，再持续增加能力**

这三条，比“Claude Code 里有多少命令、多少 tool、多少 mode”更重要。

## 六、如果我们自己做 agent 产品，最小借鉴路径是什么

如果把 Claude Code 这 3 个设计点翻译成一个更务实的落地顺序，我会建议按下面的顺序来学，而不是一上来就模仿它的全部 feature。

### 1. 先抽内核，不要先堆界面

先把这些东西从 CLI / Web / IDE 界面里剥出来：

- query loop
- session state
- tool dispatch
- context compaction
- event stream

哪怕第一版界面很丑，只要内核是独立的，后面就还有持续演化的空间。

### 2. 第二步先补策略链，不要等出事再补权限

很多团队会先让 agent “能调工具”，等快上线了再补权限。这通常会导致权限系统永远只能打补丁。更稳的做法是尽早确定：

- deny 在哪里生效
- allow 在哪里生效
- hook 能不能改写输入
- 谁负责最终批准

这一步做对了，后面不管加 Bash、MCP 还是 subagent，系统都还能控住。

### 3. 最后再统一扩展面

等到前两步稳定后，再去统一：

- 技能怎么定义
- agent 角色怎么注册
- 命令如何发现
- 外部工具怎么接入
- 项目级自定义怎样随仓库分发

这时你会发现，Claude Code 最值得学的不是某一种扩展点，而是它把这些扩展点放进了同一个演化框架里。

如果顺序反过来，一开始就急着堆 plugin、skills、commands、agents，最后非常容易把系统做成一套没有内核、没有策略边界的“功能市场”。

## 七、我的最终判断

如果让我用一句话总结 Claude Code 最近这轮源码观察，我会说：

**Claude Code 最值得学的，不是它把 agent 做得多复杂，而是它把复杂性收敛到了几个稳定骨架上：一个可复用内核、一条可控策略链、一个统一能力面。**

这三件事分别解决的是三种最常见的 agent 产品病：

- 没内核，导致所有表面都要重写
- 没策略链，导致工具权限只能靠人工兜底
- 没统一能力面，导致扩展性最后变成 patchwork

所以如果我们要从 Claude Code 学点真正能迁移的东西，我建议优先学的就是这 3 个：

1. **内核与交互壳解耦**
2. **分层权限与 hook 执行链**
3. **文件系统原生的扩展与委派体系**

这些东西并不依赖你是不是做 terminal coding agent。只要你做的是：

- 有工具调用的 agent
- 有多表面交互的 agent
- 有长期扩展需求的 agent

它们几乎都会变成你的核心架构问题。

## 参考来源

| 编号 | 来源 | 用途 |
|------|------|------|
| [1] | [TechCrunch: Claude Code source code incident](https://techcrunch.com/2026/04/01/anthropic-took-down-thousands-of-github-repos-trying-to-yank-its-leaked-source-code-a-move-the-company-says-was-an-accident/) | 交代最近源码暴露事件背景 |
| [2] | [The Guardian: Claude’s code leak](https://www.theguardian.com/technology/2026/apr/01/anthropic-claudes-code-leaks-ai) | 交代近期源码公开背景与讨论热度 |
| [3] | [anthropics/claude-code](https://github.com/anthropics/claude-code) | 官方仓库与产品定位 |
| [4] | [collection-claude-code-source-code](https://github.com/chauncygu/collection-claude-code-source-code) | 近期源码结构与模块划分概览 |
| [5] | [claude-code-analysis](https://github.com/ComeOnOliver/claude-code-analysis) | 源码逆向分析与架构模块梳理 |
| [6] | [Claude Agent SDK overview](https://platform.claude.com/docs/en/agent-sdk/overview) | SDK 与 Claude Code 共享能力核心、filesystem-based config |
| [7] | [Claude permissions docs](https://platform.claude.com/docs/en/agent-sdk/permissions) | 权限评估顺序与规则/模式设计 |
| [8] | [Claude hooks docs](https://platform.claude.com/docs/en/agent-sdk/hooks) | hook 的拦截、改写、注入上下文能力 |
| [9] | [Claude skills docs](https://platform.claude.com/docs/en/agent-sdk/skills) | Skills 作为 filesystem artifact 的设计 |
| [10] | [Claude slash commands docs](https://platform.claude.com/docs/en/agent-sdk/slash-commands) | commands 向 skills 统一收敛 |
| [11] | [Claude plugins docs](https://platform.claude.com/docs/en/agent-sdk/plugins) | 插件如何打包 skills、agents、hooks、MCP |
| [12] | [Claude subagents docs](https://platform.claude.com/docs/en/agent-sdk/subagents) | 子代理的上下文隔离、并行化、工具约束 |
| [13] | [Claude MCP docs](https://platform.claude.com/docs/en/agent-sdk/mcp) | MCP 工具命名、授权、tool search、transport |
