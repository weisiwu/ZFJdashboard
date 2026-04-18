# TeamClaw 协作平台

> 基于 Tauri 2.x 的桌面协作平台，集成 AI Agent 编排与多模态交互。

## 基本信息

| 项目 | 内容 |
|------|------|
| **技术栈** | Tauri 2.x · React · TypeScript · Rust · Vite |
| **仓库** | [weisiwu/teamclaw](https://github.com/weisiwu/teamclaw) |
| **状态** | 🔨 15% — 骨架已完成，暂停中 |

## 架构设计

TeamClaw 采用六模块架构：

| 模块 | 说明 |
|------|------|
| 模块 1 | 项目导入与管理 |
| 模块 2 | Agent 编排与调度 |
| 模块 3 | 任务系统 |
| 模块 4 | 能力系统（Tools/扩展） |
| 模块 5 | 知识库 |
| 模块 6 | 对话生命周期管理 |

## 项目结构

```
├── src/                  # React 前端
│   ├── App.tsx
│   ├── store.ts          # 状态管理
│   └── main.tsx
├── src-tauri/            # Rust 后端
│   ├── src/
│   ├── Cargo.toml
│   └── tauri.conf.json
├── project/              # PRD 文档
│   ├── teamclaw-architecture.md
│   ├── prd-module1~6.md
│   └── 技术方案设计/
└── _legacy-nextjs/       # 旧版 Next.js 实现（已弃用）
```

## 已有 PRD 文档

完整 PRD 已编写完成，涵盖：
- 整体架构设计
- 6 个功能模块的需求文档
- 技术方案设计
- 技术栈选型说明
