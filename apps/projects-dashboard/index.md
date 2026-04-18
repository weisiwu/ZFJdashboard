---
layout: page
---

# 📊 项目仪表盘

Next.js 16 项目管理仪表盘

[← 返回项目列表](/apps/)

---

## 核心文档

<div class="doc-grid">
<a class="doc-card" href="/apps/projects-dashboard/readme">
  <div class="doc-card-title">README</div>
  <div class="doc-card-arrow">→</div>
</a>
<a class="doc-card" href="/apps/projects-dashboard/prompt_supabase_migration">
  <div class="doc-card-title">PROMPT_SUPABASE_MIGRATION</div>
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
