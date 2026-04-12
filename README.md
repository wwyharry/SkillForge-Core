# SkillForge

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-Apache--2.0-green.svg)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
![Status](https://img.shields.io/badge/status-local--first-orange.svg)

English | [简体中文](README.zh-CN.md)

SkillForge is a repository distillation workbench that turns messy project materials into reusable AI skill packages.

It scans local folders, parses mixed document formats, extracts workflow evidence, clusters that evidence into capabilities, and compiles the result into previewable and exportable skill outputs through a built-in web UI.

## Why SkillForge?

Teams already have the raw knowledge they need: product docs, design notes, research reports, runbooks, SOPs, meeting notes, API references, and random markdown files scattered across repositories and shared folders.

The hard part is turning that fragmented, implicit knowledge into something reusable by an AI agent.

Doing that manually is slow and brittle:

- one-off scripts are fast to start but hard to maintain
- generic agent frameworks help orchestration, but they do not automatically distill repository knowledge into skill packages
- manual copy/paste into prompts does not scale across teams or projects

SkillForge focuses on that missing step:

> evidence extraction → capability clustering → skill compilation

So instead of just "running an agent," you can systematically convert repository knowledge into reusable skill artifacts.

## What makes it different?

### Compared with ad-hoc scripts

Ad-hoc scripts are useful for a single extraction pass, but they usually stop at file parsing or keyword search.

SkillForge gives you:

- a repeatable end-to-end pipeline
- structured job tracking
- a visual workflow dashboard
- preview and export for generated skill outputs

### Compared with LangChain / DSPy / custom agent stacks

Those tools are great for orchestration, prompting, and model workflows.
SkillForge solves a narrower but very practical problem: turning a real-world repository into reusable skill packages with a local-first review workflow.

In short:

- **LangChain / DSPy** help you build agent systems
- **SkillForge** helps you distill repository knowledge into agent-usable skills

They are complementary, not mutually exclusive.

## Core use cases

- Distill internal documentation into reusable team skills
- Convert research folders into structured analyst workflows
- Extract SOPs and process knowledge from operations repositories
- Turn API docs and implementation notes into integration-oriented skills
- Build a reviewable bridge between messy source materials and AI-ready skill packages

## Product walkthrough

SkillForge is designed as a visual, local-first workflow.

### Visual workflow

1. **Create a job** — point SkillForge at a repository or document corpus
2. **Scan and parse** — discover candidate files and parse supported formats
3. **Extract evidence** — surface workflow-relevant excerpts and task signals
4. **Cluster capabilities** — group evidence into reusable capability areas
5. **Compile skills** — generate structured skill outputs for review
6. **Export to folder** — write the generated skill set to disk

### Built-in visualization

The web UI is not just a thin shell over APIs. It provides:

- a **dashboard** with recent jobs and pipeline coverage
- a **new job form** for repository selection and goal definition
- a **job detail page** with:
  - stage timeline
  - progress tracking
  - parsed documents view
  - evidence workbench
  - capability cluster preview
  - skill plan preview
  - generated skill preview
  - export and overwrite review flow
- **live status updates** via Server-Sent Events

## Screenshots

### 1. New job form

<img width="2549" height="1403" alt="d563512473a2539a1ae612f04205a6c9" src="https://github.com/user-attachments/assets/6cd4f4d4-3db1-4ca7-822d-002f839f8703" />

### 2. Job detail and pipeline visualization

<img width="2549" height="1403" alt="84b0e0ca60d3ed6d20cbdbedf9383290" src="https://github.com/user-attachments/assets/38d9705b-c05a-4fe0-8b34-28753be5df87" />

### 3. Exported skill folder output

<img width="654" height="1044" alt="image" src="https://github.com/user-attachments/assets/46ee1649-9319-4067-bd53-1da0b94b363f" />

## Quick Start

### Prerequisites

- Python 3.11+
- Windows, macOS, or Linux

### Install

From the repository root:

```bash
pip install -r requirements.txt
```

Or install the backend package directly:

```bash
cd backend
pip install -e .
```

### Start the app

From the repository root:

```bash
python start_skillforge.py
```

Then open:

```text
http://127.0.0.1:8000
```

The launcher will:

- verify that `backend/` exists
- create `backend/.env` from `backend/.env.example` if needed
- start the FastAPI app with auto reload

### First run

1. Open `http://127.0.0.1:8000/jobs/new`
2. Enter a job name
3. Choose a local repository or document corpus
4. Describe the goal you want SkillForge to extract
5. Run the pipeline
6. Review the generated evidence, capabilities, plans, and skills
7. Export the generated skills to a local folder

## Example output

A typical generated output looks like this:

```text
exports/
└── customer-onboarding-skill/
    ├── SKILL.md
    ├── references/
    │   ├── decision-table.md
    │   ├── examples.md
    │   └── source-map.md
    ├── scripts/
    │   └── analyze_inputs.py
    └── assets/
        └── template.txt
```
**It is normal for the skills generation to take a relatively long time due to the large number of files.**

This makes the result reviewable, portable, and easy to iterate on.

## Model Requirements

SkillForge can run locally **without configuring any external model API**.

Current default behavior is local-first:

- repository scanning works without external models
- document parsing works without external models
- evidence extraction, clustering, planning, and compilation currently have heuristic/local implementations
- the web UI and export flow work without an OpenAI key or any other hosted model

SkillForge also includes an **optional model API configuration UI** for OpenAI-compatible or related providers. That configuration is useful for connection testing and future/extended model-backed workflows, but it is **not required** for the default local experience.

Today, the built-in configuration supports provider-style settings for:

- OpenAI-compatible APIs
- Azure OpenAI-style endpoints
- Anthropic-compatible endpoints
- custom compatible endpoints

## Complete Tech Stack

### Application layer

- **Python 3.11+**
- **FastAPI** for API and server-side app delivery
- **Jinja2** for server-rendered UI
- **Uvicorn** as the ASGI server
- **Vanilla JavaScript** for client-side interactions
- **Server-Sent Events (SSE)** for live job updates
- **CSS** in `backend/app/static/style.css`

### Data and configuration

- **Pydantic v2** for schemas and validation
- **pydantic-settings** for environment-based configuration
- **orjson** for JSON handling
- **python-multipart** for form processing

### Persistence

- **Local-first default mode** with database persistence disabled
- **SQLite file** in `backend/data/skillforge.db` for local app data storage
- **SQLAlchemy 2** for ORM/repository integration
- **Alembic** for migrations
- **PostgreSQL + psycopg** as optional relational persistence

### Async execution

- **Celery** for optional background execution
- **Redis** as optional broker/result backend

### Document processing

- **python-docx** for `.docx`
- **pypdf** for `.pdf`
- **openpyxl** for `.xlsx`
- native Python handling for `.md` and `.txt`

### Optional AI backend integration

- configurable provider/base URL/API key/model settings
- connection testing from the settings page
- SSL, timeout, token, sampling, and streaming controls

## Architecture at a glance

Core modules live under `backend/app/`:

- `main.py` — app bootstrap and router registration
- `web.py` — server-rendered pages and form routes
- `api/routes/` — JSON API endpoints
- `services/jobs.py` — job orchestration
- `services/inventory.py` — repository scanning and candidate discovery
- `services/parsing.py` — document parsing
- `services/extraction.py` — evidence extraction
- `services/distillation.py` — capability clustering and skill planning
- `services/compiler.py` — skill compilation and validation
- `services/exporter.py` — export flow and overwrite review
- `services/model_client.py` — optional external model connectivity
- `tasks/` — Celery integration
- `templates/` — dashboard, job form, job detail, settings pages

## Repository structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/routes/
│   │   ├── core/
│   │   ├── db/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── static/
│   │   ├── tasks/
│   │   ├── templates/
│   │   ├── main.py
│   │   └── web.py
│   ├── alembic/
│   ├── data/
│   ├── exports/
│   ├── .env.example
│   ├── alembic.ini
│   └── pyproject.toml
├── requirements.txt
├── start_skillforge.py
├── start_skillforge.bat
└── README.md
```

## API overview

### Health

- `GET /health` — health and runtime mode

### Jobs API

- `GET /api/jobs`
- `POST /api/jobs`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/status`
- `GET /api/jobs/{job_id}/events`
- `POST /api/jobs/{job_id}/run`
- `POST /api/jobs/{job_id}/dispatch`
- `POST /api/jobs/{job_id}/retry`

### Settings API

- `GET /api/settings/model-api`
- `POST /api/settings/model-api`
- `POST /api/settings/model-api/test`

### Web UI routes

- dashboard at `http://127.0.0.1:8000/`
- new job page at `http://127.0.0.1:8000/jobs/new`
- job detail page at `http://127.0.0.1:8000/jobs/{job_id}`

## Configuration

Environment variables are loaded from `backend/.env` with the `SKILLFORGE_` prefix.

Example defaults:

```env
SKILLFORGE_CORS_ORIGINS=["http://localhost:3000"]
SKILLFORGE_DATABASE_URL=postgresql+psycopg://skillforge:skillforge@localhost:5432/skillforge
SKILLFORGE_REDIS_URL=redis://localhost:6379/0
SKILLFORGE_USE_ASYNC_PIPELINE=false
SKILLFORGE_USE_DATABASE_PERSISTENCE=false
```

Important runtime flags include:

- `SKILLFORGE_USE_ASYNC_PIPELINE`
- `SKILLFORGE_USE_DATABASE_PERSISTENCE`
- `SKILLFORGE_DATABASE_URL`
- `SKILLFORGE_REDIS_URL`
- model API related fields such as base URL, API key, model name, and timeout

## Testing

There is currently **no first-party automated test suite checked into this repository**.

At the moment, validation is mainly manual:

- start the app locally
- create a job from the web UI
- run the pipeline
- verify stage progress, preview output, and export behavior

If you add tests later, `pytest` would be a natural choice, but it is not yet wired up in this repository.

## Contributing

Contributions are welcome.

A lightweight contributor workflow for now:

1. fork the repository
2. create a feature branch
3. make focused changes
4. verify the UI/API flow locally
5. open a pull request with screenshots or reproduction notes when relevant

## Limitations

- extraction and clustering are still heuristic/local-first rather than fully model-driven
- scanned-image OCR is not included, so image-only PDFs are not fully supported
- very large repositories may require narrowing scope for practical review
- no committed automated test suite yet
- output quality still depends on source material quality and structure

## Roadmap

- stronger model-backed extraction and clustering options
- richer preview and traceability UX
- better large-repository scaling and filtering
- automated test coverage
- more polished export and packaging workflows

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE).
