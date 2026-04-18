---
layout: page
---

# 🛠️ 小伍工具箱

Next.js 14 在线工具网站

[← 返回项目列表](/apps/)

---

## 核心文档

<div class="doc-grid">
<a class="doc-card" href="/apps/xiaowutools/readme">
  <div class="doc-card-title">README</div>
  <div class="doc-card-arrow">→</div>
</a>
<a class="doc-card" href="/apps/xiaowutools/spec">
  <div class="doc-card-title">SPEC</div>
  <div class="doc-card-arrow">→</div>
</a>
<a class="doc-card" href="/apps/xiaowutools/agents">
  <div class="doc-card-title">AGENTS</div>
  <div class="doc-card-arrow">→</div>
</a>

</div>


<style>
.doc-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
  margin: 16px 0 32px;
}
.doc-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 10px;
  text-decoration: none !important;
  color: inherit !important;
  transition: all 0.2s ease;
  background: var(--vp-c-bg-soft);
}
.doc-card:hover {
  border-color: var(--vp-c-brand);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.doc-card-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--vp-c-text-1);
}
.doc-card-arrow {
  color: var(--vp-c-text-3);
  font-size: 16px;
}
</style>
