#!/usr/bin/env python3
"""
scan-and-sync-docs.py
递归扫描每个子项目的 docs 目录，将文档同步到 overview-docs VitePress 站点。

用法：
  python scan-and-sync-docs.py [--root ROOT_DIR] [--target TARGET_DIR]

功能：
  1. 扫描 apps/ 下每个子项目的 docs/ 目录、project/ 目录、根目录 README.md / SPEC.md
  2. 将中文文件名 slug 化，保留目录结构
  3. 复制到 overview-docs/apps/<项目名>/ 下对应的路径
  4. 生成 VitePress 侧边栏配置 JSON
  5. 生成每个子项目的索引页（带美化卡片）
"""

import os
import sys
import re
import json
import argparse
import shutil
from pathlib import Path
from collections import OrderedDict

# ─── slug 化 ───────────────────────────────────────────────
def slugify(text: str) -> str:
    """将文件名转为 URL 友好的 slug"""
    name = Path(text).stem
    # 已有的英文 slug 直接返回
    if re.match(r'^[a-z0-9-]+$', name, re.I):
        return name.lower()
    # 中文映射表（常用项目文档关键词）
    slug_map = {
        '产品需求汇总': 'product-requirements',
        '最终确认-目标用户画像': 'user-persona',
        '最终确认-核心价值主张': 'value-proposition',
        '最终确认-产品差异化定位': 'differentiation',
        '最终确认-竞品分析': 'competitor-analysis',
        '最终确认-用户使用场景': 'user-scenarios',
        '最终确认-信息架构': 'information-architecture',
        '最终确认-核心功能列表': 'core-features',
        '最终确认-功能设计': 'feature-design',
        '最终确认-视觉与交互': 'visual-interaction',
        '最终确认-商业模式': 'business-model',
        '最终确认-内容与技术': 'content-tech',
        '最终产品原型定稿': 'prototype-final',
        '最终技术方案设计': 'tech-design-final',
        '本地数据库': 'local-database',
        '迭代变更追踪': 'iter-change-tracking',
        '辅助能力': 'auxiliary-capabilities',
        '版本回滚': 'version-rollback',
        '分支管理': 'branch-management',
        '变更追踪': 'change-tracking',
        '标签展示': 'tag-display',
        '产品需求确认点': 'requirements',
        '技术方案设计': 'tech-plans',
        '超级代理迁移方案': 'superagent-migration',
    }
    for cn, en in slug_map.items():
        if cn in name:
            return en
    # 兜底：用 pinyin 风格简写或 hash
    slug = re.sub(r'[^\w\s-]', '', name).strip().lower()
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug[:60] if slug else f'doc-{abs(hash(name)) % 10000}'


# ─── 文档发现 ───────────────────────────────────────────────
SKIP_DIRS = {'node_modules', '.next', '.git', '.vercel', '.expo', '__pycache__',
             '_legacy-nextjs', '.pytest_cache', 'data', 'scripts', 'dist', 'build', '.cache'}

def find_docs_for_app(app_dir: str) -> list:
    """发现一个 app 下所有文档文件，返回 [(相对路径, 绝对路径)] 列表"""
    docs = []
    app_name = os.path.basename(app_dir)

    # 1. docs/ 目录
    docs_dir = os.path.join(app_dir, 'docs')
    if os.path.isdir(docs_dir):
        for root, dirs, files in os.walk(docs_dir):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for f in files:
                if f.endswith('.md'):
                    full = os.path.join(root, f)
                    rel = os.path.relpath(full, docs_dir)
                    docs.append((rel, full))

    # 2. project/ 目录（teamclaw 等）
    proj_dir = os.path.join(app_dir, 'project')
    if os.path.isdir(proj_dir):
        for root, dirs, files in os.walk(proj_dir):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for f in files:
                if f.endswith('.md'):
                    full = os.path.join(root, f)
                    rel = os.path.relpath(full, proj_dir)
                    # 放到 project/ 子目录下
                    docs.append((f'project/{rel}', full))

    # 3. 根目录关键文件（README.md, SPEC.md, AGENTS.md）
    for fname in ['README.md', 'SPEC.md', 'AGENTS.md']:
        full = os.path.join(app_dir, fname)
        if os.path.isfile(full):
            docs.append((fname, full))

    # 4. 根目录其他重要文档
    for fname in os.listdir(app_dir):
        if fname.endswith('.md') and fname not in ['README.md', 'SPEC.md', 'AGENTS.md']:
            full = os.path.join(app_dir, fname)
            if os.path.isfile(full):
                docs.append((fname, full))

    return docs


# ─── 复制与 slug 化 ───────────────────────────────────────
def copy_docs_to_target(docs: list, target_dir: str, app_name: str) -> list:
    """将文档复制到目标目录，返回 [(slug_path, source_path, display_name)]"""
    results = []
    seen_slugs = {}

    for rel_path, src_path in docs:
        # 构建 slug 路径
        parts = Path(rel_path).parts
        slug_parts = []
        for i, part in enumerate(parts[:-1]):  # 目录部分
            slug_parts.append(slugify(part) if not re.match(r'^[a-z0-9-]+$', part, re.I) else part.lower())
        
        filename = parts[-1]
        stem = Path(filename).stem
        slug_name = slugify(filename)

        # 处理重名
        final_slug = slug_name
        if final_slug in seen_slugs:
            final_slug = f"{slug_name}-{len(seen_slugs)}"
        seen_slugs[final_slug] = True

        # 构建目标路径
        if slug_parts:
            target_subdir = os.path.join(target_dir, *slug_parts)
        else:
            target_subdir = target_dir
        os.makedirs(target_subdir, exist_ok=True)

        target_file = os.path.join(target_subdir, f"{final_slug}.md")

        # 复制文件
        try:
            shutil.copy2(src_path, target_file)
        except Exception as e:
            print(f"  ⚠️  复制失败: {src_path} → {target_file}: {e}")
            continue

        # 显示名 = 文件名去 .md
        display_name = stem
        # 构建页面链接
        rel_slug = '/'.join(slug_parts + [final_slug]) if slug_parts else final_slug
        
        results.append({
            'slug': rel_slug,
            'file': target_file,
            'name': display_name,
            'source': src_path,
            'group': '/'.join(slug_parts) if slug_parts else '',
        })

    return results


# ─── 侧边栏配置生成 ─────────────────────────────────────────
def generate_sidebar_config(all_apps_docs: dict) -> dict:
    """生成 VitePress 侧边栏配置"""
    sidebar = {}

    for app_name, docs in all_apps_docs.items():
        # 按分组整理
        groups = OrderedDict()
        for doc in docs:
            group = doc['group'] or '_root'
            if group not in groups:
                groups[group] = []
            groups[group].append(doc)

        items = []
        # 根目录文件
        if '_root' in groups:
            for doc in groups['_root']:
                link = f'/apps/{app_name}/{doc["slug"]}'
                items.append({'text': doc['name'], 'link': link})

        # 子目录
        for group_name, group_docs in groups.items():
            if group_name == '_root':
                continue
            group_items = []
            for doc in group_docs:
                link = f'/apps/{app_name}/{doc["slug"]}'
                group_items.append({'text': doc['name'], 'link': link})
            
            items.append({
                'text': group_name,
                'collapsed': True,
                'items': group_items,
            })

        if items:
            sidebar[f'/apps/{app_name}/'] = [
                {
                    'text': f'← 返回项目列表',
                    'link': '/apps/',
                },
                {
                    'text': get_app_display_name(app_name),
                    'items': items,
                }
            ]

    return sidebar


def get_app_display_name(app_name: str) -> str:
    """获取应用显示名"""
    names = {
        'marker-tracker': '🎯 Marker Tracker',
        'xiaowutools': '🛠️ 小伍工具箱',
        'teamclaw': '🤝 TeamClaw',
        'projects-dashboard': '📊 项目仪表盘',
        'poetry-app': '📜 诗词应用',
    }
    return names.get(app_name, f'📦 {app_name}')


def get_app_description(app_name: str) -> str:
    """获取应用简介"""
    descs = {
        'marker-tracker': 'X 光造影序列双 Marker 自动跟踪与距离测量工具',
        'xiaowutools': 'Next.js 14 在线工具网站',
        'teamclaw': 'Tauri 2.x 桌面应用 + 全栈协作平台',
        'projects-dashboard': 'Next.js 16 项目管理仪表盘',
        'poetry-app': 'Expo 跨平台古诗词移动应用',
    }
    return descs.get(app_name, '')


# ─── 索引页生成 ─────────────────────────────────────────────
def generate_app_index(app_name: str, docs: list) -> str:
    """生成子项目索引页（带美化卡片）"""
    display = get_app_display_name(app_name)
    desc = get_app_description(app_name)

    # 按 group 分组
    groups = OrderedDict()
    root_docs = []
    for doc in docs:
        if doc['group']:
            g = doc['group']
            if g not in groups:
                groups[g] = []
            groups[g].append(doc)
        else:
            root_docs.append(doc)

    cards_html = ''
    for doc in root_docs:
        cards_html += f'''<a class="doc-card" href="/apps/{app_name}/{doc['slug']}">
  <div class="doc-card-title">{doc['name']}</div>
  <div class="doc-card-arrow">→</div>
</a>\n'''

    group_sections = ''
    for gname, gdocs in groups.items():
        group_title = gname.replace('-', ' ').title()
        group_cards = ''
        for doc in gdocs:
            group_cards += f'''<a class="doc-card" href="/apps/{app_name}/{doc['slug']}">
  <div class="doc-card-title">{doc['name']}</div>
  <div class="doc-card-arrow">→</div>
</a>\n'''
        group_sections += f'''## {group_title}

<div class="doc-grid">
{group_cards}
</div>

'''

    return f'''---
layout: page
---

# {display}

{desc}

[← 返回项目列表](/apps/)

---

''' + (f'''## 核心文档

<div class="doc-grid">
{cards_html}
</div>

''' if cards_html else '') + group_sections + '''
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
'''


# ─── 应用列表页生成 ─────────────────────────────────────────
def generate_apps_index(all_apps_docs: dict) -> str:
    """生成应用总览页"""
    cards = ''
    for app_name in ['marker-tracker', 'xiaowutools', 'teamclaw', 'projects-dashboard', 'poetry-app']:
        if app_name not in all_apps_docs:
            continue
        docs = all_apps_docs[app_name]
        display = get_app_display_name(app_name)
        desc = get_app_description(app_name)
        doc_count = len(docs)
        cards += f'''<a class="app-card" href="/apps/{app_name}/">
  <div class="app-card-icon">{display.split()[0]}</div>
  <div class="app-card-info">
    <div class="app-card-name">{display.split(' ', 1)[1] if ' ' in display else display}</div>
    <div class="app-card-desc">{desc}</div>
    <div class="app-card-count">{doc_count} 篇文档</div>
  </div>
  <div class="app-card-arrow">→</div>
</a>\n'''

    return f'''---
layout: page
---

# 📦 应用项目

致富经旗下所有应用项目的文档中心。

<div class="app-grid">
{cards}
</div>

<style>
.app-grid {{
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  margin: 24px 0;
}}
.app-card {{
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
}}
.app-card:hover {{
  border-color: var(--vp-c-brand);
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.08);
}}
.app-card-icon {{
  font-size: 32px;
  flex-shrink: 0;
}}
.app-card-info {{
  flex: 1;
  min-width: 0;
}}
.app-card-name {{
  font-size: 16px;
  font-weight: 600;
  color: var(--vp-c-text-1);
  margin-bottom: 4px;
}}
.app-card-desc {{
  font-size: 13px;
  color: var(--vp-c-text-2);
  margin-bottom: 6px;
}}
.app-card-count {{
  font-size: 12px;
  color: var(--vp-c-text-3);
}}
.app-card-arrow {{
  color: var(--vp-c-text-3);
  font-size: 20px;
  flex-shrink: 0;
}}
</style>
'''


# ─── VitePress 配置生成 ──────────────────────────────────────
def generate_vitepress_config(all_apps_docs: dict, notes_sidebar: list) -> str:
    """生成完整的 VitePress 配置文件"""
    
    # Apps 侧边栏
    apps_sidebar = [
        {
            'text': '📦 应用项目',
            'items': [
                {'text': '项目一览', 'link': '/apps/'},
            ]
        }
    ]
    for app_name in ['marker-tracker', 'xiaowutools', 'teamclaw', 'projects-dashboard', 'poetry-app']:
        if app_name in all_apps_docs:
            apps_sidebar.append({
                'text': get_app_display_name(app_name),
                'collapsed': True,
                'items': [
                    {'text': '项目首页', 'link': '/apps/' + app_name + '/'},
                ] + [
                    {'text': doc['name'], 'link': '/apps/' + app_name + '/' + doc['slug']}
                    for doc in all_apps_docs[app_name][:8]
                ]
            })

    # 将 sidebar 转为 JS 字符串
    sidebar_js = json.dumps({
        '/apps/': apps_sidebar,
        '/notes/': notes_sidebar,
    }, ensure_ascii=False, indent=6)

    lines = [
        "import { defineConfig } from 'vitepress'",
        "",
        "export default defineConfig({",
        "  title: '致富经',",
        "  description: '项目文档 & 知识中心',",
        "  lang: 'zh-CN',",
        "",
        "  head: [",
        "    ['link', { rel: 'icon', href: '/favicon.ico' }]",
        "  ],",
        "",
        "  lastUpdated: true,",
        "",
        "  themeConfig: {",
        "    nav: [",
        "      { text: '首页', link: '/' },",
        "      {",
        "        text: '应用项目',",
        "        items: [",
        "          { text: '🎯 Marker Tracker', link: '/apps/marker-tracker/' },",
        "          { text: '🛠️ 小伍工具箱', link: '/apps/xiaowutools/' },",
        "          { text: '🤝 TeamClaw', link: '/apps/teamclaw/' },",
        "          { text: '📊 项目仪表盘', link: '/apps/projects-dashboard/' },",
        "          { text: '📜 诗词应用', link: '/apps/poetry-app/' },",
        "        ]",
        "      },",
        "      { text: '学习笔记', link: '/notes/' },",
        "    ],",
        "",
        "    sidebar: " + sidebar_js + ",",
        "",
        "    socialLinks: [",
        "      { icon: 'github', link: 'https://github.com/weisiwu' }",
        "    ],",
        "",
        "    footer: {",
        "      message: '致富经项目文档中心',",
        "      copyright: '© 2024-2026 致富经'",
        "    },",
        "",
        "    search: {",
        "      provider: 'local'",
        "    },",
        "",
        "    notFound: {",
        "      title: '页面未找到',",
        "      quote: '你访问的页面不存在，请检查链接或返回首页。',",
        "      linkText: '返回首页',",
        "      linkLabel: '返回首页',",
        "    },",
        "  }",
        "})",
    ]
    return "\n".join(lines)


# ─── 主流程 ─────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='扫描项目文档并同步到 VitePress 站点')
    parser.add_argument('--root', default=None, help='项目根目录（默认自动检测）')
    parser.add_argument('--target', default=None, help='VitePress 站点目录（默认 overview-docs/）')
    parser.add_argument('--dry-run', action='store_true', help='只打印不执行')
    args = parser.parse_args()

    # 自动检测根目录
    root = args.root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # 如果已经在 overview-docs/scripts/ 下，往上两层
    if os.path.basename(root) == 'overview-docs':
        root = os.path.dirname(root)
    target = args.target or os.path.join(root, 'overview-docs')

    print(f"📁 项目根目录: {root}")
    print(f"🎯 目标站点: {target}")
    print()

    apps_dir = os.path.join(root, 'apps')
    if not os.path.isdir(apps_dir):
        print(f"❌ apps 目录不存在: {apps_dir}")
        sys.exit(1)

    all_apps_docs = {}

    # 遍历每个子项目
    for app_name in sorted(os.listdir(apps_dir)):
        app_dir = os.path.join(apps_dir, app_name)
        if not os.path.isdir(app_dir):
            continue
        if app_name.startswith('.') or app_name in SKIP_DIRS:
            continue

        print(f"🔍 扫描: {app_name}")
        docs = find_docs_for_app(app_dir)
        print(f"   发现 {len(docs)} 篇文档")

        if not docs:
            continue

        # 复制到目标
        app_target = os.path.join(target, 'apps', app_name)
        os.makedirs(app_target, exist_ok=True)

        results = copy_docs_to_target(docs, app_target, app_name)
        all_apps_docs[app_name] = results

        # 生成索引页
        index_content = generate_app_index(app_name, results)
        if not args.dry_run:
            with open(os.path.join(app_target, 'index.md'), 'w') as f:
                f.write(index_content)

        for r in results:
            print(f"   ✅ {r['name']} → {r['slug']}")

    # 生成应用总览页
    print(f"\n📝 生成应用总览页")
    apps_index = generate_apps_index(all_apps_docs)
    if not args.dry_run:
        with open(os.path.join(target, 'apps', 'index.md'), 'w') as f:
            f.write(apps_index)

    # 生成 VitePress 配置
    notes_sidebar = [
        {'text': '📖 学习笔记', 'collapsed': False, 'items': [{'text': '笔记一览', 'link': '/notes/'}]},
        {'text': '🤖 Agent 框架', 'collapsed': True, 'items': [
            {'text': 'ACP 协议定义与 OpenClaw 用法', 'link': '/notes/learning/acp'},
            {'text': 'OpenClaw Subagent 并发任务', 'link': '/notes/learning/openclaw-subagent'},
            {'text': 'OpenClaw 事件与钩子体系', 'link': '/notes/learning/openclaw-events-hooks'},
            {'text': 'OpenClaw 能力地图与 Tools', 'link': '/notes/learning/openclaw-tools'},
            {'text': 'OpenClaw CLI 强化 Agent', 'link': '/notes/learning/openclaw-cli'},
        ]},
        {'text': '🎨 AI 应用设计', 'collapsed': True, 'items': [
            {'text': 'AI 生成 APP 设计稿最佳实践', 'link': '/notes/learning/ai-app-design'},
            {'text': 'Claude Code 源码架构观察', 'link': '/notes/learning/claude-code-arch'},
        ]},
        {'text': '📚 RAG 与知识库', 'collapsed': True, 'items': [
            {'text': 'Dify 知识库构建指南', 'link': '/notes/learning/dify-knowledge-base'},
            {'text': 'MaxKB 知识库构建指南', 'link': '/notes/learning/maxkb-knowledge-base'},
            {'text': 'RAGFlow 知识库构建指南', 'link': '/notes/learning/ragflow-knowledge-base'},
            {'text': 'RAPTOR 递归摘要检索指南', 'link': '/notes/learning/raptor'},
        ]},
        {'text': '🔧 其他技术', 'collapsed': True, 'items': [
            {'text': 'Token 中转站深度解析', 'link': '/notes/learning/token-gateway'},
            {'text': '个人 Markdown 知识库方案', 'link': '/notes/learning/markdown-knowledge-base'},
        ]},
        {'text': '⚡ 实战笔记', 'collapsed': True, 'items': [
            {'text': 'GitHub Actions 调度架构改造', 'link': '/notes/practice/actions-loop'},
            {'text': 'Agent 超时排查与 Cron 机制', 'link': '/notes/practice/agent-timeout'},
            {'text': 'Issue 残留与幂等性设计', 'link': '/notes/practice/issue-idempotent'},
        ]},
    ]

    config_content = generate_vitepress_config(all_apps_docs, notes_sidebar)
    if not args.dry_run:
        config_path = os.path.join(target, '.vitepress', 'config.mts')
        with open(config_path, 'w') as f:
            f.write(config_content)
        print(f"   ✅ 配置已写入: {config_path}")

    # 汇总
    total = sum(len(v) for v in all_apps_docs.values())
    print(f"\n{'='*50}")
    print(f"✅ 扫描完成！共 {len(all_apps_docs)} 个项目，{total} 篇文档")
    print(f"{'='*50}")


if __name__ == '__main__':
    main()
