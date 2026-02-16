# VibeRight

![Banner](Banner.png)

**Live demo:** [vibe-right.netlify.app](https://vibe-right.netlify.app/)

A lightweight hackathon MVP: upload a project (zip), build a **Project Map** once, then run a **Q/A loop**—answer code-understanding questions, get graded with feedback, and see your learner model update. Single-user demo, no auth.

---

## Contents

- [Understanding the project](#understanding-the-project)
- [Quick start](#quick-start)
- [API keys and environment](#api-keys-and-environment)
- [Running the project in the future](#running-the-project-in-the-future)
- [Flow](#flow)
- [Persistence](#persistence)
- [API reference](#api-for-reference)
- [Tech & constraints](#tech--constraints)

---

## Understanding the project

**What it does:** You upload a `.zip` of a codebase. VibeRight builds a one-time **project map** (key files and structure), then runs a **learn** flow: it asks you questions about the code, you answer, and it grades you and updates a simple learner model so later questions adapt to what you’ve mastered.

**Architecture:**

- **Next.js 14** (App Router) + **TypeScript**. No auth; single-user.
- **LLM:** By default a **mock client** (no API key). With your own **Anthropic API key**, the app uses **Claude** for building the project map, generating questions, and grading answers.
- **Data:** Locally, everything is file-based (`workspaces/`, `data/`). On deploy (e.g. Netlify), you can add blob storage so projects persist; see `lib/blobStorage.ts` and `lib/storage.ts`.

**User flow:**

1. **Home** – Upload a zip (max 50MB, ~200 files).
2. **Project** – Build project map once; it’s saved in the project workspace.
3. **Learn** – Q/A loop: question → answer → grade + feedback → next topic; session and learner model are persisted.

**Key directories:**

| Path | Purpose |
|------|--------|
| `app/` | Pages and API routes (home, project, learn, upload, map, question, grade, etc.). |
| `lib/` | Core logic: `schemas.ts` (Zod), `llm/` (mock + Claude), `workspace.ts`, `storage.ts`, `buildProjectMapSkill.ts`, zip/file handling. |
| `components/` | Shared UI (e.g. toasts). |
| `examples/` | `sample-src/` and script to build `sample.zip` for demos. |

---

## Quick start

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). You can use the app immediately with the **mock LLM** (no API key). To try with a sample codebase:

```bash
npm run create-sample-zip
```

Then upload `examples/sample.zip` from the home page.

---

## API keys and environment

The app works **without any API keys** using a built-in mock LLM. To use **your own Claude API** for real project maps, questions, and grading:

### 1. Get an API key

- Go to [Anthropic Console](https://console.anthropic.com/).
- Create or copy an API key (starts with `sk-ant-`).

### 2. Create local env file

In the **project root** (same folder as `package.json`):

```bash
cp .env.example .env.local
```

(On Windows: `copy .env.example .env.local`.)

### 3. Add your key

Edit `.env.local` and set:

```bash
USE_CLAUDE_LLM=true
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

- **Do not** commit `.env.local` or share your key (it’s in `.gitignore`).
- **Optional:** `ANTHROPIC_MODEL=claude-3-5-sonnet-20241022` (or another model). If unset, the app uses a default.

### 4. Restart the dev server

```bash
npm run dev
```

The app reads these at runtime: if `USE_CLAUDE_LLM` is `true` and `ANTHROPIC_API_KEY` is set, it uses Claude for map building, question generation, and grading. No code changes needed.

### Summary of env vars

| Variable | Required | Description |
|----------|----------|-------------|
| `USE_CLAUDE_LLM` | No | Set to `true` to enable Claude. Omit or set to anything else to use mock LLM. |
| `ANTHROPIC_API_KEY` | Only if using Claude | Your Anthropic API key. |
| `ANTHROPIC_MODEL` | No | Claude model name; optional, has a default. |

---

## Running the project in the future

### Commands

| Command | Description |
|---------|-------------|
| `npm install` | Install dependencies (run after clone or when `package.json` changes). |
| `npm run dev` | Start dev server at [http://localhost:3000](http://localhost:3000). |
| `npm run build` | Production build. |
| `npm run start` | Run production server (after `npm run build`). |
| `npm run create-sample-zip` | Build `examples/sample.zip` from `examples/sample-src` for testing. |
| `npm run dev:netlify` | Run with Netlify CLI (`npx netlify dev`) for local Netlify-style dev. |

### Environment

- **Local:** Copy `.env.example` to `.env.local` and add your API key if you want Claude. See [API keys and environment](#api-keys-and-environment).
- **Deploy (e.g. Netlify):** Set the same variables in the host’s environment (e.g. Netlify → Site settings → Environment variables). Never commit real keys.

### Where data lives

- **Project files:** `workspaces/<project_id>/`
- **Project map:** `workspaces/<project_id>/project_map.json`
- **Learner model:** `data/learner_model.json`
- **Sessions:** `data/sessions_<project_id>.json`

`workspaces` and `data` are in `.gitignore`. They are created when you upload a project and build a map.

### Coming back to the repo later

1. `git pull` (if applicable).
2. `npm install`.
3. If you use Claude: ensure `.env.local` exists with `USE_CLAUDE_LLM=true` and `ANTHROPIC_API_KEY` set.
4. `npm run dev` and open http://localhost:3000.

For more detail on architecture and conventions, see `AGENTS.md`.

---

## Flow

1. **Home (`/`)** – Upload a `.zip` of your project (max 50MB, ~200 files). Optional: use `examples/sample.zip` after running `npm run create-sample-zip`.
2. **Project (`/project/[id]`)** – Overview and **Build Project Map** (one-time). Map is stored as `project_map.json` in the project workspace.
3. **Learn (`/project/[id]/learn`)** – Q/A loop: see a question → type answer → submit → get score + feedback + next recommended topic. Session history and learner model are persisted.

---

## Persistence

- **Project files**: extracted under `workspaces/<project_id>/`.
- **Project map**: `workspaces/<project_id>/project_map.json`.
- **Learner model**: `data/learner_model.json` (single local user).
- **Session history**: `data/sessions_<project_id>.json`.

`workspaces` and `data` are in `.gitignore`; create them by uploading a project and building a map.

---

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

---

## Tech & constraints

**Tech:** Next.js 14 (App Router), TypeScript, Tailwind. Zod for schemas (`project_map`, question, grade, learner model, session). No auth, no payments, no vector DB; simple text search over files.

**Constraints (MVP):** Repos up to ~200 files; zip-only upload (no GitHub in this MVP); single-user; data stored on disk (or blob on deploy).
