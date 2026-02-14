# VibeCheck

A lightweight hackathon MVP: upload a project (zip), build a **Project Map** once, then run a **Q/A loop**—answer code-understanding questions, get graded with feedback, and see your learner model update. Single-user demo, no auth.

## Run locally

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Create example zip (for demo)

```bash
npm run create-sample-zip
```

This creates `examples/sample.zip` from `examples/sample-src`. Upload that zip on the home page to try the flow.

## Flow

1. **Home (`/`)** – Upload a `.zip` of your project (max 50MB, ~200 files). Optional: use `examples/sample.zip` after running `npm run create-sample-zip`.
2. **Project (`/project/[id]`)** – Overview and **Build Project Map** (one-time). Map is stored as `project_map.json` in the project workspace.
3. **Learn (`/project/[id]/learn`)** – Q/A loop: see a question → type answer → submit → get score + feedback + next recommended topic. Session history and learner model are persisted.

## Persistence

- **Project files**: extracted under `workspaces/<project_id>/`.
- **Project map**: `workspaces/<project_id>/project_map.json`.
- **Learner model**: `data/learner_model.json` (single local user).
- **Session history**: `data/sessions_<project_id>.json`.

`workspaces` and `data` are in `.gitignore`; create them by uploading a project and building a map.

## Claude API integration

By default the app uses **MockLLMClient** (no API key, deterministic questions/grades). To use **Claude** for real project maps, questions, and grading:

1. Get an API key from [Anthropic Console](https://console.anthropic.com/).
2. Copy `.env.example` to `.env.local` in the project root.
3. Set in `.env.local`:
   ```bash
   USE_CLAUDE_LLM=true
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```
4. Restart the dev server (`npm run dev`).

The app checks these at runtime: if both are set, it uses `ClaudeLLMClient` for build project map, generate question, and grade answer. No code changes required.

## API (for reference)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/upload` | Upload zip (form field `file`) |
| GET | `/api/projects` | List project IDs |
| GET/POST | `/api/project/[id]/map` | Get or build project map |
| GET | `/api/project/[id]/question` | Get next question |
| POST | `/api/project/[id]/grade` | Submit answer, get grade |
| GET | `/api/project/[id]/tree` | File tree |
| GET | `/api/project/[id]/file?path=...` | Read file |
| GET | `/api/project/[id]/search?q=...` | Text search |
| GET | `/api/project/[id]/session` | Session history |

## Tech

- Next.js 14 (App Router), TypeScript, Tailwind.
- Zod for schemas (`project_map`, `question_obj`, `grade_obj`, learner model, session).
- No auth, no payments, no vector DB; simple text search over files.

## Constraints (MVP)

- Repos up to ~200 files.
- Zip-only upload (no GitHub URL in this MVP).
- Single-user; data stored on disk.
