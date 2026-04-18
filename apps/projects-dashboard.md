# 项目仪表盘 dashboard

> 项目管理仪表盘，支持 Google OAuth 和 Magic Link 登录。

## 基本信息

| 项目 | 内容 |
|------|------|
| **技术栈** | Next.js 16 · TypeScript |
| **仓库** | [weisiwu/ZFJdashboard](https://github.com/weisiwu/ZFJdashboard) |
| **域名** | `dashboard.baoganai.com` |
| **状态** | ⚠️ 70% — Auth 有阻塞项 |

## 已完成

- ✅ 已部署到 Vercel
- ✅ 登录页：Google OAuth + Magic Link 双模式
- ✅ 邮箱白名单（`siwu.wsw@gmail.com`）

## 阻塞项

| 问题 | 说明 |
|------|------|
| ⚠️ Google OAuth | 需 Google Console 添加 Test User + redirect URI |
| ⚠️ Magic Link | Vercel 缺 Supabase 环境变量（URL/ANON_KEY/SERVICE_ROLE_KEY） |

## 环境变量

当前 Vercel 仅配置了 `GOOGLE_CLIENT_ID` 和 `GOOGLE_CLIENT_SECRET`，缺少 Supabase 相关变量。
