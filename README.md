# Pulsevo Tasks Backend

FastAPI backend powered by Neon (Postgres) with the required task columns:

`team_name`, `member_name`, `task_id`, `task_title`, `task_type`, `priority`, `status`, `created_at`, `closed_at`, `last_updated`, `source_tool`, `cycle_time`.

## Prerequisites

1. Create a Neon database and copy its **postgresql+asyncpg** connection string, e.g.
   ```
   DATABASE_URL=postgresql+asyncpg://user:password@ep-silent-123456.us-east-2.aws.neon.tech/neondb
   ```
2. Create a virtual environment and install dependencies:
   ```powershell
   cd Backend
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
3. Export/define `DATABASE_URL` (PowerShell):
   ```powershell
   $env:DATABASE_URL = "postgresql+asyncpg://..."
   ```
4. (Optional for the AI agent) set your OpenAI key/model:
   ```powershell
   $env:OPENAI_API_KEY = "sk-..."
   # optional override
   $env:OPENAI_MODEL = "gpt-4o-mini"
   ```

## Load the CSV into Neon

The repository includes `team_productivity_metrics.csv` at the repo root. Use the helper script to push it into Neon:

```powershell
cd Backend
python scripts/ingest_csv.py  # optional: --csv path\to\file.csv
```

The script auto-creates the `tasks` table (if needed) and performs an upsert so you can re-run it safely whenever the CSV changes.

## Run the API

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive docs: `http://localhost:8000/docs`

## Project Layout

- `app/main.py` - FastAPI bootstrap, CORS, startup migrations, and router registration.
- `app/config.py` - Pydantic settings (loads `DATABASE_URL`).
- `app/database.py` - Async engine/session factory for Neon.
- `app/db_models.py` - SQLAlchemy ORM definitions.
- `app/models.py` - Pydantic schemas/enums for request/response validation.
- `app/repository.py` - Async CRUD helpers used by task routes.
- `app/routers/tasks.py` - CRUD API (`/tasks`).
- `app/routers/analytics.py` - KPI/insights API for the single-page dashboard.
- `scripts/ingest_csv.py` - CSV to Neon ingestion utility.

## API Surface

- `GET /health` - readiness check.
- `GET /tasks` - list tasks (filters: `status`, `team_name`, `member_name`, `priority`, `task_type`, `source_tool`).
- `POST /tasks` - create a task (auto-generates `task_id` if omitted).
- `GET /tasks/{task_id}` - fetch one task.
- `PATCH /tasks/{task_id}` - partial update (auto-manages `last_updated`/`closed_at`).
- `DELETE /tasks/{task_id}` - remove a task.
- `GET /analytics/dashboard` - returns:
  - KPI cards (`open_tasks`, `in_progress`, `closed_today`, `closed_this_hour`, `completion_rate`)
  - Task distribution percentages for pie charts
  - 7-day trend arrays for `tasks_created`, `tasks_completed`, `tasks_in_progress`
  - Team performance blocks (`completed`, `in_progress`, `open`)
- `GET /analytics/task-management` - per-member stats with `name`, `total_assigned`, `ongoing`, `completed`, `trend_percent` (completion rate).
- `POST /ai/query` - accepts `{"question": "<natural language>"}` and returns the generated SQL plus result rows (requires `OPENAI_API_KEY`).

Plug your UI straight into `/analytics/dashboard` for the overview page and use the CRUD routes for drill-down views.
