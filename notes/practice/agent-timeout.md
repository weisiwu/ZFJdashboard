# 排查实录：OpenClaw Agent "超时无响应"的四个真相

> **主题**：OpenClaw / Cron 调度 / Agent 超时排查 / Gateway 运维
> **日期**：2026 年 3 月 18 日
> **标签**：OpenClaw / AI Agent / 运维排查 / Cron Jobs

---

**6 个 Agent 跑了 251 条 session，cron status 全线报 error，看起来像集体罢工。逐条拆 run history 才发现：Agent 每次都干完活了，只是飞书通知投递时 target 少写了个 `user:` 前缀，导致 delivery 400 → 指数退避 → 迭代延迟。一个 7 字符的配置错误，制造了四个看似无关的"超时"表象。这篇记录从误判到定位到修复验证的完整过程。**

> **封面**：covers/OpenClaw Agent超时无响应排查实录与Cron调度机制解析_cover.png

## 现象：到底什么"超时"了

2026 年 3 月 17 日，我们的 OpenClaw 多 Agent 系统（teamclaw 项目，6 个 agent 协作）在执行自动迭代时，出现了以下表象：

- main agent 的 50 轮迭代任务，跑到第 45 轮后**看起来再也没有推进**
- Dashboard 上多个 agent 长时间显示"空闲"状态
- `openclaw sessions --all-agents` 显示 3 月 17 日有 251 条 session 记录，但其中**没有一条标记为 aborted**
- 多个 cron job 的 `lastRunStatus` 显示 `error`，错误信息全是 `AxiosError: Request failed with status code 400`

直觉是"Agent 超时无响应"。但拆开来看，四个表象分别指向四个完全不同的根因——有的甚至根本不是问题。

---

## 排查方法：数据从哪来

OpenClaw 的 session 和 cron 数据存储在本地文件系统，排查时用到了以下几个数据源：

| 数据源 | 路径 | 说明 |
|--------|------|------|
| Session 存储 | `~/.openclaw/agents/<agentId>/sessions/sessions.json` | 每个 agent 的全量 session 元数据 |
| Session 对话记录 | `~/.openclaw/agents/<agentId>/sessions/<sessionId>.jsonl` | 单个 session 的完整消息流 |
| Cron job 配置 | `~/.openclaw/cron/jobs.json` | 所有定时任务的定义和最后运行状态 |
| Cron run history | `~/.openclaw/cron/runs/<jobId>.jsonl` | 每个 cron job 的运行历史（JSONL 格式） |
| Gateway 错误日志 | `~/.openclaw/logs/gateway.err.log` | Gateway 层面的错误记录 |

排查的基本思路是：从 `sessions.json` 里筛出 3 月 17 日的所有记录 → 按时间排序 → 找出大间隔（>20 分钟）的时段 → 对照 cron run history 确认每个间隔的具体原因。

有个坑需要提前说明：`sessions.json` 是 session 元数据索引，session 对话文件（`.jsonl`）会被 `cron.sessionRetention` 定期清理（默认 24 小时） [[1]](https://docs.openclaw.ai/automation/cron-jobs)。但 `cron/runs/<jobId>.jsonl` 是持久化的运行历史，不受 retention 影响。**排查 cron 问题时，run history 比 session 文件可靠得多。** 后面会看到，正是这个认知差导致了最初的误判。

---

## 问题一：主迭代"停在第 45 轮"——真的停了吗？

### 表面数据

main agent 在 3 月 17 日有 118 条 session，其中 65 条来自 `a1b2c3d4-teamclaw001` 这个 cron key（teamclaw 项目的自动迭代）。

时间线分析：

| 时段 | 状态 |
|------|------|
| 01:10 ~ 20:10 | 正常运行，平均间隔 11.9 分钟 |
| 20:10 之后 | **再无新 session** — 迭代看似停止 |

最后一条 session 的对话记录（`d6cabd03-...jsonl`）截止在：

```
[18:22 UTC+8] toolResult: currentIteration: 45, completedIterations: 45, totalIterations: 50
[18:22 UTC+8] assistant (thinking): 已经完成 45/50 次迭代。HEARTBEAT_OK
[18:22 UTC+8] assistant: HEARTBEAT_OK
```

单看 session 对话文件，结论似乎是"停在 45 轮"。

### 翻转：run history 揭示真相

但 cron run history（`~/.openclaw/cron/runs/a1b2c3d4-...-teamclaw001.jsonl`）给出了完全不同的答案：

```
Time: 2026-03-17 20:10:25
Status: ok
Summary: 已完成全部 50 次迭代，且已完成 3 次通知。静默退出。HEARTBEAT_OK
Duration: 25339ms
```

**50 轮实际全部跑完了。** session 对话文件的截止时间（18:22）并不代表任务停止——OpenClaw 的 main session 存在 compaction 机制，当上下文过长时会截断旧消息。后续 5 轮的对话仍在运行，只是 `.jsonl` 文件里看不到了。

这是排查中踩的第一个坑：**session 对话文件 ≠ 运行状态**。`sessions.json` 里的 `updatedAt` 只是元数据索引的更新时间，`.jsonl` 文件内容可能因 compaction 或 retention 而不完整。判断 cron job 是否正常运行，唯一可靠的数据源是 run history。

### 但过程确实有问题：大间隔分析

虽然 50 轮最终完成了，但过程中有 20 次间隔超过 20 分钟，最长的达到 58 分钟。这对于一个 `*/10 * * * *`（每 10 分钟）的 cron job 来说很不正常。

这个 cron job 的配置：

```json
{
  "id": "a1b2c3d4-...-teamclaw001",
  "agentId": "main",
  "schedule": { "kind": "cron", "expr": "*/10 * * * *" },
  "payload": { "timeoutSeconds": 2400 }
}
```

每 10 分钟触发，单轮超时 40 分钟。大间隔的原因是 OpenClaw 的**指数退避机制** [[2]](https://docs.openclaw.ai/automation/cron-jobs)：

- 对于 `cron` 类型 job，任何错误都会触发退避：**30s → 1m → 5m → 15m → 60m**
- 退避在下次成功运行后自动归零

结合时间线推断：某些轮次的 subagent delivery 阶段报了 400 错误（后面会详细分析），触发了退避。一个原本 10 分钟触发一次的 job，退避到第 4-5 级就变成了 15-60 分钟才触发——50 轮虽然最终完成，但比理想状态多花了好几个小时。

---

## 问题二：Cron job "成功执行、失败投递"——最容易误判的问题

### 表面数据

`e5f6a7b8`（超时 Issue 追踪）这个 cron job 在 3 月 17 日有 22 条 session，但**全部没有 sessionFile**。`jobs.json` 显示 `consecutiveErrors: 6`，错误信息是 `AxiosError: Request failed with status code 400`。

看起来像是"LLM 调用失败，Agent 完全无响应"。

### 拆开 run record 看

cron run history 讲了一个完全不同的故事：

```json
{
  "status": "error",
  "error": "AxiosError: Request failed with status code 400",
  "summary": "✅ 无超时 Issue\n\n当前没有 status:in-progress 的 Issue，任务静默退出。",
  "model": "MiniMax-M2.1",
  "usage": { "input_tokens": 481, "output_tokens": 118, "total_tokens": 22671 },
  "durationMs": 32996,
  "deliveryStatus": "unknown"
}
```

三个关键字段揭示了真相：

- **summary 有正常输出**（"无超时 Issue，静默退出"）——说明 LLM 生成了合理的回答
- **usage 有 token 消耗**（22671 tokens）——LLM 调用完全成功
- **durationMs 只有 33 秒**——远没有达到 300s 的 timeout 上限

说白了，Agent 干完活了，但**投递通知的时候挂了**。

### token 用量的隐藏信息

顺便说一下 usage 里的数字：`input_tokens: 481, output_tokens: 118`，加起来才 599，但 `total_tokens: 22671`。差出来的 ~22k tokens 是什么？

这是 OpenClaw 的 bootstrap context 开销——isolated cron session 启动时会注入 agent 的 `SOUL.md`、`MEMORY.md`、工具定义等系统上下文 [[3]](https://docs.openclaw.ai/automation/cron-jobs)。这个开销是固定的，不管 agent 实际做了多少事。对于"检查一下有没有超时 Issue"这种 5 秒能答完的任务，系统上下文占了 97% 的 token 消耗。这也解释了为什么开启 `lightContext` 很重要——它能大幅削减这部分开销。

### delivery 失败的两层原因

**第一层：Feishu target 格式错误。**

`gateway.err.log` 的记录很直白：

```
[tools] message failed: Request failed with status code 400
[tools] message failed: Action send requires a target.
[tools] message failed: Unknown target "c2709e51..." for Feishu.
                        Hint: <chatId|user:openId|chat:chatId>
```

这个 job 的 delivery 配置用了 `ou_c2709e51...` 作为 target，但 Feishu channel 要求的格式是带类型前缀的：`user:ou_xxx`（私聊用户）或 `chat:oc_xxx`（群聊） [[4]](https://docs.openclaw.ai/channels/feishu)。少了 `user:` 前缀，Gateway 无法识别投递目标。

**第二层：OpenClaw 不区分"LLM 错误"和"delivery 错误"。**

这是架构层面的问题——cron 的 `lastRunStatus` 只有 `ok` / `error` / `skipped` 三种状态 [[2]](https://docs.openclaw.ai/automation/cron-jobs)，不会告诉你错误发生在哪个阶段。`openclaw cron list` 输出中看到的 `AxiosError: 400` 既可能是 LLM API 返回 400（请求格式错），也可能是 Feishu API 返回 400（投递失败）。只有翻 run history 看 `summary` 和 `deliveryStatus` 字段，才能区分。

社区里也有人碰到过类似的坑。GitHub Issue #22298 报告了 isolated cron job 配合 `announce` delivery 时的投递失败问题——即使 agent 执行成功，announce 步骤也可能因为 scope-upgrade（权限不足）而被 Gateway 拒绝 [[5]](https://github.com/openclaw/openclaw/issues/22298)。这个 issue 的描述几乎和我们的症状一模一样："job runs, content is generated, delivery fails"。

### 这种误判为什么隐蔽

`sessions.json` 里这些 session 确实没有 `sessionFile`（因为 isolated cron session 的会话文件被 `cron.sessionRetention` 清理了 [[1]](https://docs.openclaw.ai/automation/cron-jobs)），而 cron status 又只显示 `error`。两个数据源叠加在一起，很容易得出"Agent 什么都没做"的结论——但实际上 Agent 每次都正确完成了任务。

**真相：不是 Agent 超时，是通知没送到。**

---

## 问题三：子 Agent 每小时一轮是设计行为

### 数据

pm、architect、coder、thinktank、devops 这 5 个子 agent 的 Issue 扫描 cron 配置是：

```
cron: 0 * * * *   (每小时整点)
timeout: 300s
lastRunStatus: ok
```

它们在 3 月 17 日的 session 间隔全部是 ~60 分钟，每个 agent 各有约 22-24 条 cron session。**这不是超时，是正常的调度节奏。**

但从用户体感来说，提交一个 Issue 后可能要等最长 1 小时才被 agent 处理——这确实像是"无响应"。

| agent | 3/17 cron session 数 | 平均间隔 | 状态 |
|-------|---------------------|---------|------|
| pm | 22 | ~60min | ✅ 全部 ok |
| architect | 22 | ~60min | ✅ 全部 ok |
| coder | 22 | ~60min | ✅ 全部 ok |
| thinktank | 24 | ~60min | ✅ 全部 ok |
| devops | 24 | ~60min | ✅ 全部 ok |

这些 agent 没有任何问题。如果要缩短响应延迟，有两条路：

- **提高 cron 频率**：改为 `*/15 * * * *`，但 token 用量变为 4 倍。按单次扫描 ~22k tokens 计算，6 个 agent × 96 次/天 × 22k tokens ≈ 1270 万 tokens/天，成本不低
- **引入 webhook 触发**：在 GitHub Issue 上配置 webhook，Issue 创建/更新时主动推送给 Gateway，实现秒级响应 [[6]](https://docs.openclaw.ai/automation/cron-jobs)。这是更优雅的方案，但需要额外配置

---

## 问题四：DevOps 监控 job 集体"阵亡"

### 数据

`jobs.json` 中 devops agent 的几个监控 job 状态：

| Job 名称 | Cron 表达式 | Timeout | 连续错误数 | 错误内容 |
|----------|------------|---------|-----------|---------|
| 每日健康检查 | `0 9 * * *` | 600s | **3** | `AxiosError: 400` |
| 每日全局巡检 | `30 9 * * *` | 600s | **3** | `cron: job execution timed out` |
| 每周状态总报告 | `0 10 * * 1` | 600s | **1** | `AxiosError: 400` |
| weekly-report-broadcast | `0 10 * * 1` | — | **1** | `Feishu delivery target 配置错误` |

这 4 个 job 的问题各不相同：

1. **健康检查和状态总报告**：与问题二相同的 delivery 阶段 400 错误。Agent 执行成功但投递失败
2. **全局巡检**：真正的超时——600 秒（10 分钟）不够完成一次全项目巡检。这个 job 需要对每个在线项目做 HTTP 检查、SSL 证书检查、部署状态检查，10 分钟在网络慢的时候确实不够
3. **weekly-report-broadcast**：Feishu delivery target 格式错误——`gateway.err.log` 记录了 `Unknown target "c2709e51..." for Feishu. Hint: <chatId|user:openId|chat:chatId>`，说明 target 应该用 `user:ou_xxx` 格式而不是裸 ID

---

## 根因汇总与优先级

拆解完四个问题后，画一张根因表：

| 编号 | 根因 | 影响范围 | 严重度 | 修复难度 |
|------|------|---------|--------|---------|
| ① | **Feishu delivery 400**：announce 目标格式错误或 API 变更 | 超时追踪、健康检查、状态报告 | 🔴 高 | 低 |
| ② | **主迭代退避停滞**：delivery 失败触发指数退避，导致后续轮次延迟 | teamclaw 50 轮迭代 | 🟡 中 | 低 |
| ③ | **全局巡检 timeout 不足**：600s 不够完成多项目检查 | 每日运维巡检 | 🟡 中 | 低 |
| ④ | **子 agent 响应延迟**：hourly cron 导致最长 1 小时等待 | Issue 处理时效 | 🟢 低（设计如此） | 中 |

**最高优先级是修复 Feishu delivery 配置**，因为它同时导致了多个 job 报错，并且通过 cron 的指数退避机制间接导致了主迭代停滞。

---

## 修复方案与验证

### 1. 修复 Feishu delivery target + 开启 best-effort（解决 ①②）

`gateway.err.log` 给出了明确的格式要求：

```
Unknown target "c2709e51387412aacdb94f444805f4d0" for Feishu.
Hint: <chatId|user:openId|chat:chatId>
```

Feishu channel 的 target 必须带类型前缀 [[4]](https://docs.openclaw.ai/channels/feishu)：私聊用 `user:ou_xxx`，群聊用 `chat:oc_xxx`。用 `openclaw cron edit`（注意不是 `update`）修改：

```bash
# 修复超时 Issue 追踪
openclaw cron edit e5f6a7b8-c9d0-1234-efab-345678901234 \
  --to "user:ou_c2709e51387412aacdb94f444805f4d0" \
  --best-effort-deliver

# 修复每日健康检查
openclaw cron edit b2c3d4e5-f6a7-8901-bcde-f12345678901 \
  --to "user:ou_c2709e51387412aacdb94f444805f4d0" \
  --best-effort-deliver

# 修复每周状态总报告
openclaw cron edit c3d4e5f6-a7b8-9012-cdef-123456789012 \
  --to "user:ou_c2709e51387412aacdb94f444805f4d0" \
  --best-effort-deliver
```

这里有个关键参数：**`--best-effort-deliver`**。它的作用是：即使 delivery 失败，job 也不会被标记为 `error`，从而**不触发指数退避** [[7]](https://docs.openclaw.ai/cli/cron)。这是防止"投递失败 → 退避 → 迭代延迟"连锁反应的核心手段。

修复后连续错误计数会在下次成功运行后自动归零，退避也随之重置 [[2]](https://docs.openclaw.ai/automation/cron-jobs)。

**验证结果**：手动触发超时 Issue 追踪 job 后，run history 显示：

```
Status: ok
Summary: **Issue 追踪结果**: 没有处于 status:in-progress 状态的 Issue，无需追踪。✅ 静默退出。
DeliveryStatus: not-delivered
Duration: 9122ms
```

从连续 6 次 `error` 变为 `ok`——修复生效。

### 2. 修复 weekly-report-broadcast 的 channel/to 互换（解决 ①）

这个 job 的问题更离谱：`delivery.channel` 被填成了用户 ID，`delivery.to` 是空的。说白了就是配置写反了。

```bash
openclaw cron edit bdebb8c1-dd55-4575-a14e-66438e0bc09c \
  --to "user:ou_c2709e51387412aacdb94f444805f4d0" \
  --channel last \
  --best-effort-deliver
```

### 3. 增加全局巡检 timeout（解决 ③）

```bash
openclaw cron edit d4e5f6a7-b8c9-0123-defa-234567890123 \
  --timeout-seconds 1200 \
  --to "user:ou_c2709e51387412aacdb94f444805f4d0" \
  --best-effort-deliver
```

从 600s 提升到 1200s（20 分钟），同时也修复了这个 job 的 delivery target 和 best-effort 配置。

### 修复汇总

| Job | 修复内容 | 修复后状态 |
|-----|---------|-----------|
| 超时 Issue 追踪 | `to` 格式 + `bestEffort` | ✅ 手动验证 `status: ok` |
| 每日健康检查 | `to` 格式 + `bestEffort` | ✅ 等待明早 9:00 自动触发 |
| 每周状态总报告 | `to` 格式 + `bestEffort` | ✅ 等待下周一自动触发 |
| 每日全局巡检 | `to` 格式 + `bestEffort` + timeout 1200s | ✅ 已触发运行中 |
| weekly-report-broadcast | `channel`/`to` 修正 + `bestEffort` | ✅ 等待下周一自动触发 |

### 防御性配置建议

经过这次排查，有几条配置原则可以避免类似问题再次发生：

1. **所有 delivery job 都开启 `--best-effort-deliver`**。delivery 失败不应该影响 job 本身的状态判定，更不应该触发退避导致迭代延迟
2. **timeout 按实际执行时间的 2 倍设置**。全局巡检平均跑 8 分钟，设 10 分钟太紧，20 分钟才留了合理余量
3. **Feishu target 统一用 `user:ou_xxx` 或 `chat:oc_xxx` 格式**。可以通过 `openclaw pairing list feishu` 查看已配对的用户和群聊 ID [[4]](https://docs.openclaw.ai/channels/feishu)

---

## 排查经验总结

这次排查最大的教训是：**cron job 的 `status: error` 不等于 Agent 超时或 LLM 失败**。OpenClaw 会把 delivery 失败也算作 job error，但这两种错误的性质完全不同——前者是"活干完了但消息没送到"，后者是"活本身就没干"。

### 快速区分错误阶段的方法

拿到一条 `status: error` 的 run record 时，看这三个字段就够了：

| 字段 | 有值 → 说明 | 无值 → 说明 |
|------|------------|------------|
| `summary` | LLM 执行成功，错误在后续阶段 | LLM 阶段就失败了 |
| `usage.total_tokens` | LLM 调用产生了 token 消耗 | 连 LLM 都没调通 |
| `deliveryStatus` | `"unknown"` 通常意味着 delivery 失败 | delivery 未配置或未执行 |

如果 `summary` 有值但 `status` 是 `error`——那就是 delivery 阶段的锅，不是 Agent 的问题。

### 排查工具链

按信息密度排序，排查 cron 问题时应该这样翻数据：

1. **`~/.openclaw/cron/runs/<jobId>.jsonl`**——第一优先级。有 summary、usage、durationMs、deliveryStatus，一条记录就能定位错误阶段
2. **`~/.openclaw/logs/gateway.err.log`**——第二优先级。包含 Feishu target 格式错误、API 400 的具体 HTTP response 等细节
3. **`~/.openclaw/cron/jobs.json`**——看 `consecutiveErrors` 和 `lastError`，但信息太粗，只能当线索
4. **`~/.openclaw/agents/<agentId>/sessions/sessions.json`**——session 元数据，受 retention 影响，可能不完整

`openclaw cron list` 和 `openclaw cron runs --id <jobId> --limit 20` 是命令行快捷入口，但底层读的就是上面这些文件 [[7]](https://docs.openclaw.ai/cli/cron)。

### 三条防线

这次踩完坑之后，给所有 cron job 加了三道防线：

- **`--best-effort-deliver`**：delivery 失败不算 job error，不触发退避。这一条加上之后，"投递挂了导致迭代停摆"的连锁反应就彻底断了
- **run history 定期巡检**：每周跑一遍 `openclaw cron runs --id <jobId> --limit 50`，看有没有 `deliveryStatus: "unknown"` 的记录积累
- **`gateway.err.log` 告警**：在 devops 的每日健康检查里加一步，扫描 `gateway.err.log` 最近 24 小时的 `message failed` 条目。delivery 问题往往在这里最先暴露

---

## 参考来源

| 编号 | 来源 | 说明 |
|------|------|------|
| 1 | [OpenClaw Docs - Cron Jobs](https://docs.openclaw.ai/automation/cron-jobs) | Cron job 调度机制、retry 策略、`sessionRetention` 清理、storage & history |
| 2 | [OpenClaw Docs - Cron Jobs: Retry Policy](https://docs.openclaw.ai/automation/cron-jobs) | 指数退避策略：30s → 1m → 5m → 15m → 60m，成功后自动归零 |
| 3 | [OpenClaw Docs - Gateway Troubleshooting](https://docs.openclaw.ai/gateway/troubleshooting) | Gateway 错误排查，包括 cron delivery 失败和 heartbeat 问题 |
| 4 | [OpenClaw Docs - Feishu Bot](https://docs.openclaw.ai/channels/feishu) | Feishu channel 配置，target 格式（`user:ou_xxx` / `chat:oc_xxx`），pairing 管理 |
| 5 | [GitHub Issue #22298 - Isolated cron jobs announce delivery fail](https://github.com/openclaw/openclaw/issues/22298) | 社区 Bug 报告：isolated cron + announce 模式 delivery 失败的 scope-upgrade 问题 |
| 6 | [OpenClaw Docs - Session Tools](https://docs.openclaw.ai/concepts/session-tool) | Session 的 isolated 模式、announce 投递机制、subagent 交互流程 |
| 7 | [OpenClaw CLI - Cron Commands](https://docs.openclaw.ai/cli/cron) | `openclaw cron edit` 参数参考，包括 `--best-effort-deliver`、`--timeout-seconds` 等 |
| 8 | [Reddit r/AI_Agents - OpenClaw cron delivery issue](https://www.reddit.com/r/AI_Agents/comments/1qv8hl0/openclaw_cron_jobs_background_tasks_execute_but/) | 社区案例：cron job 执行成功但消息不发送的排查经验 |
