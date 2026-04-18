# Sprint 69 任务拆解 - 变更追踪（版本关联消息截图 + 变更摘要）

> 基于 `project/docs/prd/iter69-change-tracking.md`

---

## [TASK-6901] 后端：截图关联 API 实现
- **负责角色**：coder
- **依赖**：无
- **验收标准**：
  - [ ] `POST /api/v1/versions/:id/screenshots` 接收 `{ messageId, messageContent, senderName, screenshotUrl, thumbnailUrl }`，写入存储
  - [ ] `GET /api/v1/versions/:id/screenshots` 返回截图列表
  - [ ] `DELETE /api/v1/versions/:id/screenshots/:screenshotId` 删除记录
- **状态**：待开始

---

## [TASK-6902] 后端：变更摘要 API 实现
- **负责角色**：coder
- **依赖**：无
- **验收标准**：
  - [ ] `POST /api/v1/versions/:id/changelog/generate` 接收 `changedFiles[]`，调用 AI，保存 `VersionChangelog`
  - [ ] `GET /api/v1/versions/:id/changelog` 返回 changelog
  - [ ] `PUT /api/v1/versions/:id/changelog` 保存手动编辑内容
- **状态**：待开始

---

## [TASK-6903] 后端：版本时间线 API
- **负责角色**：coder
- **依赖**：TASK-6901, TASK-6902
- **验收标准**：
  - [ ] `GET /api/v1/versions/:id/timeline` 返回合并截图关联 + changelog 生成 events 的时间线
- **状态**：待开始

---

## [TASK-6904] 前端：MessageSelector 消息选择器组件
- **负责角色**：coder
- **依赖**：后端飞书消息 API 就绪（可先用 mock）
- **验收标准**：
  - [ ] Dialog 形式，支持搜索消息内容
  - [ ] 消息列表支持翻页（每页 20 条）
  - [ ] 点击消息触发 `onSelect(message)` 回调
- **状态**：待开始

---

## [TASK-6905] 前端：ScreenshotGallery 截图画廊组件
- **负责角色**：coder
- **依赖**：TASK-6901
- **验收标准**：
  - [ ] 缩略图网格展示（3-4 列）
  - [ ] 点击放大 Modal，支持左右翻页
  - [ ] 每张卡片显示发送者 + 时间，右上角"解绑"按钮
- **状态**：待开始

---

## [TASK-6906] 前端：ChangelogPanel 变更摘要面板
- **负责角色**：coder
- **依赖**：TASK-6902
- **验收标准**：
  - [ ] 展示 AI 生成的分类摘要（features/changes/fixes/breaking）
  - [ ] "重新生成"按钮覆盖旧摘要
  - [ ] "编辑"按钮切换 Markdown 编辑模式
  - [ ] "保存"按钮持久化到后端
- **状态**：待开始

---

## [TASK-6907] 前端：VersionTimeline 版本变更时间线
- **负责角色**：coder
- **依赖**：TASK-6903
- **验收标准**：
  - [ ] Dialog 形式，展示垂直时间线
  - [ ] 每条 event 有 icon + 时间 + 描述
  - [ ] events 按时间倒序
- **状态**：待开始

---

## [TASK-6908] 前端：版本详情 Dialog 集成 + 筛选增强
- **负责角色**：coder
- **依赖**：TASK-6904, TASK-6905, TASK-6906, TASK-6907
- **验收标准**：
  - [ ] 版本详情 Dialog 的 Tab 栏整合 ScreenshotGallery、ChangelogPanel、VersionTimeline
  - [ ] Tag 面板增加"有截图"/"有摘要"筛选器
  - [ ] 截图关联入口（"关联截图"按钮）触发 MessageSelector
- **状态**：待开始

---

## [TASK-6909] 数据模型：数据库表设计（如使用真实 DB）
- **负责角色**：architect
- **依赖**：无
- **验收标准**：
  - [ ] `version_screenshots` 表：`id, version_id, message_id, message_content, sender_name, sender_avatar, screenshot_url, thumbnail_url, created_at`
  - [ ] `version_changelogs` 表：`id, version_id, title, content, changes(JSON), generated_at, generated_by`
  - [ ] 提供迁移 SQL 或 ORM 映射
- **状态**：待开始
