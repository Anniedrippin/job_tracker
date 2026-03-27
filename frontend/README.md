# Smart Job Tracker - React Frontend

## Prerequisites
You need Node.js + npm to install dependencies and run Vite.

## Setup
1. `cd frontend`
2. Copy env:
   - `.env.example` -> `.env`
3. Install:
   - `npm install`
4. Run dev server:
   - `npm run dev`

## Connects to Backend
Uses `VITE_API_BASE_URL` (default `http://localhost:8000`) and calls these endpoints:
- `POST /api/auth/signup`
- `POST /api/auth/login`
- `GET /api/users/me`
- `GET /api/jobs`
- `POST /api/jobs/manual`
- `POST /api/jobs/by-url`
- `POST /api/jobs/:job_id/apply`
- `PATCH /api/applications/:application_id`
- `GET /api/applications`
- `GET /api/analytics/dashboard`

