# Prompt: 将 Dashboard 项目数据源从硬编码迁移到 Supabase

## 项目背景

这是一个 Next.js (App Router) 项目监控大盘，部署在 Vercel。
- 仓库：`weisiwu/ZFJdashboard`
- 项目路径：`apps/projects-dashboard`
- 技术栈：Next.js + TypeScript + Tailwind CSS

**当前问题**：所有项目数据硬编码在 `src/app/lib/analytics.ts` 的 `fetchAnalyticsData()` 函数中，是一个写死的数组，导致无论怎么迭代 UI，首页数据永远不变。

## 目标

将数据源从硬编码迁移到 **Supabase**（PostgreSQL），实现：
1. 项目数据存储在 Supabase 数据库中
2. Dashboard 首页从 Supabase 实时读取数据
3. 提供管理接口（API Routes）用于增删改查项目

## 具体要求

### 1. Supabase 数据库表设计

根据现有 `src/app/lib/types.ts` 中的 `Project` 接口创建表：

```sql
CREATE TABLE projects (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT NOT NULL,
  url TEXT DEFAULT '',
  deployed BOOLEAN DEFAULT false,
  tech TEXT NOT NULL,
  color TEXT NOT NULL,
  views INTEGER DEFAULT 0,
  last_updated TIMESTAMPTZ DEFAULT now(),
  status TEXT NOT NULL CHECK (status IN ('deployed', 'developing', 'archived')),
  category TEXT DEFAULT 'other' CHECK (category IN ('web', 'mobile', 'tool', 'ai', 'other')),
  tags TEXT[] DEFAULT '{}',
  owner TEXT DEFAULT '',
  icon TEXT DEFAULT '',
  version TEXT DEFAULT 'v0.1.0',
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 启用 RLS
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

-- 允许匿名读取
CREATE POLICY "Allow public read" ON projects FOR SELECT USING (true);

-- 仅认证用户可写入
CREATE POLICY "Allow authenticated write" ON projects FOR ALL USING (auth.role() = 'authenticated');
```

同时创建 `activities` 表：

```sql
CREATE TABLE activities (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  type TEXT NOT NULL CHECK (type IN ('deploy', 'update', 'create', 'archive')),
  project TEXT NOT NULL,
  description TEXT NOT NULL,
  timestamp TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE activities ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public read" ON activities FOR SELECT USING (true);
```

### 2. 种子数据

将 `analytics.ts` 中现有的 5 个硬编码项目作为种子数据插入 `projects` 表。

### 3. Supabase 客户端配置

- 安装 `@supabase/supabase-js`
- 创建 `src/lib/supabase.ts`，导出 server 端和 client 端的 Supabase client
- 环境变量添加到 `.env.local`：
  ```
  NEXT_PUBLIC_SUPABASE_URL=your-url
  NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
  SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
  ```

### 4. 改造 `src/app/lib/analytics.ts`

- **删除**硬编码的项目数组
- **改为**从 Supabase `projects` 表查询数据
- 保持函数签名 `fetchAnalyticsData(): Promise<{ projects: Project[]; stats: Stats }>` 不变
- 注意字段映射：数据库用 `snake_case`（如 `last_updated`），TypeScript 用 `camelCase`（如 `lastUpdated`）
- 添加错误处理和 fallback（查询失败时返回空数组而非崩溃）

### 5. 创建 API Routes

在 `src/app/api/projects/` 下创建：

- `GET /api/projects` — 获取所有项目（支持 `?status=deployed&category=web` 筛选）
- `POST /api/projects` — 创建项目（需要 `API_KEY` 认证）
- `PUT /api/projects/[id]` — 更新项目（需要 `API_KEY` 认证）
- `DELETE /api/projects/[id]` — 删除项目（需要 `API_KEY` 认证）

认证方式：请求头 `Authorization: Bearer <API_KEY>`，其中 `API_KEY` 从环境变量 `.env.local` 中的 `API_KEY` 读取。

### 6. 不要破坏的东西

- `src/app/page.tsx` 的结构不需要改，它调用 `fetchAnalyticsData()` 获取数据传给 `ClientDashboard`，这个调用链保持不变
- `src/app/lib/types.ts` 中的接口定义保持不变
- 所有现有的 UI 组件不需要修改
- ISR revalidate 策略保留（`export const revalidate = 300`）

### 7. 更新 `.env.local.example`

添加 Supabase 相关的环境变量示例。

## 文件改动清单

| 操作 | 文件 |
|------|------|
| 新建 | `src/lib/supabase.ts` |
| 改造 | `src/app/lib/analytics.ts` |
| 新建 | `src/app/api/projects/route.ts` |
| 新建 | `src/app/api/projects/[id]/route.ts` |
| 更新 | `.env.local.example` |
| 更新 | `package.json`（添加 `@supabase/supabase-js` 依赖） |
| 新建 | `supabase/seed.sql`（种子数据，方便初始化） |

## 验证步骤

1. 在 Supabase 控制台创建表并插入种子数据
2. 配置 `.env.local` 的 Supabase 凭据
3. `npm run dev` 启动后首页应显示从数据库读取的项目列表
4. 通过 API 添加一个新项目，刷新页面后应立即出现
5. 通过 API 修改项目状态，刷新页面后数据应更新
