# 诗词数据说明文档

## 一、数据来源

### 原始数据
- **来源**: [chinese-poetry/chinese-poetry](https://github.com/chinese-poetry/chinese-poetry)
- **许可证**: MIT License
- **下载时间**: 2026-03-31
- **仓库大小**: 约 50MB

### 数据内容
包含中国古代诗词文献，涵盖：
- 全唐诗 (58 个 JSON 文件)
- 宋词 (23 个 JSON 文件)
- 元曲 (多个 JSON 文件)
- 五代诗词
- 四书五经
- 楚辞
- 论语等

---

## 二、本地数据库

### 2.1 数据库文件

本地使用 SQLite 数据库存储所有数据：

```
apps/poetry-app/data/poetry.db    # SQLite 数据库文件
```

### 2.2 数据库管理工具

使用 `scripts/local-db.ts` 管理本地数据库：

```bash
# 查看帮助
npx tsx scripts/local-db.ts

# 创建表结构
npx tsx scripts/local-db.ts create

# 导入所有数据
npx tsx scripts/local-db.ts import

# 查看数据统计
npx tsx scripts/local-db.ts stats

# 查看朝代列表
npx tsx scripts/local-db.ts dynasties

# 查看诗人列表 (默认 10 条)
npx tsx scripts/local-db.ts poets 20

# 查看诗词列表 (默认 5 首)
npx tsx scripts/local-db.ts poems 10

# 搜索诗词
npx tsx scripts/local-db.ts search 李白 10
npx tsx scripts/local-db.ts search 静夜思

# 导出数据到 JSON
npx tsx scripts/local-db.ts export

# 清空所有数据
npx tsx scripts/local-db.ts clear

# 删除所有表
npx tsx scripts/local-db.ts drop
```

### 2.3 使用 GUI 工具查看

推荐使用以下工具查看本地 SQLite 数据库：

| 工具 | 平台 | 说明 |
|------|------|------|
| [DB Browser for SQLite](https://sqlitebrowser.org/) | macOS/Windows/Linux | 免费 GUI 工具 |
| [TablePlus](https://tableplus.com/) | macOS/Windows | 现代化数据库管理 |
| [DataGrip](https://www.jetbrains.com/datagrip/) | macOS/Windows/Linux | JetBrains IDE |
| VS Code 插件 | VS Code | SQLite Viewer 插件 |

**使用 GUI 工具步骤**：
1. 打开工具，选择 "Open Database"
2. 选择文件：`apps/poetry-app/data/poetry.db`
3. 浏览表结构和数据

### 2.4 使用命令行查看

```bash
# 安装 sqlite3 命令行工具 (macOS 已预装)
# Ubuntu: sudo apt install sqlite3

# 打开数据库
sqlite3 apps/poetry-app/data/poetry.db

# 常用 SQL 命令
.tables                    # 查看所有表
.schema poems              # 查看 poems 表结构
SELECT COUNT(*) FROM poems;  # 统计诗词数量
SELECT * FROM dynasties;   # 查看朝代
.quit                      # 退出
```

---

## 三、本地文件结构

```
apps/poetry-app/data/
├── raw/                          # 原始数据 (从 GitHub 下载)
│   └── chinese-poetry/
│       ├── 全唐诗/
│       │   ├── poet.tang.0.json  # 唐诗数据文件
│       │   ├── poet.tang.1000.json
│       │   ├── ...
│       │   ├── authors.tang.json # 唐代作者信息
│       │   └── authors.song.json # 宋代作者信息
│       ├── 宋词/
│       │   ├── ci.song.0.json    # 宋词数据文件
│       │   ├── ci.song.1000.json
│       │   └── ...
│       ├── 元曲/
│       ├── 五代诗词/
│       └── ...
│
└── processed/                    # 处理后的数据
    ├── dynasties.json            # 朝代数据 (8 条)
    ├── poets.json                # 诗人数据 (5,376 条)
    ├── poems.json                # 诗词数据 (89,717 条)
    ├── 01_dynasties.sql          # 朝代 SQL 插入语句
    ├── 02_poets_*.sql            # 诗人 SQL 插入语句 (6 个文件)
    └── 03_poems_*.sql            # 诗词 SQL 插入语句 (90 个文件)
```

---

## 三、数据统计

### 总体统计

| 数据类型 | 数量 |
|----------|------|
| 朝代 | 8 个 |
| 诗人 | 5,376 位 |
| 诗词 | 89,717 首 |

### 按朝代分布

| 朝代 | 诗词数量 | 时间范围 |
|------|----------|----------|
| 唐 | 57,607 首 | 618-907 年 |
| 宋 | 21,053 首 | 960-1279 年 |
| 元 | 11,057 首 | 1271-1368 年 |

### 文件大小

| 文件 | 大小 |
|------|------|
| 原始数据 (raw/) | ~50 MB |
| 处理后 JSON | ~80 MB |
| SQL 文件 | ~150 MB |

---

## 四、数据结构

### 4.1 原始数据格式

#### 诗词文件 (poet.tang.*.json / ci.song.*.json)

```json
[
  {
    "id": "3ad6d468-7ff1-4a7b-8b24-a27d70d00ed4",
    "title": "帝京篇十首 一",
    "author": "太宗皇帝",
    "paragraphs": [
      "秦川雄帝宅，函谷壯皇居。",
      "綺殿千尋起，離宮百雉餘。",
      "連甍遙接漢，飛觀迥凌虛。",
      "雲日隱層闕，風煙出綺疎。"
    ],
    "strains": ["...", "..."]  // 平仄信息 (可选)
  }
]
```

#### 作者文件 (authors.*.json)

```json
[
  {
    "id": "f78aa699-e012-4059-9e29-5d30e16cc1d8",
    "name": "太宗皇帝",
    "desc": "帝姓李氏，諱世民，神堯次子，聰明英武..."
  }
]
```

### 4.2 处理后数据格式

#### dynasties.json

```json
[
  {
    "id": 1,
    "name": "唐",
    "name_ar": "العصر التانغ",
    "start_year": 618,
    "end_year": 907
  }
]
```

#### poets.json

```json
[
  {
    "id": 1,
    "name": "太宗皇帝",
    "name_ar": "",
    "dynasty": "唐",
    "dynasty_id": 1,
    "bio": "帝姓李氏，諱世民...",
    "bio_ar": ""
  }
]
```

#### poems.json

```json
[
  {
    "id": "3ad6d468-7ff1-4a7b-8b24-a27d70d00ed4",
    "title": "帝京篇十首 一",
    "title_ar": "",
    "author": "太宗皇帝",
    "poet_id": 1,
    "dynasty": "唐",
    "dynasty_id": 1,
    "content": [
      "秦川雄帝宅，函谷壯皇居。",
      "綺殿千尋起，離宮百雉餘。"
    ],
    "content_ar": [],
    "word_count": 32,
    "is_translated": false
  }
]
```

---

## 五、数据库表结构

### 5.1 朝代表 (dynasties)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL | 主键 |
| name | VARCHAR(50) | 朝代名称 (唐/宋/元等) |
| name_ar | VARCHAR(100) | 阿拉伯语名称 |
| start_year | INT | 开始年份 |
| end_year | INT | 结束年份 |
| description | TEXT | 描述 |
| description_ar | TEXT | 阿拉伯语描述 |

### 5.2 诗人表 (poets)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL | 主键 |
| name | VARCHAR(100) | 诗人姓名 |
| name_ar | VARCHAR(200) | 阿拉伯语姓名 |
| dynasty_id | INT | 所属朝代 ID |
| birth_year | INT | 出生年份 |
| death_year | INT | 逝世年份 |
| bio | TEXT | 生平简介 |
| bio_ar | TEXT | 阿拉伯语简介 |
| style | VARCHAR(200) | 诗歌风格 |

### 5.3 诗词表 (poems)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(50) | 主键 (UUID) |
| title | VARCHAR(200) | 中文标题 |
| title_ar | VARCHAR(400) | 阿拉伯语标题 |
| author | VARCHAR(100) | 作者姓名 |
| poet_id | INT | 诗人 ID |
| dynasty | VARCHAR(50) | 朝代名称 |
| dynasty_id | INT | 朝代 ID |
| content | TEXT[] | 中文内容 (按行) |
| content_ar | TEXT[] | 阿拉伯语翻译 |
| cultural_context_ar | TEXT | 文化背景 |
| word_count | INT | 字数 |
| is_translated | BOOLEAN | 是否已翻译 |

---

## 六、数据处理流程

### 6.1 数据转换脚本

位置: `scripts/transform-poetry.ts`

```bash
# 运行转换脚本
npx tsx scripts/transform-poetry.ts
```

### 6.2 处理流程图

```
原始 JSON 文件
     │
     ▼
┌─────────────────┐
│  读取诗词数据   │
│  读取作者数据   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  数据清洗转换   │
│  - 去重         │
│  - 格式化       │
│  - 关联关系     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  输出 JSON      │
│  输出 SQL       │
└─────────────────┘
```

---

## 七、导入 Supabase

### 7.1 前置条件

1. Supabase 项目已创建
2. 环境变量已配置 (`.env.local`):
   ```
   EXPO_PUBLIC_SUPABASE_URL=your-project-url
   EXPO_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
   ```

### 7.2 导入步骤

#### 方法一：SQL Editor (推荐小批量)

1. 打开 Supabase Dashboard
2. 进入 SQL Editor
3. 依次执行:
   - `supabase/schema.sql` - 创建表结构
   - `data/processed/01_dynasties.sql` - 导入朝代
   - `data/processed/02_poets_*.sql` - 导入诗人
   - `data/processed/03_poems_*.sql` - 导入诗词

#### 方法二：批量导入脚本

```bash
# 使用 Supabase CLI
supabase db push

# 或使用 Node.js 脚本批量插入
npx tsx scripts/import-to-supabase.ts
```

### 7.3 注意事项

- **数据量大**: 诗词数据约 9 万条，建议分批导入
- **超时问题**: 单次 SQL 执行可能超时，需分文件执行
- **内存限制**: 大文件导入时注意内存使用

---

## 八、数据使用示例

### 8.1 在应用中读取

```typescript
import { usePoemStore } from '@/store/poems';

function PoemList() {
  const poems = usePoemStore((state) => state.poems);
  const fetchPoems = usePoemStore((state) => state.fetchPoems);
  
  useEffect(() => {
    fetchPoems(); // 从 Supabase 获取数据
  }, []);
  
  return (
    <FlatList
      data={poems}
      renderItem={({ item }) => (
        <Text>{item.title} - {item.author}</Text>
      )}
    />
  );
}
```

### 8.2 搜索过滤

```typescript
import { filterPoems } from '@/store/poems';

const results = filterPoems(poems, '李白', '唐');
// 返回唐代李白的所有诗词
```

---

## 九、数据维护

### 9.1 更新数据

```bash
# 更新原始数据
cd data/raw/chinese-poetry
git pull origin master

# 重新处理数据
cd ../../..
npx tsx scripts/transform-poetry.ts
```

### 9.2 添加翻译

当前数据中 `*_ar` 字段为空，需要后续添加阿拉伯语翻译：

1. 使用翻译 API 批量翻译
2. 人工校对重要诗词
3. 更新 `is_translated` 字段

---

## 十、相关文件

| 文件 | 说明 |
|------|------|
| `supabase/schema.sql` | 数据库表结构定义 |
| `scripts/transform-poetry.ts` | 数据转换脚本 |
| `scripts/fetch-tables.ts` | Supabase 表查询脚本 |
| `store/poems.ts` | Zustand 状态管理 |
| `lib/supabase.ts` | Supabase 客户端配置 |

---

## 十一、参考资料

- [chinese-poetry GitHub](https://github.com/chinese-poetry/chinese-poetry)
- [Supabase 文档](https://supabase.com/docs)
- [Zustand 状态管理](https://zustand-demo.pmnd.rs/)
