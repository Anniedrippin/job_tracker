import smtplib
from email.mime.text import MIMEText
from typing import Optional

from celery.schedules import crontab

from sqlalchemy.orm import Session

from app.db.models import Application, ApplicationStatus, Job, User
from app.db.session import SessionLocal
from app.tasks.celery_app import celery_app
from app.core.config import settings


def _smtp_enabled() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD and settings.SMTP_FROM)


def _send_email(to_email: str, subject: str, body: str) -> None:
    if not _smtp_enabled():
        return

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)


def _daily_reminder_body(user: User) -> str:
    return (
        "Hi!\n\n"
        "Quick reminder to follow up on jobs you marked as applied.\n\n"
        "Open your dashboard to update statuses.\n\n"
        "- Smart Job Tracker"
    )


def _weekly_summary_body(user: User, total: int, interviews: int, rejections: int) -> str:
    rejection_rate = (rejections / total) if total else 0.0
    return (
        f"Weekly summary for {user.username or user.email}\n\n"
        f"Total applied: {total}\n"
        f"Interviews: {interviews}\n"
        f"Rejections: {rejections}\n"
        f"Rejection rate: {rejection_rate:.2%}\n\n"
        "- Smart Job Tracker"
    )


@celery_app.task(name="app.tasks.reminders.send_daily_reminders", bind=True, ignore_result=True)
def send_daily_reminders(self) -> None:
    db: Session = SessionLocal()
    try:
        if not _smtp_enabled():
            return

        # Simple heuristic: notify users with at least one "applied" application.
        users = db.query(User).join(Application).filter(Application.status == ApplicationStatus.applied).distinct().all()
        for user in users:
            body = _daily_reminder_body(user)
            _send_email(user.email, "Daily job follow-up reminder", body)
    finally:
        db.close()


@celery_app.task(name="app.tasks.reminders.send_weekly_summaries", bind=True, ignore_result=True)
def send_weekly_summaries(self) -> None:
    db: Session = SessionLocal()
    try:
        if not _smtp_enabled():
            return

        users = db.query(User).all()
        for user in users:
            total = db.query(Application).filter(Application.user_id == user.id).count()
            interviews = db.query(Application).filter(Application.user_id == user.id, Application.status == ApplicationStatus.interview).count()
            rejections = db.query(Application).filter(Application.user_id == user.id, Application.status == ApplicationStatus.rejected).count()
            body = _weekly_summary_body(user, total, interviews, rejections)
            _send_email(user.email, "Weekly Smart Job Tracker summary", body)
    finally:
        db.close()


# Beat schedule helper (Celery Beat can read this in `celery_app.conf.beat_schedule`)
celery_app.conf.beat_schedule = {
    "send-daily-reminders": {
        "task": "app.tasks.reminders.send_daily_reminders",
        "schedule": crontab(hour=9, minute=0),
    },
    "send-weekly-summaries": {
        "task": "app.tasks.reminders.send_weekly_summaries",
        "schedule": crontab(day_of_week="mon", hour=9, minute=0),
    },
}

