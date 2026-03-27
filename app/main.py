from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.db.models import Base
from app.db.session import engine


def _parse_cors_origins(value: str) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


app = FastAPI(title="Smart Job Tracker", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def on_startup() -> None:
    # For initial scaffold/dev: create tables automatically.
    # For production, switch to Alembic migrations.
    Base.metadata.create_all(bind=engine)

