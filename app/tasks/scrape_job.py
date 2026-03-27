import json
import re
from typing import Dict, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.db.models import Job, JobScrapeStatus
from app.db.session import SessionLocal
from app.tasks.celery_app import celery_app


def _safe_strip(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _extract_from_meta(soup: BeautifulSoup) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    title = None
    company = None
    description = None

    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = og_title.get("content")

    # LinkedIn/Indeed often use og:site_name for publisher/company name, but it's not guaranteed.
    og_site = soup.find("meta", property="og:site_name")
    if og_site and og_site.get("content"):
        company = og_site.get("content")

    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        description = meta_desc.get("content")

    # Fallbacks
    if not title and soup.title and soup.title.text:
        title = soup.title.text

    return _safe_strip(title), _safe_strip(company), _safe_strip(description)


def _extract_from_json_ld(soup: BeautifulSoup) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    title = None
    company = None
    description = None
    location = None

    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string
        if not raw:
            continue
        raw = raw.strip()
        if not raw:
            continue

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue

        # Schema can be object or list.
        candidates = payload if isinstance(payload, list) else [payload]
        for c in candidates:
            if not isinstance(c, dict):
                continue

            # Common job posting fields
            t = c.get("title")
            hiring_org = c.get("hiringOrganization") or c.get("hiringOrg") or c.get("organization")
            if isinstance(hiring_org, dict):
                c_name = hiring_org.get("name")
            elif isinstance(hiring_org, str):
                c_name = hiring_org
            else:
                c_name = None
            d = c.get("description")
            job_loc = c.get("jobLocation") or c.get("jobloc")
            c_loc = None
            if isinstance(job_loc, dict):
                addr = job_loc.get("address")
                if isinstance(addr, dict):
                    locality = addr.get("addressLocality")
                    region = addr.get("addressRegion")
                    country = addr.get("addressCountry")
                    parts = [p for p in [locality, region, country] if isinstance(p, str) and p.strip()]
                    c_loc = ", ".join(parts) if parts else None
                else:
                    c_loc = job_loc.get("name")
            elif isinstance(job_loc, str):
                c_loc = job_loc

            title = title or (t if isinstance(t, str) else None)
            company = company or (c_name if isinstance(c_name, str) else None)
            description = description or (d if isinstance(d, str) else None)
            location = location or (c_loc if isinstance(c_loc, str) else None)

    # Basic cleanup if description is HTML-ish
    if description:
        description = re.sub(r"\s+", " ", description).strip()

    return _safe_strip(title), _safe_strip(company), _safe_strip(description), _safe_strip(location)


def _extract_job_details(html: str) -> Dict[str, Optional[str]]:
    # Prefer lxml when available; fall back to built-in parser otherwise.
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    title, company, description = _extract_from_meta(soup)
    location = None

    # Try JSON-LD even if meta extraction succeeded (location is often only there).
    t2, c2, d2, loc2 = _extract_from_json_ld(soup)
    title = title or t2
    company = company or c2
    description = description or d2
    location = loc2 or location

    return {
        "title": title,
        "company": company,
        "description": description,
        "location": location,
    }


def scrape_job_now(job_id: str) -> None:
    """
    Synchronous execution path for local dev / when Celery+Redis aren't reachable.
    Updates the job row in PostgreSQL with scrape results.
    """
    db: Session = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        job.scrape_status = JobScrapeStatus.scraping
        job.scrape_error = None
        db.commit()

        if not job.url:
            job.scrape_status = JobScrapeStatus.scrape_failed
            job.scrape_error = "Missing job URL"
            db.commit()
            return

        user_agent = "Mozilla/5.0 (compatible; SmartJobTracker/1.0; +https://example.com/bot)"
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        # Try simple requests first (fast). If blocked (e.g. Indeed 403), fall back to Playwright.
        html: str
        try:
            resp = requests.get(job.url, headers=headers, timeout=25)
            resp.raise_for_status()
            html = resp.text
        except requests.HTTPError as e:
            if getattr(resp, "status_code", None) == 403:
                html = _fetch_job_html_playwright(job.url, user_agent=user_agent)
            else:
                raise
        except requests.RequestException:
            html = _fetch_job_html_playwright(job.url, user_agent=user_agent)

        details = _extract_job_details(html)

        if not details.get("title") and not details.get("description"):
            job.scrape_status = JobScrapeStatus.scrape_failed
            job.scrape_error = "Could not extract title/description"
        else:
            job.title = details.get("title") or job.title
            job.company = details.get("company") or job.company
            job.description = details.get("description") or job.description
            job.location = details.get("location") or job.location
            job.scrape_status = JobScrapeStatus.scraped

        db.commit()
    except Exception as e:
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.scrape_status = JobScrapeStatus.scrape_failed
                job.scrape_error = str(e)[:2000]
                db.commit()
        finally:
            pass
        raise
    finally:
        db.close()


def _fetch_job_html_playwright(url: str, user_agent: str) -> str:
    """
    Fetch HTML using headless Chromium (helps bypass simple 403 blocks).
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise RuntimeError("Playwright is not installed; cannot fallback for blocked pages") from e

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=user_agent)
        page = context.new_page()

        # Speed up: abort heavy resources.
        def route_handler(route):
            try:
                if route.request.resource_type in ["image", "media", "font", "stylesheet"]:
                    route.abort()
                else:
                    route.continue_()
            except Exception:
                try:
                    route.abort()
                except Exception:
                    pass

        page.route("**/*", route_handler)

        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        # Many job pages expose meta tags; wait briefly but don't fail hard.
        try:
            page.wait_for_selector(
                "meta[property='og:title'], meta[property='og:site_name'], meta[name='description']",
                timeout=8000,
            )
        except Exception:
            pass

        html = page.content()
        browser.close()
        return html


@celery_app.task(name="app.tasks.scrape_job.scrape_job", bind=True, autoretry_for=(requests.RequestException,), retry_backoff=True, max_retries=3)
def scrape_job(self, job_id: str) -> None:
    try:
        scrape_job_now(job_id)
    except Exception:
        # Celery handles retries; keep the task contract.
        raise

