---
layout: page
---

# 学习笔记

个人技术学习文章与实战笔记汇总。点击标题查看完整内容。

## 🤖 Agent 框架

<div class="note-grid">

<a class="note-card" href="/notes/learning/acp">
  <div class="note-card-title">ACP 协议定义与 OpenClaw 用法</div>
  <div class="note-card-desc">深入解析 ACP（Agent Communication Protocol）的协议规范，以及在 OpenClaw 中的两种实际应用方式。</div>
  <div class="note-card-tag">Agent 协议</div>
</a>

<a class="note-card" href="/notes/learning/openclaw-subagent">
  <div class="note-card-title">OpenClaw Subagent 并发任务</div>
  <div class="note-card-desc">探讨 OpenClaw 的子代理架构设计，以及如何实现并发任务编排。</div>
  <div class="note-card-tag">Agent 框架</div>
</a>

<a class="note-card" href="/notes/learning/openclaw-events-hooks">
  <div class="note-card-title">OpenClaw 事件与钩子体系</div>
  <div class="note-card-desc">OpenClaw 的事件驱动架构和钩子扩展机制的设计原理与使用方法。</div>
  <div class="note-card-tag">Agent 框架</div>
</a>

<a class="note-card" href="/notes/learning/openclaw-tools">
  <div class="note-card-title">OpenClaw 能力地图与 Tools</div>
  <div class="note-card-desc">全面梳理 OpenClaw 支持的工具类型和扩展能力。</div>
  <div class="note-card-tag">Agent 框架</div>
</a>

<a class="note-card" href="/notes/learning/openclaw-cli">
  <div class="note-card-title">OpenClaw CLI 强化 Agent</div>
  <div class="note-card-desc">利用 CLI 工具增强 Agent 能力，实现自动化工作流与自我进化。</div>
  <div class="note-card-tag">Agent 工具</div>
</a>

</div>

## 🎨 AI 应用设计

<div class="note-grid">

<a class="note-card" href="/notes/learning/ai-app-design">
  <div class="note-card-title">AI 生成 APP 设计稿最佳实践</div>
  <div class="note-card-desc">使用 AI 工具生成高质量应用设计稿的方法论和实践经验。</div>
  <div class="note-card-tag">AI 应用</div>
</a>

<a class="note-card" href="/notes/learning/claude-code-arch">
  <div class="note-card-title">Claude Code 源码架构观察</div>
  <div class="note-card-desc">从 Claude Code 源码中提取的三个值得学习的架构设计模式。</div>
  <div class="note-card-tag">AI 代码工具</div>
</a>

</div>

## 📚 RAG 与知识库

<div class="note-grid">

<a class="note-card" href="/notes/learning/dify-knowledge-base">
  <div class="note-card-title">Dify 知识库构建指南</div>
  <div class="note-card-desc">Dify 平台上构建高质量知识库的完整流程。</div>
  <div class="note-card-tag">RAG 平台</div>
</a>

<a class="note-card" href="/notes/learning/maxkb-knowledge-base">
  <div class="note-card-title">MaxKB 知识库构建指南</div>
  <div class="note-card-desc">MaxKB 平台的知识库构建方法与最佳实践。</div>
  <div class="note-card-tag">RAG 平台</div>
</a>

<a class="note-card" href="/notes/learning/ragflow-knowledge-base">
  <div class="note-card-title">RAGFlow 知识库构建指南</div>
  <div class="note-card-desc">RAGFlow 引擎的深度使用指南。</div>
  <div class="note-card-tag">RAG 平台</div>
</a>

<a class="note-card" href="/notes/learning/raptor">
  <div class="note-card-title">RAPTOR 递归摘要检索指南</div>
  <div class="note-card-desc">RAPTOR 递归摘要树检索技术的原理与实践。</div>
  <div class="note-card-tag">检索增强</div>
</a>

</div>

## 🔧 其他技术

<div class="note-grid">

<a class="note-card" href="/notes/learning/token-gateway">
  <div class="note-card-title">Token 中转站深度解析</div>
  <div class="note-card-desc">分析 Token 中转服务的运作机制、市场需求和风险。</div>
  <div class="note-card-tag">AI 基础设施</div>
</a>

<a class="note-card" href="/notes/learning/markdown-knowledge-base">
  <div class="note-card-title">个人 Markdown 知识库方案</div>
  <div class="note-card-desc">基于 Markdown 的个人知识管理系统设计方案。</div>
  <div class="note-card-tag">工具链</div>
</a>

</div>

## ⚡ 实战笔记

<div class="note-grid">

<a class="note-card" href="/notes/practice/actions-loop">
  <div class="note-card-title">GitHub Actions 调度架构改造</div>
  <div class="note-card-desc">从简单的轮询模式改造为循环模式的架构演进过程。</div>
  <div class="note-card-tag">CI/CD</div>
</a>

<a class="note-card" href="/notes/practice/agent-timeout">
  <div class="note-card-title">Agent 超时排查与 Cron 机制</div>
  <div class="note-card-desc">排查 Agent 超时无响应问题的完整过程，以及 Cron 调度机制的深入分析。</div>
  <div class="note-card-tag">排障</div>
</a>

<a class="note-card" href="/notes/practice/issue-idempotent">
  <div class="note-card-title">Issue 残留与幂等性设计</div>
  <div class="note-card-desc">自动迭代流程中 Issue 残留问题分析与幂等性解决方案。</div>
  <div class="note-card-tag">幂等性</div>
</a>

</div>

<style>
.note-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
  margin: 16px 0 32px;
}
.note-card {
  display: block;
  padding: 20px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 12px;
  text-decoration: none !important;
  color: inherit !important;
  transition: all 0.25s ease;
  background: var(--vp-c-bg-soft);
}
.note-card:hover {
  border-color: var(--vp-c-brand);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}
.note-card-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--vp-c-text-1);
}
.note-card-desc {
  font-size: 13px;
  color: var(--vp-c-text-2);
  line-height: 1.6;
  margin-bottom: 12px;
}
.note-card-tag {
  display: inline-block;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--vp-c-brand-dimm);
  color: var(--vp-c-brand);
  font-weight: 500;
}
</style>
