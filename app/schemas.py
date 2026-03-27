import enum
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    username: Optional[str] = Field(default=None, max_length=80)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    username: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class JobScrapeStatus(str, enum.Enum):
    queued = "queued"
    scraping = "scraping"
    scraped = "scraped"
    scrape_failed = "scrape_failed"


class JobManualCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    company: str = Field(min_length=1, max_length=200)
    location: Optional[str] = Field(default=None, max_length=200)


class JobByUrlCreate(BaseModel):
    url: str = Field(min_length=8, max_length=2000)


class JobIngestFromExtension(BaseModel):
    # Payload sent by the Chrome extension after extracting from a job page.
    # Note: fields are best-effort because different sources provide different DOM structures.
    url: Optional[str] = Field(default=None, min_length=8, max_length=2000)
    title: str = Field(min_length=1, max_length=300)
    company: Optional[str] = Field(default=None, max_length=200)
    location: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = None


class JobInDB(BaseModel):
    id: uuid.UUID
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    scrape_status: JobScrapeStatus
    scrape_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApplicationStatus(str, enum.Enum):
    applied = "applied"
    interview = "interview"
    rejected = "rejected"
    offer = "offer"


class ApplicationCreate(BaseModel):
    status: ApplicationStatus = ApplicationStatus.applied


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus


class ApplicationInDB(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    status: ApplicationStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AnalyticsDashboard(BaseModel):
    total_applied: int
    interviews: int
    offers: int
    rejections: int
    rejection_rate: float

