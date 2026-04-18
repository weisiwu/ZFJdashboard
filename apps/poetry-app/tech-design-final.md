# 诗词翻译 App 技术方案

> 版本：v1.0 | 日期：2026-02-27 | 架构师：Arch-Bot

---

## 1. 项目概述

| 项目 | 诗词翻译 App |
|------|--------------|
| 平台 | Android + iOS |
| 核心功能 | 中阿对照诗词阅读、离线使用 |
| 目标用户 | 诗词爱好者、中阿语言学习者 |
| 阶段 | MVP（最小可行产品） |

---

## 2. 技术选型

### 2.1 推荐技术栈

| 类别 | 推荐方案 | 理由 |
|------|----------|------|
| **框架** | **React Native + Expo** | 快速开发、轻量级、适合MVP |
| **语言** | TypeScript | 类型安全、团队协作友好 |
| **状态管理** | Zustand | 轻量、简单、适合中小型项目 |
| **本地存储** | AsyncStorage + JSON Bundle | 离线数据预置 |
| **导航** | React Navigation | 社区成熟、文档完善 |
| **UI组件** | React Native Paper | Material Design 3 组件库 |
| **后端/数据** | Supabase（未来扩展） | 轻量级BaaS、易于集成 |

### 2.2 为什么不选 Flutter？

- Flutter 包体积较大（首次安装约 25MB+）
- 轻量级 MVP 场景下，Expo 开发效率更高
- React Native 团队现有技能可能更匹配

---

## 3. 架构设计

### 3.1 目录结构

```
poetry-app/
├── src/
│   ├── components/          # 可复用组件
│   │   ├── PoetryCard.tsx
│   │   ├── SearchBar.tsx
│   │   └── CategoryFilter.tsx
│   ├── screens/             # 页面
│   │   ├── HomeScreen.tsx
│   │   ├── PoemDetailScreen.tsx
│   │   ├── SearchScreen.tsx
│   │   └── CategoryScreen.tsx
│   ├── navigation/          # 导航配置
│   │   └── AppNavigator.tsx
│   ├── store/               # 状态管理
│   │   └── usePoetryStore.ts
│   ├── data/                # 本地数据
│   │   └── poems.json       # 101首诗词
│   ├── services/            # API服务（未来扩展）
│   │   └── supabase.ts
│   ├── hooks/               # 自定义Hooks
│   │   └── usePoems.ts
│   ├── types/               # TypeScript类型
│   │   └── index.ts
│   └── utils/               # 工具函数
│       └── helpers.ts
├── assets/                  # 静态资源
│   └── fonts/               # 字体文件
├── App.tsx                  # 入口文件
└── app.json                 # Expo配置
```

### 3.2 模块划分

| 模块 | 职责 | 边界 |
|------|------|------|
| **Presentation** | UI渲染、交互响应 | screens/, components/ |
| **Business Logic** | 业务逻辑、状态管理 | store/, hooks/ |
| **Data** | 数据获取、存储 | data/, services/ |
| **Navigation** | 路由管理 | navigation/ |

### 3.3 数据流

```
User Action → Screen → Hook/Store → Data Source → Store Update → UI Re-render
```

---

## 4. 数据模型设计

### 4.1 诗词数据结构

```typescript
interface Poem {
  id: string;
  title: string;           // 中文标题
  titleArabic: string;    // 阿拉伯语标题
  author: string;         // 作者
  content: string;        // 中文正文
  contentArabic: string;  // 阿拉伯语译文
  category: string;       // 分类（唐诗/宋词/等）
  dynasty: string;        // 朝代
  tags: string[];        // 标签
}
```

### 4.2 分类数据结构

```typescript
interface Category {
  id: string;
  name: string;           // 分类名称
  nameArabic: string;    // 阿拉伯语名称
  poemCount: number;      // 诗词数量
}
```

---

## 5. API 对接方案

### 5.1 当前阶段（MVP）

- **数据存储**：本地 JSON 文件（poems.json）
- **数据加载**：App 启动时 bundle 加载到内存
- **无需网络**：完全离线可用

### 5.2 未来扩展（Supabase）

当需要用户数据同步、更多诗词内容时：

```typescript
// supabase.ts
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  'YOUR_SUPABASE_URL',
  'YOUR_SUPABASE_ANON_KEY'
);

// 示例：获取诗词列表
const fetchPoems = async (category?: string) => {
  let query = supabase.from('poems').select('*');
  if (category) query = query.eq('category', category);
  const { data, error } = await query;
  return { data, error };
};
```

### 5.3 数据同步策略

| 场景 | 策略 |
|------|------|
| 首次安装 | 读取本地 JSON + 可选检查 Supabase 更新 |
| 日常使用 | 纯本地，无需网络 |
| 内容更新 | App Store/Play Store 更新 APK/Bundle |

---

## 6. 离线实现方案

### 6.1 本地数据预置

```typescript
// 方式一：直接 import（推荐，Expo 支持良好）
import poems from './data/poems.json';

// 方式二：运行时读取
const loadPoems = async () => {
  const response = await require('./data/poems.json');
  return response;
};
```

### 6.2 数据缓存

- **首次加载**：从 JSON 解析到内存（Zustand store）
- **搜索缓存**：搜索结果缓存到 AsyncStorage
- **用户收藏**（未来）：AsyncStorage 持久化

---

## 7. 功能清单

### MVP（第一阶段）

| 功能 | 优先级 | 状态 |
|------|--------|------|
| 诗词列表展示 | P0 | - |
| 诗词详情阅读（中阿对照） | P0 | - |
| 分类浏览 | P0 | - |
| 搜索功能 | P1 | - |
| 诗词分类筛选 | P1 | - |

### 未来版本

| 功能 | 优先级 |
|------|--------|
| 用户登录/注册 | P2 |
| 收藏功能 | P2 |
| 笔记功能 | P2 |
| 诗词下载（离线包） | P2 |
| 深色模式 | P3 |

---

## 8. 工作量评估

### 8.1 前端（React Native + Expo）

| 模块 | 功能 | 工作量 |
|------|------|--------|
| **基础设置** | 项目初始化、TypeScript配置、导航搭建 | 0.5 人天 |
| **数据层** | JSON 解析、Zustand Store、类型定义 | 0.5 人天 |
| **首页** | 诗词列表、分类标签、下拉刷新 | 1 人天 |
| **详情页** | 中阿对照展示、滚动阅读 | 0.5 人天 |
| **分类页** | 分类列表、筛选逻辑 | 0.5 人天 |
| **搜索** | 搜索框、实时搜索、结果展示 | 1 人天 |
| **UI优化** | 字体适配、样式调整、Loading状态 | 1 人天 |
| **测试修复** | Bug修复、兼容性测试 | 1 人天 |
| **总计** | | **6 人天** |

### 8.2 后端（MVP 阶段）

| 模块 | 说明 | 工作量 |
|------|------|--------|
| **本地数据** | 101首诗词 JSON 整理与校验 | 0（已有） |
| **Supabase 搭建** | （未来版本） | - |
| **API 接口** | （未来版本） | - |
| **总计** | | **0 人天** |

> 💡 MVP 阶段无后端开发需求，数据全部本地预置。

---

## 9. 风险与建议

| 风险 | 等级 | 应对措施 |
|------|------|----------|
| 阿拉伯语字体显示 | 中 | 预置 Arabic 字体，使用 `expo-font` 加载 |
| 长文本滚动性能 | 低 | 使用 `FlashList` 替代 `FlatList` |
| 中阿混合排版 | 中 | 使用 `react-native-localize` 检测系统语言 |

---

## 10. 总结

- **技术栈**：React Native + Expo + TypeScript + Zustand
- **开发周期**：约 6 人天（前端）
- **上线状态**：MVP 可快速上线，无需后端
- **扩展性**：预留 Supabase 接口，未来平滑演进

---

> 架构师：Arch-Bot 🏗️
