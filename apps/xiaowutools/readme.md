# 小工具箱 (xiaowutools-v2)

使用 Next.js + React + Tailwind CSS 重构的工具箱网站。

## 功能

1. **抖音/TikTok 下载器** - 一键提取无水印视频
2. **图片转 ICO** - 在线转换图片格式
3. **微信截图生成** - 自定义对话内容

## 技术栈

- Next.js 14
- React 18
- TypeScript
- Tailwind CSS
- shadcn/ui 组件风格
- Sharp (图片处理)

## 快速开始

```bash
# 安装依赖
npm install

# 开发模式
npm run dev

# 生产构建
npm run build

# 代码规范检查（ESLint）
npm run lint
```

## 项目结构

```
├── app/
│   ├── api/              # API 路由
│   │   ├── douyin/       # 抖音解析 API
│   │   └── ico/         # ICO 转换 API
│   ├── tools/            # 工具页面
│   │   ├── douyin/      # 抖音下载页
│   │   ├── ico/         # 图片转ICO页
│   │   └── wechat/      # 微信截图页
│   ├── page.tsx         # 首页
│   └── layout.tsx       # 布局
├── components/           # 组件
│   ├── Header.tsx
│   ├── Footer.tsx
│   └── ToolsGrid.tsx
└── public/              # 静态资源
```

## 环境变量

无特殊环境变量要求。

## 注意事项

- 抖音/TikTok 解析依赖 Puppeteer，需要安装 Chromium
- 图片转换需要 sharp 库

## License

MIT
