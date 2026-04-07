"""
Job scraping logic for multiple sources.
Each scraper returns a list of job dicts:
  {title, company, location, url, description, date_posted, source}

Failures in any single source are caught and logged — the pipeline continues.
"""

import hashlib
import logging
import time
from datetime import datetime, timezone

import feedparser
import requests
from bs4 import BeautifulSoup

from config import STATE_ABBREVIATIONS, TARGET_STATES

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

REQUEST_DELAY = 2  # seconds between requests


def make_job_id(title: str, company: str, location: str) -> str:
    key = f"{title.lower().strip()}|{company.lower().strip()}|{location.lower().strip()}"
    return hashlib.md5(key.encode()).hexdigest()


def safe_get(url: str, **kwargs) -> requests.Response | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, **kwargs)
        resp.raise_for_status()
        return resp
    except Exception as e:
        logger.warning("GET %s failed: %s", url, e)
        return None


# ---------------------------------------------------------------------------
# Indeed RSS
# ---------------------------------------------------------------------------

INDEED_QUERIES = [
    "GIS+analyst",
    "GIS+specialist",
    "GIS+technician",
    "geospatial+analyst",
    "spatial+analyst",
    "remote+sensing+analyst",
    "GIS+developer",
    "cartographer",
]

INDEED_LOCATIONS = [
    ("Florida", "FL"),
    ("Texas", "TX"),
    ("North+Carolina", "NC"),
]


def scrape_indeed() -> list[dict]:
    jobs = []
    base = "https://www.indeed.com/rss"

    for query in INDEED_QUERIES:
        for state_name, state_abbr in INDEED_LOCATIONS:
            url = f"{base}?q={query}&l={state_name}&radius=100"
            logger.info("Indeed RSS: %s in %s", query, state_name)
            feed = feedparser.parse(url)

            for entry in feed.entries:
                title = entry.get("title", "").strip()
                # Indeed RSS title format: "Job Title - Company - City, ST"
                parts = [p.strip() for p in title.split(" - ")]
                job_title = parts[0] if parts else title
                company = parts[1] if len(parts) > 1 else "Unknown"
                location = parts[2] if len(parts) > 2 else state_name

                link = entry.get("link", "")
                summary = BeautifulSoup(entry.get("summary", ""), "html.parser").get_text()
                published = entry.get("published", datetime.now(timezone.utc).isoformat())

                job = {
                    "id": make_job_id(job_title, company, location),
                    "title": job_title,
                    "company": company,
                    "location": location,
                    "url": link,
                    "description": summary[:2000],
                    "date_posted": published,
                    "source": "Indeed",
                }
                jobs.append(job)

            time.sleep(REQUEST_DELAY)

    logger.info("Indeed: collected %d raw listings", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# USAJobs API  (free — requires User-Agent + email key in headers)
# ---------------------------------------------------------------------------


def scrape_usajobs(api_key: str, user_email: str) -> list[dict]:
    if not api_key or not user_email:
        logger.warning("USAJobs: missing API key or email — skipping")
        return []

    jobs = []
    base = "https://data.usajobs.gov/api/search"
    headers = {
        "Host": "data.usajobs.gov",
        "User-Agent": user_email,
        "Authorization-Key": api_key,
    }

    keywords = ["GIS", "geospatial", "spatial analyst", "cartographer", "remote sensing"]
    locations = ["Florida", "Texas", "North Carolina"]

    for keyword in keywords:
        for location in locations:
            params = {
                "Keyword": keyword,
                "LocationName": location,
                "ResultsPerPage": 25,
                "Fields": "Min",
            }
            logger.info("USAJobs: %s in %s", keyword, location)
            try:
                resp = requests.get(base, headers=headers, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.warning("USAJobs request failed: %s", e)
                time.sleep(REQUEST_DELAY)
                continue

            items = data.get("SearchResult", {}).get("SearchResultItems", [])
            for item in items:
                mv = item.get("MatchedObjectDescriptor", {})
                title = mv.get("PositionTitle", "")
                org = mv.get("OrganizationName", "")
                loc_list = mv.get("PositionLocation", [{}])
                loc = loc_list[0].get("LocationName", location) if loc_list else location
                url = mv.get("PositionURI", "")
                desc = mv.get("QualificationSummary", "")
                posted = mv.get("PublicationStartDate", datetime.now(timezone.utc).isoformat())

                job = {
                    "id": make_job_id(title, org, loc),
                    "title": title,
                    "company": org,
                    "location": loc,
                    "url": url,
                    "description": desc[:2000],
                    "date_posted": posted,
                    "source": "USAJobs",
                }
                jobs.append(job)

            time.sleep(REQUEST_DELAY)

    logger.info("USAJobs: collected %d raw listings", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# GISJobs.com
# ---------------------------------------------------------------------------


def scrape_gisjobs() -> list[dict]:
    jobs = []
    base_url = "https://www.gisjobs.com/classifiedads/"
    state_slugs = ["florida", "texas", "north-carolina"]

    for slug in state_slugs:
        url = f"{base_url}?state={slug}"
        logger.info("GISJobs: fetching %s", url)
        resp = safe_get(url)
        if not resp:
            time.sleep(REQUEST_DELAY)
            continue

        soup = BeautifulSoup(resp.text, "lxml")
        # GISJobs listings are in table rows or divs — parse generically
        listings = soup.find_all("div", class_=lambda c: c and "job" in c.lower())
        if not listings:
            # Fallback: look for any anchor with "job" in href
            listings = soup.find_all("a", href=lambda h: h and "/classifiedads/" in h)

        for item in listings:
            if isinstance(item, BeautifulSoup.__class__):
                continue
            try:
                link_tag = item.find("a") if item.name != "a" else item
                if not link_tag:
                    continue
                title = link_tag.get_text(strip=True)
                href = link_tag.get("href", "")
                if not href.startswith("http"):
                    href = "https://www.gisjobs.com" + href

                # Try to get company/location from surrounding text
                text = item.get_text(separator=" ", strip=True)
                job = {
                    "id": make_job_id(title, "", slug),
                    "title": title,
                    "company": "",
                    "location": slug.replace("-", " ").title(),
                    "url": href,
                    "description": text[:2000],
                    "date_posted": datetime.now(timezone.utc).isoformat(),
                    "source": "GISJobs.com",
                }
                if title and len(title) > 3:
                    jobs.append(job)
            except Exception as e:
                logger.debug("GISJobs parse error: %s", e)

        time.sleep(REQUEST_DELAY)

    logger.info("GISJobs.com: collected %d raw listings", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# LinkedIn Jobs (public RSS — limited but no auth needed)
# ---------------------------------------------------------------------------


def scrape_linkedin() -> list[dict]:
    jobs = []
    # LinkedIn public job search RSS (unofficial, may break)
    queries = ["GIS+analyst", "geospatial+analyst", "spatial+analyst", "GIS+technician"]
    locations = ["Florida", "Texas", "North+Carolina"]

    for query in queries:
        for location in locations:
            url = (
                f"https://www.linkedin.com/jobs/search/?keywords={query}"
                f"&location={location}&f_TPR=r86400&trk=public_jobs_jobs-search-bar_search-submit"
            )
            logger.info("LinkedIn: %s in %s", query, location)
            resp = safe_get(url)
            if not resp:
                time.sleep(REQUEST_DELAY)
                continue

            soup = BeautifulSoup(resp.text, "lxml")
            cards = soup.find_all("div", class_=lambda c: c and "job-search-card" in (c or ""))
            if not cards:
                cards = soup.find_all("li", class_=lambda c: c and "result-card" in (c or ""))

            for card in cards:
                try:
                    title_tag = card.find("h3") or card.find("h2")
                    company_tag = card.find("h4") or card.find(class_=lambda c: c and "company" in (c or ""))
                    location_tag = card.find(class_=lambda c: c and "location" in (c or ""))
                    link_tag = card.find("a", href=True)

                    title = title_tag.get_text(strip=True) if title_tag else ""
                    company = company_tag.get_text(strip=True) if company_tag else ""
                    loc = location_tag.get_text(strip=True) if location_tag else location.replace("+", " ")
                    href = link_tag["href"] if link_tag else ""

                    if not title:
                        continue

                    job = {
                        "id": make_job_id(title, company, loc),
                        "title": title,
                        "company": company,
                        "location": loc,
                        "url": href,
                        "description": card.get_text(separator=" ", strip=True)[:2000],
                        "date_posted": datetime.now(timezone.utc).isoformat(),
                        "source": "LinkedIn",
                    }
                    jobs.append(job)
                except Exception as e:
                    logger.debug("LinkedIn card parse error: %s", e)

            time.sleep(REQUEST_DELAY)

    logger.info("LinkedIn: collected %d raw listings", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# Government Jobs (state/local government GIS postings)
# ---------------------------------------------------------------------------


def scrape_governmentjobs() -> list[dict]:
    jobs = []
    # GovernmentJobs.com public search
    state_params = [
        ("Florida", "FL"),
        ("Texas", "TX"),
        ("North Carolina", "NC"),
    ]
    keywords = ["GIS", "Geographic Information", "geospatial", "spatial analyst"]

    for keyword in keywords:
        for state_name, state_abbr in state_params:
            url = (
                f"https://www.governmentjobs.com/jobs?keyword={keyword.replace(' ', '+')}"
                f"&location={state_name.replace(' ', '+')}&sort=PostingDate&order=Descending"
            )
            logger.info("GovernmentJobs: %s in %s", keyword, state_name)
            resp = safe_get(url)
            if not resp:
                time.sleep(REQUEST_DELAY)
                continue

            soup = BeautifulSoup(resp.text, "lxml")
            rows = soup.find_all("div", class_=lambda c: c and "job-title" in (c or ""))
            if not rows:
                rows = soup.find_all("li", class_=lambda c: c and "list-item" in (c or ""))

            for row in rows:
                try:
                    link_tag = row.find("a", href=True)
                    if not link_tag:
                        continue
                    title = link_tag.get_text(strip=True)
                    href = link_tag["href"]
                    if not href.startswith("http"):
                        href = "https://www.governmentjobs.com" + href

                    text = row.get_text(separator=" ", strip=True)
                    job = {
                        "id": make_job_id(title, "", state_name),
                        "title": title,
                        "company": state_name + " Government",
                        "location": state_name,
                        "url": href,
                        "description": text[:2000],
                        "date_posted": datetime.now(timezone.utc).isoformat(),
                        "source": "GovernmentJobs",
                    }
                    if title and len(title) > 3:
                        jobs.append(job)
                except Exception as e:
                    logger.debug("GovernmentJobs parse error: %s", e)

            time.sleep(REQUEST_DELAY)

    logger.info("GovernmentJobs: collected %d raw listings", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_all_scrapers(usajobs_api_key: str = "", usajobs_email: str = "") -> list[dict]:
    """
    Run all scrapers and return a deduplicated combined list.
    Individual source failures are caught — pipeline continues.
    """
    all_jobs: list[dict] = []

    sources = [
        ("Indeed", scrape_indeed, {}),
        ("USAJobs", scrape_usajobs, {"api_key": usajobs_api_key, "user_email": usajobs_email}),
        ("GISJobs.com", scrape_gisjobs, {}),
        ("LinkedIn", scrape_linkedin, {}),
        ("GovernmentJobs", scrape_governmentjobs, {}),
    ]

    for name, func, kwargs in sources:
        try:
            results = func(**kwargs)
            all_jobs.extend(results)
            logger.info("%s: %d jobs added (running total: %d)", name, len(results), len(all_jobs))
        except Exception as e:
            logger.error("Source '%s' failed entirely: %s", name, e)

    # Deduplicate by job ID (keep first occurrence)
    seen_ids: set[str] = set()
    unique_jobs: list[dict] = []
    for job in all_jobs:
        if job["id"] not in seen_ids:
            seen_ids.add(job["id"])
            unique_jobs.append(job)

    logger.info("Total unique jobs from all sources: %d", len(unique_jobs))
    return unique_jobs
