# Repository Guidelines

## Project Structure & Module Organization
- `app/`: Next.js App Router pages and layouts.
  - `app/tools/<tool-slug>/page.tsx`: individual tool pages.
  - `app/api/.../route.ts`: server endpoints (e.g., ICO conversion, IP geo).
  - `app/layout.tsx`, `app/page.tsx`, `app/globals.css`: global shell and homepage.
- `components/`: shared UI (`Header`, `Footer`, `ToolsGrid`, ads, recent usage).
- `public/`: static assets (`favicon.ico`, `robots.txt`, `sitemap.xml`, `ads.txt`).
- `scripts/`: maintenance automation (version bump, tool keep-lists, monitoring).

## Build, Test, and Development Commands
- `npm run dev`: start local dev server.
- `npm run lint`: run Next.js ESLint checks (`--max-warnings=200`).
- `npm run build`: production build (runs `prebuild` first).
- `npm run start`: serve the built app locally.

Example workflow:
```bash
npm run lint && npm run build
```
Run this before opening a PR or deploying.

## Coding Style & Naming Conventions
- Language: TypeScript + React function components.
- Indentation: 2 spaces; keep imports grouped and unused imports removed.
- Tool route naming: kebab-case directory names under `app/tools/` (e.g., `json-format`, `ip-query`).
- Component naming: PascalCase file/component names in `components/`.
- Styling: Tailwind utility classes in JSX; global tokens/overrides in `app/globals.css`.

## Testing Guidelines
- No dedicated unit test framework is currently configured.
- Required quality gate is:
  1. `npm run lint`
  2. `npm run build`
- For UI changes, manually verify homepage, header/footer contrast, category switching, and at least one tool detail page.

## Commit & Pull Request Guidelines
- Existing history includes automated commits like `Auto upgrade: YYYY-MM-DD HH:MM`.
- For manual work, use clear, scoped messages, e.g.:
  - `feat(ui): redesign tools grid filtering flow`
  - `fix(header): improve nav text contrast`
- PRs should include:
  - concise change summary and motivation,
  - affected paths (e.g., `components/ToolsGrid.tsx`),
  - screenshots/GIFs for UI updates,
  - lint/build status,
  - deployment preview or production URL when applicable.

## Security & Configuration Notes
- Do not hardcode secrets in source.
- Review external API usage in `app/api` and tool pages; prefer server routes over direct insecure HTTP calls.

## Agent-Specific Rule
- Deployment is opt-in only: do not run `vercel` or any production deployment command unless the user explicitly asks to deploy in that turn.
- After code changes, default to local verification only (`npm run lint`, `npm run build`) and report status without publishing.
