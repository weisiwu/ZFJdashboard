# 小工具箱 xiaowutools

> 在线工具箱网站，提供多种实用工具。

## 基本信息

| 项目 | 内容 |
|------|------|
| **技术栈** | Next.js 14 · React 18 · TypeScript · Tailwind CSS · shadcn/ui |
| **仓库** | [weisiwu/zhifujing-tools](https://github.com/weisiwu/zhifujing-tools) |
| **状态** | ✅ 90% — 已部署运行 |

## 核心功能

1. **抖音/TikTok 下载器** — 一键提取无水印视频
2. **图片转 ICO** — 在线转换图片格式
3. **微信截图生成** — 自定义对话内容
4. 多语言支持（中/英）
5. 工具使用记录、最近使用
6. SEO 优化（sitemap、robots.txt）

## 项目结构

```
├── app/
│   ├── api/              # API 路由（抖音解析、ICO 转换等）
│   ├── tools/            # 各工具页面
│   ├── page.tsx          # 首页
│   └── layout.tsx        # 布局
├── components/           # 公共组件
│   ├── Header.tsx
│   ├── Footer.tsx
│   ├── ToolsGrid.tsx
│   └── ...
├── scripts/              # 构建/升级脚本
└── public/               # 静态资源
```

## 特色

- 响应式设计，移动端友好
- 支持 Google AdSense 广告
- 自动构建版本号管理
- Launchd 定时自动升级脚本
