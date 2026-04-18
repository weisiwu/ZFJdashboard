---
layout: page
---

# 📦 应用项目

致富经旗下所有应用项目的文档中心。

<div class="app-grid">
<a class="app-card" href="/apps/marker-tracker/">
  <div class="app-card-icon">🎯</div>
  <div class="app-card-info">
    <div class="app-card-name">Marker Tracker</div>
    <div class="app-card-desc">X 光造影序列双 Marker 自动跟踪与距离测量工具</div>
    <div class="app-card-count">5 篇文档</div>
  </div>
  <div class="app-card-arrow">→</div>
</a>
<a class="app-card" href="/apps/xiaowutools/">
  <div class="app-card-icon">🛠️</div>
  <div class="app-card-info">
    <div class="app-card-name">小伍工具箱</div>
    <div class="app-card-desc">Next.js 14 在线工具网站</div>
    <div class="app-card-count">3 篇文档</div>
  </div>
  <div class="app-card-arrow">→</div>
</a>
<a class="app-card" href="/apps/teamclaw/">
  <div class="app-card-icon">🤝</div>
  <div class="app-card-info">
    <div class="app-card-name">TeamClaw</div>
    <div class="app-card-desc">Tauri 2.x 桌面应用 + 全栈协作平台</div>
    <div class="app-card-count">17 篇文档</div>
  </div>
  <div class="app-card-arrow">→</div>
</a>
<a class="app-card" href="/apps/projects-dashboard/">
  <div class="app-card-icon">📊</div>
  <div class="app-card-info">
    <div class="app-card-name">项目仪表盘</div>
    <div class="app-card-desc">Next.js 16 项目管理仪表盘</div>
    <div class="app-card-count">2 篇文档</div>
  </div>
  <div class="app-card-arrow">→</div>
</a>
<a class="app-card" href="/apps/poetry-app/">
  <div class="app-card-icon">📜</div>
  <div class="app-card-info">
    <div class="app-card-name">诗词应用</div>
    <div class="app-card-desc">Expo 跨平台古诗词移动应用</div>
    <div class="app-card-count">17 篇文档</div>
  </div>
  <div class="app-card-arrow">→</div>
</a>

</div>

<style>
.app-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  margin: 24px 0;
}
.app-card {
  display: flex;
  align-items: center;
  padding: 20px 24px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 14px;
  text-decoration: none !important;
  color: inherit !important;
  transition: all 0.25s ease;
  background: var(--vp-c-bg-soft);
  gap: 16px;
}
.app-card:hover {
  border-color: var(--vp-c-brand);
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.08);
}
.app-card-icon {
  font-size: 32px;
  flex-shrink: 0;
}
.app-card-info {
  flex: 1;
  min-width: 0;
}
.app-card-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--vp-c-text-1);
  margin-bottom: 4px;
}
.app-card-desc {
  font-size: 13px;
  color: var(--vp-c-text-2);
  margin-bottom: 6px;
}
.app-card-count {
  font-size: 12px;
  color: var(--vp-c-text-3);
}
.app-card-arrow {
  color: var(--vp-c-text-3);
  font-size: 20px;
  flex-shrink: 0;
}
</style>
