import { defineConfig } from 'vitepress'

export default defineConfig({
  title: '致富经',
  description: '项目文档 & 知识中心',
  lang: 'zh-CN',

  head: [
    ['link', { rel: 'icon', href: '/favicon.ico' }]
  ],

  lastUpdated: true,

  themeConfig: {
    nav: [
      { text: '首页', link: '/' },
      {
        text: '应用项目',
        items: [
          { text: '🎯 Marker Tracker', link: '/apps/marker-tracker' },
          { text: '🛠️ 小伍工具箱', link: '/apps/xiaowutools' },
          { text: '🤝 TeamClaw', link: '/apps/teamclaw' },
          { text: '📊 项目仪表盘', link: '/apps/projects-dashboard' },
          { text: '📜 诗词应用', link: '/apps/poetry-app' },
        ]
      },
      { text: '学习笔记', link: '/notes/' },
    ],

    sidebar: {
      '/apps/': [
        {
          text: '📦 应用项目',
          items: [
            { text: '项目一览', link: '/apps/' },
            { text: '🎯 Marker Tracker', link: '/apps/marker-tracker' },
            { text: '🛠️ 小伍工具箱', link: '/apps/xiaowutools' },
            { text: '🤝 TeamClaw', link: '/apps/teamclaw' },
            { text: '📊 项目仪表盘', link: '/apps/projects-dashboard' },
            { text: '📜 诗词应用', link: '/apps/poetry-app' },
          ]
        }
      ],
      '/notes/': [
        {
          text: '📖 学习笔记',
          items: [
            { text: '笔记一览', link: '/notes/' },
            { text: '技术文章', link: '/notes/learning' },
            { text: '实战笔记', link: '/notes/practice' },
          ]
        }
      ],
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
