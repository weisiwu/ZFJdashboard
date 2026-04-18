# OpenClaw能力地图：它支持哪些Tools与扩展机制？

> **封面**：covers/OpenClaw能力地图：它支持哪些Tools与扩展机制？_cover.png

**OpenClaw 真正值得研究的，不是它列出了多少工具名，而是它已经把能力拆成了原生 tools、skills、hooks、plugins、MCP 和 bundle 兼容层。理解这些层各自负责什么，才能判断你该在什么地方扩它，而不是把所有需求都塞进一个“插件”里。**

如果只把 OpenClaw 理解成“一个可以聊天、可以跑 agent 的壳”，那你会低估它很多。把官方文档和最近的 release 说明连起来看之后，更准确的理解应该是：**OpenClaw 不是只有一组 agent tools，而是围绕原生工具、技能、插件、Hook、MCP、provider capability 和 channel capability 组织起来的一整套扩展平台。**

这篇文章不打算只列一个“支持什么功能”的清单，而是回答三个更实用的问题：

1. OpenClaw 自带哪些核心 tools
2. OpenClaw 的扩展到底分哪几层
3. 如果我们要给 OpenClaw 增加能力，最合适的入口是哪一层

## 一、先看总图：OpenClaw 的能力不是一层，而是五层

OpenClaw 官方 `Tools and Plugins` 文档把三件事区分得很清楚：

- **Tools**：agent 真正调用的执行能力
- **Skills**：告诉 agent 什么时候、怎么用这些能力
- **Plugins**：把工具、能力提供者、命令、Hook 等打包起来 [[1]](https://docs.openclaw.ai/tools)

但如果继续往下拆，OpenClaw 的能力面其实至少有五层：

1. **Built-in tools**：OpenClaw 自带的执行能力
2. **Skills**：以 `SKILL.md` 形式组织的提示与命令能力
3. **Hooks**：拦截生命周期、消息、工具、网关事件的自动化层
4. **Plugins**：真正扩展 OpenClaw 产品表面的能力注册层
5. **MCP**：既能把外部 MCP server 纳入 OpenClaw，也能把 OpenClaw 自己暴露成 MCP server [[1]](https://docs.openclaw.ai/tools) [[2]](https://docs.openclaw.ai/tools/plugin) [[3]](https://docs.openclaw.ai/cli/mcp)

如果不把这五层拆开，你很容易把所有东西都叫成“插件”或者“工具”，最后很难判断扩展应该落在哪里。

## 二、OpenClaw 自带哪些 tools

官方 `Tools and Plugins` 页面已经把内建工具面列得很完整。OpenClaw 不是只有读写文件和跑命令，而是内建了一整套多模态、会话化、自动化工具 [[1]](https://docs.openclaw.ai/tools)。

### 1. 执行与代码操作类

最基础的一层是执行和代码改动：

- `exec`
- `process`
- `code_execution`
- `read`
- `write`
- `edit`
- `apply_patch` [[1]](https://docs.openclaw.ai/tools) [[4]](https://docs.openclaw.ai/tools/exec)

其中 `exec` 不只是“跑个 shell”。官方文档说明它带有：

- `/exec` 级别的 session override
- approval 流程
- allowlist / safe bins
- companion app / node host 审批
- OpenAI/Codex 路径下的 `apply_patch` 支持 [[4]](https://docs.openclaw.ai/tools/exec)

这意味着 OpenClaw 对“执行工具”不是裸放行，而是做成了一个带审批和安全策略的正式工具面。

### 2. 浏览器与网页能力

OpenClaw 内建浏览器能力，不只是 web fetch：

- `browser`
- `web_search`
- `x_search`
- `web_fetch` [[1]](https://docs.openclaw.ai/tools)

浏览器工具的官方文档说明，它支持：

- 独立 `openclaw` 浏览器 profile
- tab 控制
- click/type/drag/select
- snapshot、screenshot、PDF
- `user` profile 挂接已有 Chrome 登录态 [[5]](https://docs.openclaw.ai/tools/browser)

这点非常关键，因为它说明 OpenClaw 的 browser 不只是“抓网页文本”，而是更接近一套正式的 browser automation surface。

### 3. 会话与 agent 编排类

OpenClaw 还把 session / subagent 相关能力直接做成工具：

- `sessions_*`
- `subagents`
- `agents_list`
- `session_status` [[1]](https://docs.openclaw.ai/tools)

也就是说，多 agent / 子会话能力在 OpenClaw 里不是外挂，而是核心工具面的一部分。这和前面那篇关于 OpenClaw subagent 的笔记是一致的：它把并发和拆分建立在 session tools 上，而不是藏在内部实现里。

### 4. 消息、自动化和网关控制类

OpenClaw 还有一批很容易被忽视的工具：

- `message`
- `cron`
- `gateway`
- `nodes`
- `canvas` [[1]](https://docs.openclaw.ai/tools)

尤其 `gateway` 工具，官方直接列出了：

- `config.schema.lookup`
- `config.get`
- `config.patch`
- `config.apply`
- `update.run` [[1]](https://docs.openclaw.ai/tools)

这意味着 OpenClaw 不是只给 agent 操作工作区文件，还允许它在一定策略下操作 gateway 自身的配置面。

### 5. 多模态生成类

最近几个版本里，OpenClaw 的内建工具面还明显往多模态扩展：

- `image`
- `image_generate`
- `music_generate`
- `video_generate`
- `tts` [[1]](https://docs.openclaw.ai/tools) [[6]](https://github.com/openclaw/openclaw/releases/tag/v2026.4.5)

2026.4.5 的 release note 明确提到：

- 新增 built-in `video_generate`
- 新增 built-in `music_generate`
- 引入 bundled Comfy workflow media plugin，支持 image / video / workflow-backed music [[6]](https://github.com/openclaw/openclaw/releases/tag/v2026.4.5)

这说明 OpenClaw 的 tool surface 正在从 coding / chat 扩展到完整的 media workflow。

## 三、Skills：这不是工具，而是“能力说明书 + 可调用入口”

Skills 文档把这层定义得很清楚：它们是以 `SKILL.md` 为核心的能力单元，负责告诉 agent 什么时候、如何使用某项能力 [[7]](https://docs.openclaw.ai/tools/skills)。

### 1. Skills 的几个关键特征

OpenClaw 的 skills 支持：

- 多级位置与优先级
- per-agent 与 shared skills
- agent allowlist
- 插件打包 skills
- ClawHub 安装与更新 [[7]](https://docs.openclaw.ai/tools/skills)

官方列出的优先级包括：

- `skills.load.extraDirs`
- bundled skills
- `~/.openclaw/skills`
- `~/.agents/skills`
- `<workspace>/.agents/skills`
- `<workspace>/skills` [[7]](https://docs.openclaw.ai/tools/skills)

这意味着 skills 本质上已经是一个**可覆盖、可分层、可随工作区分发**的 artifact 系统。

### 2. Skills 不只是 prompt，还能变成 slash command

这点非常值得注意。Skills 可以声明：

- `user-invocable`
- `disable-model-invocation`
- `command-dispatch: tool`
- `command-tool`
- `command-arg-mode` [[7]](https://docs.openclaw.ai/tools/skills)

也就是说，一个 skill 不一定只能“被模型在 prompt 里看到”，它还可以：

- 变成用户 slash command
- 甚至绕过模型，直接 deterministic 地 dispatch 到某个 tool

这让 skills 的角色非常特别：**它既像 prompt artifact，又像命令封装层。**

### 3. Skills 还带环境注入和 gating

官方文档还提到 skills 支持：

- load-time filters
- `skills.entries.<key>.env`
- `skills.entries.<key>.apiKey`
- run 结束后恢复原始环境
- skills watcher 自动刷新 [[7]](https://docs.openclaw.ai/tools/skills)

这说明 OpenClaw 的 skill 不是一段静态 Markdown，而是一个带配置、带环境、带生命周期的运行辅助单元。

## 四、Hooks：OpenClaw 的自动化与拦截层

OpenClaw 的 hooks 不只是“做点日志”。官方 hooks 文档明确给出了事件体系、目录发现规则和启停方式 [[8]](https://docs.openclaw.ai/automation/hooks)。

### 1. Hook 能看哪些事件

文档列出的事件包括：

- `command:new`
- `command:reset`
- `command:stop`
- `session:compact:before`
- `session:compact:after`
- `session:patch`
- `agent:bootstrap`
- `gateway:startup`
- `message:received`
- `message:transcribed`
- `message:preprocessed`
- `message:sent` [[8]](https://docs.openclaw.ai/automation/hooks)

而 plugin hooks 那一层还包括：

- `before_tool_call`
- `before_agent_reply`
- `before_install` [[8]](https://docs.openclaw.ai/automation/hooks)

这说明 OpenClaw 的 hooks 不是只有“命令触发器”，而是横跨消息流、session、agent、gateway、工具执行的多层自动化接口。

### 2. Hook 从哪里发现

官方 discovery 顺序是：

1. bundled hooks
2. plugin hooks
3. `~/.openclaw/hooks/`
4. `<workspace>/hooks/` [[8]](https://docs.openclaw.ai/automation/hooks)

这和 skills 很像，也是一种分层覆盖模型。

### 3. Hook 不只是观察，还能拦截

在插件能力文档里，OpenClaw 明确说明：

- `before_tool_call: { block: true }` 可以终止后续 handler
- `before_tool_call: { requireApproval: true }` 可以暂停执行并请求审批
- `message_sending: { cancel: true }` 可以取消发送 [[9]](https://docs.openclaw.ai/plugins/agent-tools)

所以如果说 skills 更像“教 agent 怎么做”，那 hooks 更像“在系统关键节点插手控制”。

## 五、Plugins：OpenClaw 真正的扩展总线

如果只选一个“OpenClaw 扩展能力的总入口”，那就是插件系统。因为插件不只是加 tool，而是可以加一整个 capability surface。

### 1. Plugin 能扩什么

官方 `Building Plugins` 与 `Plugin Internals` 文档列出的注册点非常多：

- `api.registerProvider(...)`
- `api.registerCliBackend(...)`
- `api.registerChannel(...)`
- `api.registerSpeechProvider(...)`
- `api.registerRealtimeTranscriptionProvider(...)`
- `api.registerRealtimeVoiceProvider(...)`
- `api.registerMediaUnderstandingProvider(...)`
- `api.registerImageGenerationProvider(...)`
- `api.registerMusicGenerationProvider(...)`
- `api.registerVideoGenerationProvider(...)`
- `api.registerWebFetchProvider(...)`
- `api.registerWebSearchProvider(...)`
- `api.registerTool(...)`
- `api.registerCommand(...)`
- `api.registerHook(...)`
- `api.registerHttpRoute(...)`
- `api.registerCli(...)` [[10]](https://docs.openclaw.ai/plugins/architecture) [[9]](https://docs.openclaw.ai/plugins/agent-tools)

这已经不是“插件加一个功能”的范畴，而是接近一个**产品级 capability registry**。

### 2. Plugin 的所有权模型也很清楚

`Plugin Internals` 文档里一个特别重要的观点是：

- plugin 是 ownership boundary
- capability 是 core contract [[10]](https://docs.openclaw.ai/plugins/architecture)

官方甚至明确说：

- `openai` 插件拥有 OpenAI 文本、语音、图片等相关面
- `google` 插件拥有 Google 模型、媒体理解、图像生成、web search
- `firecrawl` 拥有 web fetch
- `qwen` 拥有文本、媒体理解和 video generation [[10]](https://docs.openclaw.ai/plugins/architecture)

这说明 OpenClaw 的插件体系不是到处塞功能点，而是在按“厂商能力面”和“功能能力面”做 ownership 划分。

### 3. 原生插件非常强，但也有强信任边界

官方写得很直白：

- native plugin 可以注册 tools、network handlers、hooks、services
- native plugin bug 可能 crash gateway
- 恶意 native plugin 等价于在 OpenClaw 进程里执行任意代码 [[10]](https://docs.openclaw.ai/plugins/architecture)

所以插件能力很强，但这不是浏览器扩展那种轻沙箱模型，而是更接近“进程内扩展模块”。

## 六、Plugin Bundles：OpenClaw 正在吃进 Claude / Cursor / Codex 生态

这是我觉得 OpenClaw 很有意思的一层。它不只支持原生 OpenClaw 插件，还支持兼容 bundle：

- `openclaw.plugin.json`
- `.codex-plugin/`
- `.claude-plugin/`
- `.cursor-plugin/` [[2]](https://docs.openclaw.ai/tools/plugin)

`Plugin Bundles` 文档说明，OpenClaw 当前能从 bundle 里映射这些能力 [[11]](https://docs.openclaw.ai/plugins/bundles)：

- `commands/` 和 `.cursor/commands/` 作为 skill roots
- `HOOK.md + handler.ts/js` 作为 hook pack
- `settings.json` 作为 embedded Pi defaults
- `.lsp.json` / `lspServers` 作为 LSP 默认配置
- `mcpServers` 作为 Pi 里的 MCP 工具来源

这非常重要，因为它说明 OpenClaw 的扩展策略不是只搞自家格式，而是在主动兼容周边 agent 工具生态。

当然，文档也明确列了“detected but not executed”的部分，比如：

- Claude agents
- hooks.json automation
- Cursor rules 等 [[11]](https://docs.openclaw.ai/plugins/bundles)

也就是说，OpenClaw 现在不是全量兼容，而是**选择性映射那些最容易纳入本体能力模型的部分**。

## 七、MCP：OpenClaw 是双向的，不只是接别人

OpenClaw 的 MCP 能力有两个方向，这一点特别值得单独拎出来。

### 1. OpenClaw 作为 MCP server

通过 `openclaw mcp serve`，OpenClaw 可以把自己暴露成一个 MCP server，让 Claude Code、Codex 或其他 MCP client 直接跟 OpenClaw 背后的 channel conversations 交互 [[3]](https://docs.openclaw.ai/cli/mcp)。

它暴露的 bridge tools 包括：

- `conversations_list`
- `conversation_get`
- `messages_read`
- `attachments_fetch`
- `events_poll`
- `events_wait`
- `messages_send`
- `permissions_list_open`
- `permissions_respond` [[3]](https://docs.openclaw.ai/cli/mcp)

这不是简单“把一个工具暴露出去”，而是把 OpenClaw 的 conversation routing 能力整个桥接给外部 agent。

### 2. OpenClaw 作为 MCP client registry

另一方面，OpenClaw 自己也管理 `mcp.servers` 配置，支持：

- `openclaw mcp list`
- `openclaw mcp show`
- `openclaw mcp set`
- `openclaw mcp unset` [[3]](https://docs.openclaw.ai/cli/mcp)

也就是说，OpenClaw 既能用别人家的 MCP server，也能把自己变成别人可消费的 MCP server。

### 3. Plugin Bundles 还能给 Pi 注入 MCP

更进一步，bundle 文档说明启用的 bundle 可以贡献 `mcpServers`，OpenClaw 会把它们合并进 embedded Pi 的有效设置里，并暴露 bundle MCP tools [[11]](https://docs.openclaw.ai/plugins/bundles)。

这意味着 MCP 在 OpenClaw 里不是孤立子系统，而是已经进入了 plugin / bundle / embedded agent 的统一能力面。

## 八、如果要扩 OpenClaw，应该从哪一层下手

这是最实用的问题。不是每种需求都该写插件。

| 你的目标 | 更适合的层 | 原因 |
|------|------------|------|
| 想教 agent 一套稳定做法 | Skills | 成本最低，最适合知识和流程封装 |
| 想把 slash command 直接映射到工具 | Skill + `command-dispatch: tool` | 比自写完整插件更轻 |
| 想在消息、工具、会话生命周期里做拦截 | Hooks | 适合观察与控制 |
| 想增加真正的新工具 | Plugin `registerTool` | 这是正式扩展工具面的入口 |
| 想接新模型、图片、语音、搜索供应商 | Provider plugin | 走 capability contract 更自然 |
| 想兼容 Claude / Cursor / Codex 生态资产 | Plugin bundles | OpenClaw 已经支持一部分 bundle 映射 |
| 想把 OpenClaw 对接给 Claude Code / Codex | `openclaw mcp serve` | 让外部 MCP client 消费 OpenClaw 会话面 |
| 想让 OpenClaw 使用外部 MCP 工具 | `mcp.servers` / bundle MCP | 这是纳入外部工具生态的标准路径 |

这个表背后的关键判断是：**OpenClaw 不是所有扩展都靠插件完成，它更像一个分层扩展平台。**

## 九、两个最值得照着做的扩展示例

如果你不想只停留在“我知道它支持什么”，而是想判断“我下一个扩展应该怎么做”，下面两个例子最有代表性。

### 1. 例子一：新增一个真正的 agent tool

如果你的目标是让 OpenClaw 多一个全新的执行能力，比如：

- 调内部服务
- 跑某个工作流
- 调企业私有 API
- 做结构化数据查询

那最标准的路径就是写一个原生 plugin，并通过 `registerTool` 注册工具。官方文档给出的最小示例已经非常清楚：

- 用 `definePluginEntry`
- 在 `register(api)` 里调用 `api.registerTool(...)`
- 为工具声明 name、description、parameters、execute [[9]](https://docs.openclaw.ai/plugins/agent-tools)

而且 OpenClaw 还区分：

- **required tool**：默认可用
- **optional tool**：需要用户加入 allowlist 才能使用 [[9]](https://docs.openclaw.ai/plugins/agent-tools)

这背后其实有一个很成熟的设计：**“扩工具”和“放权限”是两件事。** 你可以把工具注册进平台，但是否在某个环境里开放，还要再经过 `tools.allow`、plugin allow/deny、hook 审批等策略层。

所以如果你准备给 OpenClaw 接企业内部能力，我会优先建议你走这一层，而不是把复杂逻辑全塞进 skill。因为 skill 更适合“教 agent 怎么用能力”，而不是“创造一个新能力”。

### 2. 例子二：把 OpenClaw 反向接给 Claude Code / Codex

另一个非常有代表性的能力，不是“让 OpenClaw 多一个工具”，而是“让别的 agent 把 OpenClaw 当工具”。

这里的标准路径就是：

- 启动 `openclaw mcp serve`
- 让 Claude Code、Codex 或其他 MCP client 连接过来
- 通过 bridge tools 读会话、收事件、回消息、处理审批 [[3]](https://docs.openclaw.ai/cli/mcp)

官方文档列出的 bridge tools 包括：

- `conversations_list`
- `messages_read`
- `events_poll`
- `events_wait`
- `messages_send`
- `permissions_respond` [[3]](https://docs.openclaw.ai/cli/mcp)

这说明 MCP 在 OpenClaw 里不是一个“外部工具目录”，而是一种真正的**互操作层**：

- 你可以让 OpenClaw 消费外部 MCP server
- 也可以让外部 MCP client 消费 OpenClaw 的 conversation / routing / approval 能力

这比“给 OpenClaw 加一个 web API”更有意思，因为它直接把 OpenClaw 接进了当前最活跃的 agent 互联生态里。

## 十、最近最值得注意的能力趋势

从 2026.4.5 release 看，OpenClaw 最近的能力增长很有方向感 [[6]](https://github.com/openclaw/openclaw/releases/tag/v2026.4.5)：

- 内建 `video_generate`
- 内建 `music_generate`
- ComfyUI workflow media plugin 进入 bundled 路径
- ClawHub 搜索、安装流程进入技能面板
- 背景 Claude CLI run 通过 loopback MCP bridge 暴露 OpenClaw tools
- ACPX runtime 更深地进入内建 runtime

这几条放在一起看，说明 OpenClaw 最近的演进方向不是“多加几个命令”，而是：

- 持续扩张 tool surface
- 持续加强 plugin / marketplace / bundle 分发
- 持续把外部 agent runtime 和 MCP 桥接纳入统一能力面

## 十一、我的最终判断

如果让我给一个结论，我会说：**OpenClaw 真正强的地方，不是它支持多少个 tool 名称，而是它已经把“能力”做成了分层系统。**

它至少同时具备：

- 一套很丰富的内建工具面
- 一套以 `SKILL.md` 为核心的知识/命令层
- 一套可拦截生命周期的 hooks 体系
- 一套可注册 provider、channel、tool、route、CLI 的插件系统
- 一套双向 MCP 桥接能力
- 一套兼容 Claude / Cursor / Codex bundle 的生态吸收层

所以如果你问：“OpenClaw 支持哪些能力，尤其是 tools 和扩展？”

更准确的回答不是一张 feature list，而是：**它已经不是一个单纯的 agent app，而是在往一个带原生工具、插件总线、能力契约和生态兼容层的 agent platform 走。**

## 参考来源

| 编号 | 来源 | 用途 |
|------|------|------|
| [1] | [Tools and Plugins - OpenClaw](https://docs.openclaw.ai/tools) | 内建 tools 总览与工具/技能/插件三层关系 |
| [2] | [Plugins - OpenClaw](https://docs.openclaw.ai/tools/plugin) | 插件安装、配置、发现、enablement 规则 |
| [3] | [mcp - OpenClaw](https://docs.openclaw.ai/cli/mcp) | OpenClaw 作为 MCP server 与 MCP registry 的双向能力 |
| [4] | [Exec Tool - OpenClaw](https://docs.openclaw.ai/tools/exec) | `exec`、审批、安全策略、`apply_patch` |
| [5] | [Browser (OpenClaw-managed) - OpenClaw](https://docs.openclaw.ai/tools/browser) | 浏览器自动化能力与 profile 模式 |
| [6] | [OpenClaw v2026.4.5 release](https://github.com/openclaw/openclaw/releases/tag/v2026.4.5) | 最近新增 video/music/Comfy/plugin flows 等能力 |
| [7] | [Skills - OpenClaw](https://docs.openclaw.ai/tools/skills) | skills 的位置、优先级、allowlist、dispatch、环境注入 |
| [8] | [Hooks - OpenClaw](https://docs.openclaw.ai/automation/hooks) | hooks 事件面、发现顺序、配置和 CLI |
| [9] | [Building Plugins - OpenClaw](https://docs.openclaw.ai/plugins/agent-tools) | `registerTool`、`registerHook`、可扩能力面 |
| [10] | [Plugin Internals - OpenClaw](https://docs.openclaw.ai/plugins/architecture) | capability model、ownership boundary、load pipeline |
| [11] | [Plugin Bundles - OpenClaw](https://docs.openclaw.ai/plugins/bundles) | Claude/Cursor/Codex bundle 的兼容映射 |
