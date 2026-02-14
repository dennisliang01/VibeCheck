# Agent guide

Short reference for the AI assistant working in this repo.

## Architecture

- **Next.js 14** (App Router) + **TypeScript**. Single-user demo; no auth.
- **Flow:** User uploads a .zip → files go to `workspaces/<project_id>/` → one-time **project map** is built (discovery + LLM or mock) → **Q/A learn page** (questions, answer, grade, learner model).
- **Persistence:** File-based. `workspaces/<id>/` (extracted zip + `project_map.json`), `data/learner_model.json`, `data/sessions_<id>.json`.
- **LLM:** Interface in `lib/llm/`; **MockLLMClient** by default, **ClaudeLLMClient** when `USE_CLAUDE_LLM=true` and `ANTHROPIC_API_KEY` set.

## Key directories

| Path | Purpose |
|------|--------|
| `app/` | Pages and API routes. `app/page.tsx` (home), `app/project/[id]/` (redirect to learn), `app/project/[id]/learn/page.tsx` (Q/A + code viewer), `app/api/` (upload, load-sample, project/[id]/map, question, grade, tree, file, search, session). |
| `lib/` | Core logic. `schemas.ts` (Zod), `llm/` (types, mock, claude), `workspace.ts` (repo_tree, get_file, search_repo), `storage.ts` (project map, learner model, session), `buildProjectMapSkill.ts` (discovery + key files), `zipExtract.ts`, `filesSummary.ts`. |
| `components/` | Shared UI (e.g. `ToastContext.tsx`). |
| `examples/` | `sample-src/` and `sample.zip` for demo. |

## Commands

```bash
npm install
npm run dev          # http://localhost:3000
npm run build
npm run create-sample-zip   # create examples/sample.zip
```

## Conventions

- **TypeScript:** Strict. Use types/interfaces; avoid `any`.
- **Schemas:** All shared shapes (project map, question, grade, learner model, session) live in `lib/schemas.ts` and use **Zod**. Validate at API boundaries (e.g. `ProjectMapSchema.parse(...)`).
- **Edits:** Prefer **minimal, targeted changes**. Use search-and-replace or small edits; **do not rewrite whole files** unless the task clearly requires it (e.g. new page or major refactor). Preserve existing style and structure when editing.
- **APIs:** Route handlers in `app/api/` return JSON; use `NextResponse.json()`. Parse request body with the same Zod schemas where applicable.
- **Styling:** Tailwind. CSS variables in `app/globals.css` (`--bg`, `--card`, `--border`, `--text`, `--muted`, `--accent`, etc.).
