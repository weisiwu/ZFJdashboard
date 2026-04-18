import { defineConfig } from 'vitepress'

export default defineConfig({
  title: '致富经',
  description: '项目文档 & 知识中心',
  lang: 'zh-CN',

  head: [
    ['link', { rel: 'icon', href: '/favicon.ico' }]
  ],

  lastUpdated: true,
  ignoreDeadLinks: true,

  markdown: {
    template: false,
  },

  themeConfig: {
    nav: [
      { text: '首页', link: '/' },
      {
        text: '应用项目',
        items: [
          { text: '🎯 Marker Tracker', link: '/apps/marker-tracker/' },
          { text: '🛠️ 小伍工具箱', link: '/apps/xiaowutools/' },
          { text: '🤝 TeamClaw', link: '/apps/teamclaw/' },
          { text: '📊 项目仪表盘', link: '/apps/projects-dashboard/' },
          { text: '📜 诗词应用', link: '/apps/poetry-app/' },
        ]
      },
      { text: '学习笔记', link: '/notes/' },
    ],

    sidebar: {
      "/apps/": [
            {
                  "text": "📦 应用项目",
                  "items": [
                        {
                              "text": "项目一览",
                              "link": "/apps/"
                        }
                  ]
            },
            {
                  "text": "🎯 Marker Tracker",
                  "collapsed": true,
                  "items": [
                        {
                              "text": "项目首页",
                              "link": "/apps/marker-tracker/"
                        },
                        {
                              "text": "PRD",
                              "link": "/apps/marker-tracker/prd"
                        },
                        {
                              "text": "TEST_CASES",
                              "link": "/apps/marker-tracker/test_cases"
                        },
                        {
                              "text": "TASKS",
                              "link": "/apps/marker-tracker/tasks"
                        },
                        {
                              "text": "TECHNICAL_DESIGN",
                              "link": "/apps/marker-tracker/technical_design"
                        },
                        {
                              "text": "README",
                              "link": "/apps/marker-tracker/readme"
                        }
                  ]
            },
            {
                  "text": "🛠️ 小伍工具箱",
                  "collapsed": true,
                  "items": [
                        {
                              "text": "项目首页",
                              "link": "/apps/xiaowutools/"
                        },
                        {
                              "text": "README",
                              "link": "/apps/xiaowutools/readme"
                        },
                        {
                              "text": "SPEC",
                              "link": "/apps/xiaowutools/spec"
                        },
                        {
                              "text": "AGENTS",
                              "link": "/apps/xiaowutools/agents"
                        }
                  ]
            },
            {
                  "text": "🤝 TeamClaw",
                  "collapsed": true,
                  "items": [
                        {
                              "text": "项目首页",
                              "link": "/apps/teamclaw/"
                        },
                        {
                              "text": "prd-module6-conversation-lifecycle",
                              "link": "/apps/teamclaw/project/prd-module6-conversation-lifecycle"
                        },
                        {
                              "text": "prd-module2-agent-orchestration",
                              "link": "/apps/teamclaw/project/prd-module2-agent-orchestration"
                        },
                        {
                              "text": "teamclaw-conversation-lifecycle",
                              "link": "/apps/teamclaw/project/teamclaw-conversation-lifecycle"
                        },
                        {
                              "text": "prd-module1-project-import",
                              "link": "/apps/teamclaw/project/prd-module1-project-import"
                        },
                        {
                              "text": "prd-module5-knowledge-base",
                              "link": "/apps/teamclaw/project/prd-module5-knowledge-base"
                        },
                        {
                              "text": "prd-module3-task-system",
                              "link": "/apps/teamclaw/project/prd-module3-task-system"
                        },
                        {
                              "text": "prd-module4-capability-system",
                              "link": "/apps/teamclaw/project/prd-module4-capability-system"
                        },
                        {
                              "text": "teamclaw-architecture",
                              "link": "/apps/teamclaw/project/teamclaw-architecture"
                        }
                  ]
            },
            {
                  "text": "📊 项目仪表盘",
                  "collapsed": true,
                  "items": [
                        {
                              "text": "项目首页",
                              "link": "/apps/projects-dashboard/"
                        },
                        {
                              "text": "README",
                              "link": "/apps/projects-dashboard/readme"
                        },
                        {
                              "text": "PROMPT_SUPABASE_MIGRATION",
                              "link": "/apps/projects-dashboard/prompt_supabase_migration"
                        }
                  ]
            },
            {
                  "text": "📜 诗词应用",
                  "collapsed": true,
                  "items": [
                        {
                              "text": "项目首页",
                              "link": "/apps/poetry-app/"
                        },
                        {
                              "text": "最终产品原型定稿",
                              "link": "/apps/poetry-app/prototype-final"
                        },
                        {
                              "text": "最终技术方案设计",
                              "link": "/apps/poetry-app/tech-design-final"
                        },
                        {
                              "text": "本地数据库",
                              "link": "/apps/poetry-app/local-database"
                        },
                        {
                              "text": "00-产品需求汇总",
                              "link": "/apps/poetry-app/requirements/product-requirements"
                        },
                        {
                              "text": "14-18-最终确认-视觉与交互",
                              "link": "/apps/poetry-app/requirements/visual-interaction"
                        },
                        {
                              "text": "02-最终确认-核心价值主张",
                              "link": "/apps/poetry-app/requirements/value-proposition"
                        },
                        {
                              "text": "05-最终确认-用户使用场景",
                              "link": "/apps/poetry-app/requirements/user-scenarios"
                        },
                        {
                              "text": "04-最终确认-竞品分析",
                              "link": "/apps/poetry-app/requirements/competitor-analysis"
                        }
                  ]
            }
      ],
      "/notes/": [
            {
                  "text": "📖 学习笔记",
                  "collapsed": false,
                  "items": [
                        {
                              "text": "笔记一览",
                              "link": "/notes/"
                        }
                  ]
            },
            {
                  "text": "🤖 Agent 框架",
                  "collapsed": true,
                  "items": [
                        {
                              "text": "ACP 协议定义与 OpenClaw 用法",
                              "link": "/notes/learning/acp"
                        },
                        {
                              "text": "OpenClaw Subagent 并发任务",
                              "link": "/notes/learning/openclaw-subagent"
                        },
                        {
                              "text": "OpenClaw 事件与钩子体系",
                              "link": "/notes/learning/openclaw-events-hooks"
                        },
                        {
                              "text": "OpenClaw 能力地图与 Tools",
                              "link": "/notes/learning/openclaw-tools"
                        },
                        {
                              "text": "OpenClaw CLI 强化 Agent",
                              "link": "/notes/learning/openclaw-cli"
                        }
                  ]
            },
            {
                  "text": "🎨 AI 应用设计",
                  "collapsed": true,
                  "items": [
                        {
                              "text": "AI 生成 APP 设计稿最佳实践",
                              "link": "/notes/learning/ai-app-design"
                        },
                        {
                              "text": "Claude Code 源码架构观察",
                              "link": "/notes/learning/claude-code-arch"
                        }
                  ]
            },
            {
                  "text": "📚 RAG 与知识库",
                  "collapsed": true,
                  "items": [
                        {
                              "text": "Dify 知识库构建指南",
                              "link": "/notes/learning/dify-knowledge-base"
                        },
                        {
                              "text": "MaxKB 知识库构建指南",
                              "link": "/notes/learning/maxkb-knowledge-base"
                        },
                        {
                              "text": "RAGFlow 知识库构建指南",
                              "link": "/notes/learning/ragflow-knowledge-base"
                        },
                        {
                              "text": "RAPTOR 递归摘要检索指南",
                              "link": "/notes/learning/raptor"
                        }
                  ]
            },
            {
                  "text": "🔧 其他技术",
                  "collapsed": true,
                  "items": [
                        {
                              "text": "Token 中转站深度解析",
                              "link": "/notes/learning/token-gateway"
                        },
                        {
                              "text": "个人 Markdown 知识库方案",
                              "link": "/notes/learning/markdown-knowledge-base"
                        }
                  ]
            },
            {
                  "text": "⚡ 实战笔记",
                  "collapsed": true,
                  "items": [
                        {
                              "text": "GitHub Actions 调度架构改造",
                              "link": "/notes/practice/actions-loop"
                        },
                        {
                              "text": "Agent 超时排查与 Cron 机制",
                              "link": "/notes/practice/agent-timeout"
                        },
                        {
                              "text": "Issue 残留与幂等性设计",
                              "link": "/notes/practice/issue-idempotent"
                        }
                  ]
            }
      ]
},

    socialLinks: [
      { icon: 'github', link: 'https://github.com/weisiwu' }
    ],

    footer: {
      message: '致富经项目文档中心',
      copyright: '© 2024-2026 致富经'
    },

    search: {
      provider: 'local'
    },

    notFound: {
      title: '页面未找到',
      quote: '你访问的页面不存在，请检查链接或返回首页。',
      linkText: '返回首页',
      linkLabel: '返回首页',
    },
  }
})