# 一个 `user:` 前缀引发的 Issue 残留：OpenClaw 自动迭代的幂等性问题

> **主题**：OpenClaw / 自动迭代 / Issue 重复创建 / 幂等性
> **日期**：2026 年 3 月 18 日
> **标签**：OpenClaw / Multi-Agent / 幂等性 / Cron 调度

---

**50 轮自动迭代跑完后，GitHub 上留下 4 个状态从未变化的 open Issue。追查发现，早期迭代因 delivery 失败触发指数退避和重复调度，同一轮次最多创建了 7 个 Issue，而关闭逻辑只处理最新的那个——剩下的就成了孤儿。这是一个典型的分布式系统幂等性缺失问题，AI Agent 编排系统同样逃不开。**

> **封面**：covers/OpenClaw自动迭代Issue残留问题分析与幂等性设计_cover.png

## 现象：4 个永远不会被处理的 Issue

2026 年 3 月 17 日，teamclaw 项目的 50 轮自动迭代全部完成后，GitHub Issues 里仍有 4 个 open 状态的 `auto-iteration` Issue：

| Issue | 迭代轮次 | 创建时间 | 最后更新 | 评论数 |
|-------|---------|---------|---------|--------|
| #41 | iter-3 | 03-16 19:20 | 03-16 19:20 | 1（仅方向确定） |
| #48 | iter-9 | 03-16 21:10 | 03-16 21:10 | 1（仅方向确定） |
| #59 | iter-19 | 03-17 00:20 | 03-17 00:20 | 1（仅方向确定） |
| #60 | iter-19 | 03-17 00:30 | 03-17 00:31 | 2（方向确定 + PM 分析） |

它们的共同特征：

- 都只停留在"方向确定"阶段，没有后续的 architect 设计、coder 编码等步骤
- `updatedAt` 和 `createdAt` 几乎相同——创建之后就再也没人碰过
- GitHub assignees 为空——body 里写了"指派者: coder"，但这只是文本，不是真正的 GitHub assignment
- #59 和 #60 都是 iter-19，标题和方向完全一样——**重复创建**

直觉告诉我们这些 Issue "卡住了"，但对应的迭代轮次（iter-3、iter-9、iter-19）实际上早就完成了——只不过是通过**其他编号的 Issue** 完成的。

---

## 拆解：同一轮迭代为什么会有多个 Issue

拉出全部 87 个 `auto-iteration` Issue（83 closed + 4 open），按迭代轮次分组后，真相浮出水面：

| 迭代轮次 | Issue 数量 | Issue 编号 | 备注 |
|---------|-----------|-----------|------|
| iter-1 | **6** | #16, #26, #27, #33, #34, #35 | 最严重的重复 |
| iter-2 | **5** | #17, #28, #36, #37, #38 | |
| iter-3 | **7** | #18, #31, #32, #39, #40, #42, **#41(open)** | 含 1 个残留 |
| iter-9 | **4** | #23, #24, #49, **#48(open)** | 含 1 个残留 |
| iter-18 | **5** | #10, #11, #12, #13, #58 | |
| iter-19 | **4** | #14, #61, **#59(open)**, **#60(open)** | 含 2 个残留 |
| iter-20 | **3** | #15, #62, #63 | |
| iter-21 ~ iter-50 | **各 1** | #64 ~ #93 | 完全正常 ✅ |

规律非常明显：**iter-1 到 iter-20 大量重复创建，iter-21 开始恢复正常。**

### 重复创建的根因：delivery 失败 → 退避 → 重调度

这个问题和之前排查的 Agent 超时问题是同一条因果链 [[1]](https://docs.openclaw.ai/automation/cron-jobs)：

1. main agent 的 cron job 每 10 分钟触发，执行一轮迭代
2. 迭代过程中，main agent 创建一个 GitHub Issue，然后通过 subagent 分发给 coder 执行
3. 执行完成后，cron job 的 delivery 阶段尝试通过 Feishu 发送通知
4. 因为 Feishu target 格式缺少 `user:` 前缀，delivery 返回 HTTP 400
5. OpenClaw 将整个 job 标记为 `error`，触发指数退避（30s → 1m → 5m → 15m → 60m）[[2]](https://docs.openclaw.ai/automation/cron-jobs)
6. 退避结束后 cron 重新触发，main agent 不知道上一轮已经创建过 Issue，**于是又创建了一个**

这就是 iter-1 能创建 6 个 Issue 的原因——delivery 反复失败，cron 反复重试，每次重试都创建新 Issue。

### 关闭逻辑的缺陷：只关"最新的"

当 main agent 判断某一轮迭代完成时，它的关闭逻辑是：搜索该轮次最新的 open Issue → 关闭它 → 进入下一轮。

问题在于：如果同一轮次有 7 个 Issue（如 iter-3），关闭逻辑可能只关了其中的 6 个，漏掉了 #41。或者更准确地说，关闭逻辑是分批执行的——早期创建的 Issue 在后续的某个重试轮次中被"补关"了，但 #41 恰好处在一个缝隙里：它被创建后，main agent 的下一次重试创建了 #42 并且成功完成了迭代，关闭时只找到了 #42，#41 就被遗漏了。

这是一个经典的**竞态条件**（race condition）：多个重试实例并行操作同一组资源（GitHub Issues），但没有全局锁或幂等性保护。

---

## 本质：AI Agent 系统的幂等性问题

这个问题放到更大的背景下看，其实是分布式系统中最经典的问题之一——**幂等性**（idempotency）。

### 什么是幂等性

一个操作如果执行一次和执行多次的效果完全相同，就是幂等的。HTTP GET 是幂等的（请求 100 次返回相同结果），HTTP POST 通常不是（提交 100 次会创建 100 条记录）。

main agent 创建 Issue 的操作就是一个**非幂等操作**——每次调用 GitHub API 的 `POST /repos/{owner}/{repo}/issues` 都会创建一个新 Issue，无论之前是否已经创建过同轮次的 Issue。

### AI Agent 系统为什么特别容易踩这个坑

传统分布式系统中，幂等性有成熟的解决方案：给每个请求分配唯一 ID，服务端用这个 ID 去重 [[3]](https://dev.to/arif/ai-agent-failures-are-distributed-systems-failures-heres-the-complete-mapping-216k)。但 AI Agent 系统有几个额外的复杂性：

- **LLM 是非确定性的**：同样的 prompt，每次调用可能产生不同的输出。重试一个 agent step 不等于"重放"——它可能做出完全不同的决策
- **副作用难以回滚**：agent 创建了一个 GitHub Issue、发了一条飞书消息、修改了一个文件——这些副作用在重试时无法自动撤销
- **错误边界模糊**：OpenClaw 的 cron status 不区分"LLM 失败"和"delivery 失败" [[2]](https://docs.openclaw.ai/automation/cron-jobs)，导致本不该重试的操作（已成功执行但 delivery 失败）被当作失败重试了

社区里也有人遇到过类似问题。GitHub Issue #8520 报告了 isolated cron task 无限重试导致 API cooldown 的 bug——每次重试都创建新的 isolated session 并调用 LLM，连续的 429 错误直接冻结了整个 OpenClaw 实例 [[4]](https://github.com/openclaw/openclaw/issues/8520)。

### 理想的解决方案：任务级幂等键

参考分布式系统的做法 [[3]](https://dev.to/arif/ai-agent-failures-are-distributed-systems-failures-heres-the-complete-mapping-216k)，agent 的每个"有副作用的步骤"应该有一个幂等键（idempotency key）：

```
幂等键 = hash(jobId + iterationNumber + stepName)
```

执行流程变成：

```
1. 生成幂等键：key = hash("teamclaw001" + "iter-3" + "create-issue")
2. 检查 store：这个 key 执行过吗？
   - 是 → 返回上次的结果（Issue #41 的 URL），跳过创建
   - 否 → 创建 Issue，记录结果到 store
3. 继续下一步
```

这样无论 cron 重试多少次，同一轮迭代只会创建一个 Issue。

OpenClaw 目前没有内置这个机制——cron 的重试策略只关注"成功/失败"，不关注"这个任务的副作用是否已经产生" [[1]](https://docs.openclaw.ai/automation/cron-jobs)。GitHub Issue #24355 提出了更细粒度的重试策略（区分 transient/permanent 错误），但还没有涉及幂等性 [[5]](https://github.com/openclaw/openclaw/issues/24355)。

---

## 当前的缓解措施

在 OpenClaw 原生支持幂等性之前，可以通过几个配置降低重复创建的概率：

### 1. `--best-effort-deliver` 阻断重试链

```bash
openclaw cron edit <jobId> --best-effort-deliver
```

delivery 失败不再标记 job 为 error → 不触发退避 → 不重复调度 → 不重复创建 Issue [[6]](https://docs.openclaw.ai/cli/cron)。这是目前最有效的缓解手段。

### 2. Agent SOUL 中加入自检逻辑

在 main agent 的 `SOUL.md` 中添加规则：

```markdown
## 迭代 Issue 创建规则
- 创建新 Issue 前，先搜索是否已存在同轮次的 open Issue
- 搜索条件：label=auto-iteration, title 包含 "iter-{N}"
- 如果已存在，复用该 Issue 而不是创建新的
```

这相当于在 agent 层面实现了"查重"——不依赖底层框架的幂等性支持，而是靠 LLM 的推理能力来避免重复。不完美（LLM 可能忽略这条规则），但在大多数情况下有效。

### 3. 定期清理残留 Issue

对于已经产生的残留，用 `gh` CLI 批量关闭：

```bash
for i in 60 59 48 41; do
  gh issue close $i -R weisiwu/claw_issues \
    -c "历史残留：该迭代轮次已有其他 Issue 完成并关闭，此为早期重复创建的副本。"
done
```

这次的 4 个残留已通过上述命令关闭。

---

## 更广的视角：AI Agent 编排的分布式系统陷阱

这次 Issue 残留问题虽然影响不大（就是多了几个垃圾 Issue），但它暴露的底层问题——**非幂等操作 + 自动重试 = 资源泄漏**——在 AI Agent 系统中是普遍存在的。

几个常见的场景：

| 场景 | 非幂等操作 | 重试后果 | 缓解方案 |
|------|-----------|---------|---------|
| 本次案例 | 创建 GitHub Issue | 同轮次多个 Issue | best-effort-deliver + agent 自检 |
| 发送通知 | POST 飞书消息 | 用户收到重复消息 | 消息去重 ID |
| 代码提交 | git commit + push | 重复 commit | commit message 检查 |
| 文件生成 | 写入磁盘 | 覆盖或重复文件 | 文件名含幂等键 |
| API 调用 | 调用外部服务 | 重复计费/操作 | idempotency-key header |

有篇文章把这个问题说得很到位：**AI Agent 的失败模式就是分布式系统的失败模式** [[3]](https://dev.to/arif/ai-agent-failures-are-distributed-systems-failures-heres-the-complete-mapping-216k)。解决方案也是一脉相承的——幂等键、事务日志、回滚机制、断路器。只不过 LLM 的非确定性给这些方案增加了额外的复杂度：你不能简单地"重放"一个 agent step，因为 LLM 第二次可能做出完全不同的决策。

正确的做法是：**记录第一次执行的输出，重试时返回记录的结果而不是重新调用 LLM** [[3]](https://dev.to/arif/ai-agent-failures-are-distributed-systems-failures-heres-the-complete-mapping-216k)。这让 agent 工作流变成可恢复的——崩溃后从上次完成的步骤继续，而不是从头开始。

---

## 参考来源

| 编号 | 来源 | 说明 |
|------|------|------|
| 1 | [OpenClaw Docs - Cron Jobs](https://docs.openclaw.ai/automation/cron-jobs) | Cron job 调度机制、重试策略、session 管理 |
| 2 | [OpenClaw Docs - Cron Jobs: Retry Policy](https://docs.openclaw.ai/automation/cron-jobs) | 指数退避策略（30s → 60m），错误状态不区分 LLM/delivery |
| 3 | [AI Agent Failures Are Distributed Systems Failures](https://dev.to/arif/ai-agent-failures-are-distributed-systems-failures-heres-the-complete-mapping-216k) | Agent 系统的幂等性设计、任务级 idempotency key 模式 |
| 4 | [GitHub Issue #8520 - Cron isolated tasks infinite retry loop](https://github.com/openclaw/openclaw/issues/8520) | 无限重试导致 API cooldown 的 bug 报告 |
| 5 | [GitHub Issue #24355 - Cron retry policy for transient failures](https://github.com/openclaw/openclaw/issues/24355) | 社区提出的更细粒度重试策略（区分 transient/permanent） |
| 6 | [OpenClaw CLI - Cron Commands](https://docs.openclaw.ai/cli/cron) | `openclaw cron edit` 参数，包括 `--best-effort-deliver` |
| 7 | [GitHub Blog - Multi-agent workflows often fail](https://github.blog/ai-and-ml/generative-ai/multi-agent-workflows-often-fail-heres-how-to-engineer-ones-that-dont/) | GitHub 官方博客：multi-agent 可靠性工程实践 |
