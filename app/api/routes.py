from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import (
    Application,
    ApplicationStatus,
    Job,
    JobScrapeStatus,
    User,
)
from app.schemas import (
    ApplicationCreate,
    ApplicationInDB,
    ApplicationUpdate,
    AnalyticsDashboard,
    JobByUrlCreate,
    JobInDB,
    JobIngestFromExtension,
    JobManualCreate,
    UserCreate,
    UserLogin,
    UserRead,
    TokenResponse,
)
from app.tasks.scrape_job import scrape_job, scrape_job_now
from app.utils.redis_health import is_redis_available
from app.utils.cache import get_json_cache, set_json_cache
from uuid import UUID


router = APIRouter(prefix="/api")


def _require_owner(db: Session, user: User, job_id: UUID) -> Job:
    job = db.query(Job).filter(Job.id == job_id, Job.owner_user_id == user.id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.post("/auth/signup", response_model=TokenResponse)
def signup(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        email=payload.email,
        username=payload.username,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token)


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token)


@router.get("/users/me", response_model=UserRead)
def me(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return user


@router.post("/jobs/manual", response_model=JobInDB)
def create_manual_job(
    payload: JobManualCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = Job(
        owner_user_id=user.id,
        title=payload.title,
        company=payload.company,
        location=payload.location,
        scrape_status=JobScrapeStatus.scraped,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.post("/jobs/by-url", response_model=JobInDB)
def create_job_by_url(
    payload: JobByUrlCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    url = payload.url.strip()

    existing = db.query(Job).filter(Job.owner_user_id == user.id, Job.url == url).first()
    if existing:
        # If we've never successfully scraped (or previously failed), retry.
        if existing.scrape_status != JobScrapeStatus.scraped:
            existing.scrape_status = JobScrapeStatus.queued
            existing.scrape_error = None
            db.commit()
            db.refresh(existing)

            if is_redis_available(settings.CELERY_BROKER_URL):
                scrape_job.delay(str(existing.id))
            else:
                scrape_job_now(str(existing.id))
                existing = db.query(Job).filter(Job.id == existing.id).first()
        return existing

    job = Job(owner_user_id=user.id, url=url, scrape_status=JobScrapeStatus.queued)
    db.add(job)
    db.commit()
    db.refresh(job)

    # Enqueue scraping (preferred), but fall back to synchronous scraping
    # when Redis isn't reachable (common local-dev setup).
    if is_redis_available(settings.CELERY_BROKER_URL):
        scrape_job.delay(str(job.id))
    else:
        scrape_job_now(str(job.id))
        job = db.query(Job).filter(Job.id == job.id).first()
    return job


@router.post("/jobs/ingest", response_model=JobInDB)
def ingest_job_from_extension(
    payload: JobIngestFromExtension,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    url = payload.url.strip() if payload.url else None

    existing = None
    if url:
        existing = db.query(Job).filter(Job.owner_user_id == user.id, Job.url == url).first()

    if existing:
        existing.title = payload.title
        existing.company = payload.company
        existing.location = payload.location
        existing.description = payload.description
        existing.scrape_status = JobScrapeStatus.scraped
        db.commit()
        db.refresh(existing)
        return existing

    job = Job(
        owner_user_id=user.id,
        url=url,
        title=payload.title,
        company=payload.company,
        location=payload.location,
        description=payload.description,
        scrape_status=JobScrapeStatus.scraped,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/jobs", response_model=List[JobInDB])
def list_jobs(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return (
        db.query(Job)
        .filter(Job.owner_user_id == user.id)
        .order_by(Job.updated_at.desc())
        .all()
    )


@router.get("/jobs/{job_id}", response_model=JobInDB)
def get_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = _require_owner(db, user, job_id)
    return job


@router.post("/jobs/{job_id}/apply", response_model=ApplicationInDB)
def apply_to_job(
    job_id: UUID,
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = _require_owner(db, user, job_id)

    status_value = ApplicationStatus(payload.status.value)

    existing = db.query(Application).filter(Application.user_id == user.id, Application.job_id == job.id).first()
    if existing:
        existing.status = status_value
        db.commit()
        db.refresh(existing)
        return existing

    app_row = Application(user_id=user.id, job_id=job.id, status=status_value)
    db.add(app_row)
    db.commit()
    db.refresh(app_row)
    return app_row


@router.patch("/applications/{application_id}", response_model=ApplicationInDB)
def update_application_status(
    application_id: UUID,
    payload: ApplicationUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    app_row = (
        db.query(Application)
        .filter(Application.id == application_id, Application.user_id == user.id)
        .first()
    )
    if not app_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    app_row.status = ApplicationStatus(payload.status.value)
    db.commit()
    db.refresh(app_row)
    return app_row


@router.get("/applications", response_model=List[ApplicationInDB])
def list_applications(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return (
        db.query(Application)
        .filter(Application.user_id == user.id)
        .order_by(Application.updated_at.desc())
        .all()
    )




@router.delete("/jobs/{job_id}")
def delete_job(job_id: UUID, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    db.delete(job)
    db.commit()

    return {"message": "Job deleted"}

@router.get("/analytics/dashboard", response_model=AnalyticsDashboard)
def dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cache_key = f"dashboard:{user.id}"
    cached = get_json_cache(cache_key)
    if cached:
        return AnalyticsDashboard(**cached)

    total = db.query(func.count(Application.id)).filter(Application.user_id == user.id).scalar() or 0
    interviews = (
        db.query(func.count(Application.id))
        .filter(Application.user_id == user.id, Application.status == ApplicationStatus.interview)
        .scalar()
        or 0
    )
    offers = (
        db.query(func.count(Application.id))
        .filter(Application.user_id == user.id, Application.status == ApplicationStatus.offer)
        .scalar()
        or 0
    )
    rejections = (
        db.query(func.count(Application.id))
        .filter(Application.user_id == user.id, Application.status == ApplicationStatus.rejected)
        .scalar()
        or 0
    )
    rejection_rate = (rejections / total) if total else 0.0

    result = AnalyticsDashboard(
        total_applied=total,
        interviews=interviews,
        offers=offers,
        rejections=rejections,
        rejection_rate=rejection_rate,
    )
    set_json_cache(cache_key, result.model_dump(), ttl_seconds=60)
    return result


