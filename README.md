# Smart Job Tracker (FastAPI + PostgreSQL + Celery + Redis)

End-to-end workflow:
1. Signup/Login -> JWT access token
2. Add job manually or by URL (background scraping)
3. Apply to job -> track application status
4. Update status -> timestamps
5. Analytics dashboard -> aggregated stats
6. Automation layer -> daily reminders + weekly summary email (SMTP)

## Tech Stack
- FastAPI (API)
- PostgreSQL (storage)
- SQLAlchemy (ORM)
- Passlib bcrypt (password hashing)
- JWT (python-jose)
- Celery + Redis (background jobs + queue)
- BeautifulSoup/lxml (basic HTML scraping)

## Local Setup (no Docker)
1. Create and activate a virtual environment
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Copy env file:
   - Create `.env` from `.env.example` and update values.
4. Run the API:
   - `uvicorn app.main:app --reload --port 8000`
5. Run the Celery worker (same terminal or another):
   - `celery -A app.tasks.celery_app.celery_app worker -B --loglevel=info`

## Docker Compose
1. Copy `.env` from `.env.example` and update values.
2. Run:
   - `docker compose up --build`

## API Endpoints (prefix: `/api`)
### Auth
- `POST /auth/signup` -> `{ "access_token": "..." }`
- `POST /auth/login`
- `GET /users/me`

### Jobs
- `POST /jobs/manual` body `{ "title": "...", "company": "...", "location": "..." }`
- `POST /jobs/by-url` body `{ "url": "https://..." }` (enqueues scraper)
- `POST /jobs/ingest` (Chrome extension phase 2) body:
  - `{ "url": "optional", "title": "...", "company": "...", "location": "...", "description": "..." }`
- `GET /jobs`
- `GET /jobs/{job_id}`

### Applications
- `POST /jobs/{job_id}/apply` body `{ "status": "applied|interview|rejected|offer" }`
- `PATCH /applications/{application_id}` body `{ "status": "..." }`
- `GET /applications`

### Analytics
- `GET /analytics/dashboard`
  - returns total applied, interviews, offers, rejections, rejection rate

## Scraping Notes
- The scraper uses a best-effort extraction strategy (OpenGraph meta tags + JSON-LD).
- Sources like LinkedIn/Indeed often block bots or require auth. You may need to adapt `app/tasks/scrape_job.py` per source.

## Next Steps (Phase 2+)
- Improve scraping per provider (LinkedIn/Indeed) using Playwright.
- Add caching (Redis cache-hit) for dashboard/jobs lists.
- Add frontend + Chrome extension UI.
- Switch to Alembic migrations instead of `Base.metadata.create_all()`.

