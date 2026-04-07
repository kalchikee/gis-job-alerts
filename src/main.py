"""
Orchestrator: scrape → deduplicate → score → email → persist cache
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from config import SEEN_JOBS_MAX_AGE_DAYS, SEEN_JOBS_PATH
from emailer import send_digest
from scorer import rank_jobs
from scraper import run_all_scrapers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main")


def load_seen_jobs(path: str) -> dict:
    """Load {job_id: iso_timestamp} from JSON file."""
    p = Path(path)
    if p.exists() and p.stat().st_size > 0:
        try:
            with p.open() as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Could not load seen_jobs.json: %s — starting fresh", e)
    return {}


def save_seen_jobs(path: str, seen: dict) -> None:
    """Persist seen jobs dict to JSON."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as f:
        json.dump(seen, f, indent=2)
    logger.info("Saved %d entries to %s", len(seen), path)


def prune_seen_jobs(seen: dict, max_age_days: int) -> dict:
    """Remove entries older than max_age_days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    pruned = {
        job_id: ts
        for job_id, ts in seen.items()
        if datetime.fromisoformat(ts.replace("Z", "+00:00")) > cutoff
    }
    removed = len(seen) - len(pruned)
    if removed:
        logger.info("Pruned %d stale entries from seen_jobs cache", removed)
    return pruned


def filter_new_jobs(jobs: list[dict], seen: dict) -> list[dict]:
    """Return only jobs not already in the seen cache."""
    new = [j for j in jobs if j["id"] not in seen]
    logger.info("New jobs after dedup: %d of %d", len(new), len(jobs))
    return new


def mark_seen(jobs: list[dict], seen: dict) -> dict:
    """Add all scraped job IDs to the seen dict (with current timestamp)."""
    now = datetime.now(timezone.utc).isoformat()
    for job in jobs:
        seen[job["id"]] = now
    return seen


def get_env(name: str, required: bool = True) -> str:
    value = os.environ.get(name, "").strip()
    if required and not value:
        logger.error("Missing required environment variable: %s", name)
        sys.exit(1)
    return value


def main() -> None:
    logger.info("=== GIS Job Alert Pipeline starting ===")

    # --- Config from environment ---
    gmail_address = get_env("GMAIL_ADDRESS")
    gmail_password = get_env("GMAIL_APP_PASSWORD")
    recipient = get_env("RECIPIENT_EMAIL")
    usajobs_key = get_env("USAJOBS_API_KEY", required=False)
    usajobs_email = get_env("USAJOBS_EMAIL", required=False)

    # --- Load cache ---
    seen = load_seen_jobs(SEEN_JOBS_PATH)
    seen = prune_seen_jobs(seen, SEEN_JOBS_MAX_AGE_DAYS)
    logger.info("Seen-jobs cache: %d entries after pruning", len(seen))

    # --- Scrape ---
    raw_jobs = run_all_scrapers(
        usajobs_api_key=usajobs_key,
        usajobs_email=usajobs_email,
    )

    # --- Deduplicate ---
    new_jobs = filter_new_jobs(raw_jobs, seen)

    # --- Score + rank ---
    if new_jobs:
        top_jobs = rank_jobs(new_jobs)
        logger.info("Top jobs to send: %d", len(top_jobs))
    else:
        top_jobs = []
        logger.info("No new jobs found today.")

    # --- Send email ---
    # Always send so you know the pipeline ran (even if 0 results)
    success = send_digest(
        jobs=top_jobs,
        sender_email=gmail_address,
        sender_password=gmail_password,
        recipient_email=recipient,
    )
    if not success:
        logger.error("Email delivery failed — cache will still be updated")

    # --- Update cache ---
    seen = mark_seen(raw_jobs, seen)  # mark everything scraped (not just top N)
    save_seen_jobs(SEEN_JOBS_PATH, seen)

    logger.info("=== Pipeline complete ===")


if __name__ == "__main__":
    main()
