# Codeval – Multi-Agent Code Validator MVP

A local MVP that analyzes a codebase and produces a consolidated validation report. Uses an Orchestrator that routes work to specialist agents: **Functional Validator**, **Security Reviewer**, and **Error Resilience Reviewer**.

## Features

- **Fingerprint-based routing**: Detects languages, frameworks, tests, and entrypoints
- **Static heuristics**: TODO/FIXME, bare except, eval/exec, shell=True, SQL concatenation, unsafe deserialization, missing timeouts
- **Optional LLM enhancement**: OpenAI-compatible API for deeper analysis (falls back to static-only if no key)
- **Extensible**: Add new agents via copy/paste + registration

## Requirements

- Python 3.11+
- Optional: `OPENAI_API_KEY` for LLM mode

## Setup

```bash
pip install -e .
```

For development with tests:

```bash
pip install -e ".[dev]"
```

## Usage

### Basic run (JSON output)

```bash
codeval run --path ./myrepo --out report.json
```

### Markdown output

```bash
codeval run --path ./myrepo --out report.md --format md
```

### Static-only (no LLM)

```bash
codeval run --path ./myrepo --out report.json --llm off
```

Or omit `OPENAI_API_KEY` – the tool automatically falls back to static-only mode.

### With include/exclude patterns

```bash
codeval run --path ./myrepo --out report.json --include "*.py" --exclude "venv/*"
```

### Limit files analyzed

```bash
codeval run --path ./myrepo --out report.json --max-files 30
```

## Environment

| Variable           | Description                          |
|--------------------|--------------------------------------|
| `ANTHROPIC_API_KEY` | Claude API key (preferred if set)   |
| `OPENAI_API_KEY`   | OpenAI API key (fallback)            |

If `ANTHROPIC_API_KEY` is set, Claude is used. Otherwise OpenAI is used. If neither is set, runs in static-only mode.

## Output

### JSON report schema

- `summary`: Short description
- `scores`: `functional`, `security`, `resilience`, `overall` (0–100)
- `findings`: Deduplicated list with `id`, `severity`, `confidence`, `title`, `evidence`, `impact`, `recommendation`, `patch_hint`, `test_hint`
- `recommended_next_steps`: Actionable items
- `fingerprint`: Codebase metadata (languages, frameworks, tests, entrypoints)

### Scoring

- Each category starts at 100
- Severity penalties: critical -30, high -20, medium -10, low -3
- Overall = 0.4×functional + 0.35×security + 0.25×resilience

## Adding a New Agent

1. **Copy an existing agent** (e.g. `codeval/agents/functional.py`)

2. **Create your agent class**:

```python
# codeval/agents/myagent.py
from codeval.agents.base import BaseAgent
from codeval.schemas import AgentReport, CodebaseFingerprint, FileSnippet, HeuristicHit

class MyAgent(BaseAgent):
    name = "myagent"

    async def run(self, fingerprint, files, heuristics, llm_enabled):
        heuristic_findings = self._heuristics_to_findings(heuristics, "mycategory")
        if not llm_enabled:
            return self._merge_reports(heuristic_findings, None)
        # ... call LLM, merge, return AgentReport
```

3. **Register in the orchestrator** (`codeval/orchestrator.py`):

```python
from codeval.agents.myagent import MyAgent

agents = [FunctionalAgent(), SecurityAgent(), ResilienceAgent(), MyAgent()]
```

4. **Add routing in the slicer** if your agent needs special file selection (e.g. in `_score_file` and `slice_repo`).

5. **Update `CATEGORY_WEIGHTS`** in the orchestrator if you want the new agent to affect the overall score.

## Project Structure

```
codeval/
  __init__.py
  cli.py           # CLI entry
  orchestrator.py  # 3-stage pipeline
  llm.py           # OpenAI wrapper
  fingerprint.py   # Repo fingerprinting
  slicer.py        # File/snippet selection
  heuristics.py    # Static patterns
  schemas.py       # Pydantic models
  agents/
    base.py
    functional.py
    security.py
    resilience.py
tests/
config.example.yaml
```

## License

MIT
