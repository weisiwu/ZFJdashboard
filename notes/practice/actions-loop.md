# 告别空转：GitHub Actions 自动迭代调度从 Cron 轮询到循环执行的架构改造

> **主题**：GitHub Actions / CI/CD 调度模型 / 自动迭代
> **日期**：2026 年 3 月 18 日
> **标签**：GitHub Actions / CI/CD / 调度架构 / DevOps

---

**50 轮 AI Agent 迭代，Cron 轮询跑了 15.5 小时，换成 While 循环只要 6.3 小时——省掉的 9 小时全是每轮结束后傻等下一个 15 分钟窗口的空转时间。一个 while 循环加三个 workflow_dispatch 参数，把调度模型从「盲目的时钟驱动」切到「完成即触发」，是这次改造的全部内容。代价是丢掉了轮次隔离性，需要用 timeout 防挂死、用环境清理防状态泄露来补。**

> **封面**：covers/GitHub Actions自动迭代调度从轮询到循环的架构改造_cover.png

## 问题背景：15 分钟的间隔到底浪费了多少时间

我们的 AI Agent 系统（OpenClaw）通过 GitHub Actions 驱动自动迭代——每一轮迭代会扫描 GitHub Issues，调用 LLM 处理任务，然后等待下一轮。最初的调度方式非常直觉：用 Cron 表达式 `*/15 * * * *` 每 15 分钟触发一次 workflow。

```yaml
on:
  schedule:
    - cron: '*/15 * * * *'
```

跑了一轮 50 次迭代后，问题暴露得很明显：预计 12.5 小时完成的任务，实际耗时接近 20 小时。

拉出日志一看，原因分两层：

1. **正常轮次空等严重**：44 轮正常迭代平均只需 3 分钟，但每轮都被固定间隔拉到 15 分钟——多出来的 12 分钟纯粹在空转
2. **异常轮次雪上加霜**：6 轮因 LLM 接口超时耗时约 40 分钟，不仅超出了 15 分钟窗口，还连带错过了后续 2-3 个 Cron 触发点

说白了，Cron 轮询是一种"盲调度"——它不关心上一轮跑没跑完，到点就触发。这在 Agent 迭代这种**单轮耗时波动大、需要串行执行**的场景下，天然不合适。

---

## 两种调度模型的本质区别

在动手改之前，有必要搞清楚这两种调度模型的根本差异。

### Cron 轮询（Polling）

Cron 轮询是一种**时钟驱动**的调度方式。GitHub Actions 的调度器每分钟检查一次 Cron 表达式，时间匹配就启动一个新的 workflow run [[1]](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule)。

核心特征：
- 每次触发都是一个**独立的 workflow run**，彼此没有状态关联
- 调度器**不感知**上一轮的执行状态（是否完成、是否成功）
- 如果上一轮还在跑，需要靠 `concurrency` 配置防止并发 [[2]](https://docs.github.com/actions/writing-workflows/choosing-what-your-workflow-does/control-the-concurrency-of-workflows-and-jobs)
- 最小精度 5 分钟（GitHub 官方不保证分钟级准确性）

时间线大致是这样的：

```
00:00  cron 触发 → scan 开始
00:03  scan 完成 ✅
00:03~00:15  ⏸️ 空等 12 分钟
00:15  cron 触发 → scan 开始
00:17  scan 完成 ✅
00:17~00:30  ⏸️ 空等 13 分钟
00:30  cron 触发 → scan 开始（这轮比较慢）
00:45  cron 触发 → 上一轮还在跑，concurrency 阻止，跳过
01:00  cron 触发 → 上一轮还在跑，跳过
01:10  scan 完成 ✅（耗时 40 分钟）
01:10~01:15  ⏸️ 空等 5 分钟
01:15  cron 触发 → scan 开始
```

每一轮的「有效工作时间 / 总占用时间」比值非常低。3 分钟的 scan 占了 15 分钟的时间槽，利用率只有 20%。

### While 循环执行（Loop-based）

循环执行是一种**完成驱动**的调度方式。在同一个 workflow job 的 shell 脚本里用 `while` 循环串联多轮迭代，上一轮的 `openclaw scan` 命令返回后，立刻进入下一轮。

核心特征：
- 所有轮次在**同一个 job 进程内**串行执行
- 上一轮结束的信号就是命令返回——shell 的同步阻塞调用天然保证了这一点
- 轮间间隔完全可控（10 秒、30 秒，甚至 0 秒）
- 无需 `concurrency` 防并发，因为根本不存在并发

时间线变成这样：

```
00:00  Round 1 开始
00:03  Round 1 完成 ✅ → 等 10 秒
00:03  Round 2 开始
00:05  Round 2 完成 ✅ → 等 10 秒
00:06  Round 3 开始
...
01:20  Round 20 开始（慢轮次）
02:00  Round 20 完成 ✅ → 等 10 秒
02:00  Round 21 立刻开始
```

没有空等，没有窗口错过，总耗时 = 所有 scan 的实际用时之和 + 轮间间隔之和。

---

## 具体实现

改造后的 `agent-scan.yml` 关键部分：

### 触发方式

```yaml
on:
  # 每小时兜底（从每 15 分钟降频，仅作安全网）
  schedule:
    - cron: '0 * * * *'

  # Issue 事件实时响应
  issues:
    types: [opened, edited, labeled, unlabeled, assigned, unassigned]
  issue_comment:
    types: [created]

  # 手动触发 —— 连续迭代的主入口
  workflow_dispatch:
    inputs:
      agent:
        description: 'Agent to trigger'
        required: false
        default: 'all'
        type: choice
        options: [all, main, architect, designer, thinktank, pm, coder, devops]
      max_rounds:
        description: 'Max iteration rounds (1 = single run)'
        required: false
        default: '1'
        type: string
      pause_seconds:
        description: 'Pause between rounds in seconds (default 10)'
        required: false
        default: '10'
        type: string
```

三个触发源各司其职 [[3]](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_dispatch)：
- **`workflow_dispatch`**：日常跑批的主力，手动设置 `max_rounds=50` 连续执行
- **`issues` / `issue_comment`**：有新 Issue 或评论时实时响应一轮
- **`schedule`**：每小时兜底扫一次，防止手动链条意外中断后 Issue 被遗漏

### 循环执行核心逻辑

```bash
MAX_ROUNDS=$\{\{ steps.params.outputs.max_rounds }}
AGENT="$\{\{ steps.params.outputs.agent }}"
PAUSE=$\{\{ steps.params.outputs.pause }}
ROUND=1
SUCCESS=0
FAILED=0

while [ $ROUND -le $MAX_ROUNDS ]; do
    echo "🔄 Round $ROUND/$MAX_ROUNDS - $(date '+%Y-%m-%d %H:%M:%S')"

    START_TIME=$(date +%s)

    if [ "$AGENT" == "all" ]; then
      openclaw scan --all      # 同步阻塞：跑完才返回
    else
      openclaw scan --agent $AGENT
    fi

    EXIT_CODE=$?
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    if [ $EXIT_CODE -eq 0 ]; then
      echo "✅ Round $ROUND done (${DURATION}s)"
      SUCCESS=$((SUCCESS + 1))
    else
      echo "❌ Round $ROUND failed, exit=$EXIT_CODE (${DURATION}s)"
      FAILED=$((FAILED + 1))
    fi

    ROUND=$((ROUND + 1))

    # 轮间暂停（最后一轮不暂停）
    if [ $ROUND -le $MAX_ROUNDS ] && [ $PAUSE -gt 0 ]; then
      echo "⏳ Next round in ${PAUSE}s..."
      sleep $PAUSE
    fi
done

echo "📊 Total: $((SUCCESS + FAILED)) | ✅ $SUCCESS | ❌ $FAILED"
```

这段代码的关键在于 `openclaw scan --all` 是一个**同步阻塞调用**。Shell 会等这行命令执行完毕，拿到退出码之后，才继续往下走。不需要任何额外机制来"检测上一轮是否结束"——进程本身的执行顺序就是保证。

### 参数化设计

通过 `workflow_dispatch` 的 `inputs` 暴露三个参数：

| 参数 | 作用 | 默认值 |
|------|------|--------|
| `agent` | 指定扫描的 Agent 角色 | `all` |
| `max_rounds` | 最大迭代轮数 | `1` |
| `pause_seconds` | 轮间暂停秒数 | `10` |

在 GitHub Actions 页面手动触发时填入参数即可。比如设置 `max_rounds=50`、`pause_seconds=10`，就能连续跑 50 轮，每轮间隔 10 秒。

---

## 量化对比：时间节省了多少

用实际运行数据算一笔账。50 轮迭代中，44 轮正常（平均 3 分钟），6 轮 LLM 超时（平均 40 分钟）。

| 指标 | Cron 轮询（15min） | 循环执行（10s 间隔） |
|------|-------------------|---------------------|
| 正常轮总耗时 | 44 × 15min = 660min | 44 × 3min = 132min |
| 超时轮总耗时 | 6 × ~45min = 270min | 6 × 40min = 240min |
| 轮间等待 | 含在 15min 间隔内 | 50 × 10s ≈ 8min |
| **合计** | **~930min ≈ 15.5h** | **~380min ≈ 6.3h** |
| **时间利用率** | ~40% | ~98% |

最大的节省来自正常轮次：660 分钟压缩到 132 分钟，砍掉了 528 分钟的空等时间。这些时间在 Cron 模型下完全浪费了——机器在那干等着，什么都没做。

---

## 循环模型的隐性代价：你放弃了什么

效率提升不是没有代价的。从 Cron 切到循环执行，实质上是把**多个独立 workflow run 压缩成了一个长时间运行的单 job**。这个转变带来几个需要正视的问题。

### 轮次隔离性丧失

Cron 模式下，每轮迭代是一个独立的 workflow run，拥有干净的执行环境——独立的文件系统快照、独立的环境变量、独立的日志流。一轮失败不会污染下一轮的状态。

循环模式下，50 轮跑在同一个 shell 进程里。如果某一轮的 `openclaw scan` 修改了工作目录下的文件、写入了临时状态、或者泄露了环境变量，后续轮次都会受到影响。这在实践中表现为：第 1-30 轮正常，第 31 轮开始出现诡异错误——因为前面某轮残留的状态累积到了临界点。

应对方式是在每轮开始前做一次环境清理：

```bash
while [ $ROUND -le $MAX_ROUNDS ]; do
    # 每轮开始前清理临时文件，防止状态泄露
    rm -rf /tmp/openclaw_scan_* 2>/dev/null || true

    openclaw scan --all
    # ...
done
```

### 日志可读性下降

Cron 模式下，每轮一个 workflow run，在 GitHub Actions 页面上每轮有独立的日志页面，可以单独查看、搜索、下载。

循环模式下，50 轮的日志全部混在同一个 job 的同一个 step 输出里。当你要排查第 37 轮的问题时，需要在几千行日志里搜索 `Round 37`。日志量大时，GitHub 的 Web UI 甚至会截断显示。

改善方案：在每轮输出中加入明显的分隔线和时间戳（实现代码中已经包含），同时考虑将关键信息写入 workflow 的 Job Summary [[9]](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#adding-a-job-summary)：

```bash
# 每轮结束后写入 Job Summary
echo "| $ROUND | $STATUS | ${DURATION}s | $(date '+%H:%M:%S') |" >> $GITHUB_STEP_SUMMARY
```

### 单轮挂死风险

这是最容易被忽视的问题。Cron 模式下，即使某轮 scan 挂死，`timeout-minutes` 会在 job 级别兜底，而且不影响下一个 cron 触发的独立 run。

循环模式下，如果 `openclaw scan` 因为 LLM 接口无响应而永远不返回，整个 while 循环就卡死了——后面的所有轮次都无法执行，直到 350 分钟的 job 超时才会被 GitHub 强制杀掉。

解决方案是用 `timeout` 命令为每轮设置独立的超时上限 [[10]](https://www.baeldung.com/linux/bash-kill-child-process-after-timeout)：

```bash
# 单轮最长 30 分钟，超时自动 kill
timeout 1800 openclaw scan --all
EXIT_CODE=$?

if [ $EXIT_CODE -eq 124 ]; then
    echo "⏰ Round $ROUND timed out after 30min, skipping..."
    FAILED=$((FAILED + 1))
fi
```

`timeout` 命令返回退出码 124 表示超时终止。这样即使某轮卡死，30 分钟后会被自动杀掉，循环继续推进。这比等 350 分钟的 job 超时要合理得多。

### 失败策略选择

当前实现中，某轮失败后循环会继续跑下一轮。这对 Agent 迭代场景是合理的——Issue A 处理失败不应该阻塞 Issue B 的处理。

但在其他场景下（比如数据库迁移、有序部署），可能需要 fail-fast 策略：

```bash
if [ $EXIT_CODE -ne 0 ]; then
    echo "❌ Round $ROUND failed, aborting remaining rounds"
    break  # 立即退出循环
fi
```

两种策略可以通过一个额外的 `workflow_dispatch` 输入参数来控制，让使用者根据场景选择。

---

## 需要注意的约束：GitHub Actions 6 小时限制

GitHub 托管的 runner 对单个 job 有**最长 6 小时（360 分钟）**的硬性限制 [[4]](https://docs.github.com/en/actions/administering-github-actions/usage-limits-billing-and-administration)。超时后 job 会被强制终止。

这意味着：如果单轮平均 15 分钟，一次最多跑约 24 轮。50 轮需要分批。

几种应对方式：

### 方案一：分批手动触发

最简单。第一批跑 24 轮，完成后再手动触发第二批 26 轮。虽然要人工介入一次，但总耗时仍远低于 Cron 模式。

### 方案二：Self-hosted Runner

自己的机器做 runner，没有 6 小时限制 [[5]](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/about-self-hosted-runners)。可以一口气跑完 50 轮甚至更多。适合迭代量大、需要无人值守的场景。

### 方案三：Workflow 链式触发

一个 workflow 完成后，通过 GitHub API 触发下一个 workflow run，形成自动接力。这是突破 6 小时限制的最优雅方案，但有一个前置条件：需要 Personal Access Token（PAT）。因为 `GITHUB_TOKEN` 触发的事件不会创建新的 workflow run——这是 GitHub 为防止递归炸弹设置的安全机制 [[6]](https://docs.github.com/en/actions/security-guides/automatic-token-authentication#using-the-github_token-in-a-workflow)。

具体做法是在循环结束后，检查是否还有剩余轮次，如果有则通过 `gh` CLI 触发下一个 batch：

```bash
# 循环结束后检查是否需要接力
REMAINING=$((MAX_ROUNDS - ROUND + 1))
if [ $REMAINING -gt 0 ]; then
    echo "🔗 Triggering next batch: $REMAINING rounds remaining"
    gh workflow run agent-scan.yml \
        -f agent="$AGENT" \
        -f max_rounds="$REMAINING" \
        -f pause_seconds="$PAUSE"
fi
```

要让这段代码生效，需要两步配置：
1. 在仓库 Settings → Secrets 中添加一个 PAT（需要 `repo` 和 `actions` 权限），命名为 `PAT_TOKEN`
2. 将 job 的 `env` 中 `GITHUB_TOKEN` 替换为 `$\{\{ secrets.PAT_TOKEN }}`

这样 50 轮迭代可以自动拆成「24 轮 + 26 轮」两个 batch，中间无需人工介入。代价是多维护一个 PAT secret。

### 在 workflow 中的配置

`timeout-minutes: 350` 设置略低于 360 分钟的上限，留出缓冲：

```yaml
jobs:
  scan:
    runs-on: ubuntu-latest
    timeout-minutes: 350
```

---

## Concurrency 控制：三种触发源如何共存

改造后有三种触发源（cron、issue 事件、手动触发），可能同时发生。`concurrency` 配置确保同一时刻只有一个实例在执行 [[2]](https://docs.github.com/actions/writing-workflows/choosing-what-your-workflow-does/control-the-concurrency-of-workflows-and-jobs)：

```yaml
concurrency:
  group: agent-scan-$\{\{ github.event.inputs.agent || 'all' }}
  cancel-in-progress: false
```

- `cancel-in-progress: false`：不取消正在运行的 job，新触发的排队等待
- 按 agent 分组：不同 agent 的 scan 可以并行，同一 agent 的必须排队

实际效果：手动触发的 50 轮循环在跑的时候，cron 的每小时兜底触发会排队等待，不会干扰正在进行的迭代。

---

## 调度模式选型：什么场景该用哪种

这次改造的经验可以抽象为一个更通用的选型原则：

| 场景特征 | 适合 Cron 轮询 | 适合循环执行 |
|---------|---------------|-------------|
| 任务耗时稳定 | ✅ | ✅ |
| 任务耗时波动大 | ❌ 空等或错过 | ✅ 自适应 |
| 需要串行执行 | ⚠️ 需 concurrency 保护 | ✅ 天然串行 |
| 任务间无依赖 | ✅ | ✅ |
| 需要长时间运行 | ✅ 每轮独立 | ⚠️ 受 6h 限制 |
| 需要精确控制轮数 | ❌ | ✅ 参数化 |
| 无人值守 | ✅ | ⚠️ 需兜底机制 |

对于 AI Agent 的自动迭代这种场景——单轮耗时从 2 分钟到 40 分钟不等、必须串行、需要精确控制轮数——循环执行明显是更合适的模型。

踩过这个坑的人都知道，调度策略的选择对总耗时的影响远比优化单轮执行时间来得大。把每轮空等的 12 分钟省下来，44 轮就是 528 分钟——将近 9 个小时。任何单轮优化都很难达到这个量级。

---

## 总结与延伸

这次改造的核心思路只有一句话：**把外部时钟驱动换成进程内完成驱动**。

技术上的改动量很小——一个 `while` 循环加几个 `workflow_dispatch` 输入参数——但效果显著：50 轮迭代从 15.5 小时压缩到 6.3 小时，时间利用率从 40% 提升到 98%。改动量和收益的比值，大概是我做过的 ROI 最高的架构调整之一。

回头看，这个问题的本质是**调度模型和任务特征的错配**。Cron 适合"定期检查、耗时稳定"的场景（比如每天凌晨跑一次数据备份），但 AI Agent 迭代是"串行依赖、耗时波动剧烈"的任务——两种截然不同的特征，需要不同的调度策略。

几个值得记住的经验：

- **调度策略的选择对总耗时的影响，往往大于对单轮执行的优化**。528 分钟的空等时间，靠优化 scan 逻辑是省不出来的
- **Shell 的同步阻塞是一个被低估的协调机制**。不需要消息队列、不需要回调、不需要轮询状态——命令返回就是信号
- **效率和隔离性是一对 tradeoff**。循环模型快，但丢了轮次隔离；Cron 模型慢，但每轮干净。根据场景选择，不存在银弹
- **兜底机制不可省**。低频 Cron + 单轮 `timeout` + `concurrency` 控制，三层保险确保系统不会因为一个意外就完全停摆

后续还可以探索的方向：
- **智能退出**：在循环中检测"连续 N 轮无新 Issue"后自动停止，避免空跑浪费 Actions 分钟数
- **进度通知**：每轮结束后通过 Webhook 推送状态到飞书 / 钉钉，不用一直盯着 Actions 页面
- **自动接力**：结合 PAT + `gh workflow run` 实现跨 6 小时的 batch 自动衔接
- **指标采集**：将每轮的耗时、成功率、LLM token 消耗写入 Job Summary 或外部监控系统，积累数据用于后续优化

---

## 参考来源

| 编号 | 来源 | 说明 |
|------|------|------|
| 1 | [GitHub Docs - Events that trigger workflows: schedule](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule) | Cron 调度的触发机制和精度说明 |
| 2 | [GitHub Docs - Control the concurrency of workflows and jobs](https://docs.github.com/actions/writing-workflows/choosing-what-your-workflow-does/control-the-concurrency-of-workflows-and-jobs) | Concurrency group 配置详解 |
| 3 | [GitHub Docs - Events: workflow_dispatch](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_dispatch) | 手动触发和参数化输入的用法 |
| 4 | [GitHub Docs - Usage limits, billing, and administration](https://docs.github.com/en/actions/administering-github-actions/usage-limits-billing-and-administration) | GitHub Actions 用量限制，包括 6 小时 job 上限 |
| 5 | [GitHub Docs - About self-hosted runners](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/about-self-hosted-runners) | Self-hosted runner 的能力和限制差异 |
| 6 | [GitHub Docs - Automatic token authentication](https://docs.github.com/en/actions/security-guides/automatic-token-authentication#using-the-github_token-in-a-workflow) | GITHUB_TOKEN 的权限限制和防递归机制 |
| 7 | [Graphite - GitHub Actions timeouts](https://graphite.com/guides/github-actions-timeouts) | 超时原因分析和应对方案 |
| 8 | [Design Gurus - Event-Driven vs. Polling Architecture](https://www.designgurus.io/course-play/grokking-system-design-fundamentals/doc/eventdriven-vs-polling-architecture) | 轮询与事件驱动架构的系统性对比 |
| 9 | [GitHub Docs - Workflow commands: Adding a job summary](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#adding-a-job-summary) | Job Summary 功能，用于在 Actions 页面输出结构化摘要 |
| 10 | [Baeldung - Kill a Child Process After a Given Timeout in Bash](https://www.baeldung.com/linux/bash-kill-child-process-after-timeout) | Bash timeout 命令用法，用于单轮超时保护 |
