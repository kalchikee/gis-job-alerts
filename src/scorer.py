"""
Score each job 0–100 against Ethan Kalchik's resume/profile.

Scoring breakdown:
  40pts — Skill keyword match (weighted hits in title + description)
  25pts — Job title similarity match
  15pts — Location match (FL/TX/NC/remote)
  10pts — Experience level appropriateness
  10pts — Negative keyword penalty (subtracted)
"""

import logging
import re

from config import (
    HIGH_VALUE_KEYWORDS,
    MAX_RESULTS_PER_EMAIL,
    MIN_SCORE_TO_INCLUDE,
    NEGATIVE_KEYWORDS,
    STATE_ABBREVIATIONS,
    TARGET_JOB_TITLES,
    TARGET_STATES,
)

logger = logging.getLogger(__name__)


def _normalize(text: str) -> str:
    return text.lower().strip()


# ---------------------------------------------------------------------------
# Skill match  (0–40 pts)
# ---------------------------------------------------------------------------

# Maximum possible raw keyword score used for normalization
_MAX_RAW_KEYWORD_SCORE = sum(v * 2 for v in HIGH_VALUE_KEYWORDS.values())


def score_skills(title: str, description: str) -> tuple[float, list[str]]:
    """Return (score 0–40, list of matched skill labels)."""
    corpus = _normalize(f"{title} {description}")
    raw = 0
    matched: list[str] = []

    for keyword, weight in HIGH_VALUE_KEYWORDS.items():
        if keyword.lower() in corpus:
            raw += weight
            matched.append(keyword)

    # Normalize to 0–40 range; cap at 40
    normalized = min(40, (raw / max(_MAX_RAW_KEYWORD_SCORE, 1)) * 40 * 4)
    return round(normalized, 1), matched


# ---------------------------------------------------------------------------
# Title match  (0–25 pts)
# ---------------------------------------------------------------------------

def _title_similarity(a: str, b: str) -> float:
    """Simple word-overlap Jaccard similarity."""
    words_a = set(re.findall(r"\w+", a.lower()))
    words_b = set(re.findall(r"\w+", b.lower()))
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def score_title(job_title: str) -> float:
    """Return score 0–25 based on best match against TARGET_JOB_TITLES."""
    best = max(_title_similarity(job_title, t) for t in TARGET_JOB_TITLES)
    return round(best * 25, 1)


# ---------------------------------------------------------------------------
# Location match  (0–15 pts)
# ---------------------------------------------------------------------------

def score_location(location: str) -> float:
    loc_lower = _normalize(location)

    # Check full state names
    for state in TARGET_STATES:
        if state.lower() in loc_lower:
            return 15.0

    # Check abbreviations (e.g. ", FL" or " TX " or "NC,")
    for abbr in STATE_ABBREVIATIONS:
        pattern = r"\b" + abbr.lower() + r"\b"
        if re.search(pattern, loc_lower):
            return 15.0

    # Remote / hybrid
    if "remote" in loc_lower:
        return 12.0
    if "hybrid" in loc_lower:
        return 10.0

    return 0.0


# ---------------------------------------------------------------------------
# Experience level  (0–10 pts)
# ---------------------------------------------------------------------------

_EXP_PATTERNS = [
    (r"\b(entry.?level|new grad|recent grad|0.?2 years?|1.?2 years?)\b", 10),
    (r"\b(0.?3 years?|1.?3 years?|2.?3 years?)\b", 10),
    (r"\b(0.?5 years?|1.?5 years?|2.?5 years?|3.?5 years?|mid.?level)\b", 10),
    (r"\b(5.?7 years?)\b", 5),
    (r"\b([6-9]\+? years?|1[0-9]\+? years?)\b", 0),
    (r"\b(7\+? years?|8\+? years?|9\+? years?)\b", 0),
]


def score_experience(description: str) -> float:
    text = _normalize(description)
    for pattern, pts in _EXP_PATTERNS:
        if re.search(pattern, text):
            return float(pts)
    # No explicit experience requirement found — assume entry/mid level
    return 8.0


# ---------------------------------------------------------------------------
# Negative keyword penalty  (0–10 pts subtracted)
# ---------------------------------------------------------------------------

def score_penalty(title: str, description: str) -> float:
    corpus = _normalize(f"{title} {description}")
    hits = sum(1 for kw in NEGATIVE_KEYWORDS if kw.lower() in corpus)
    return min(10.0, hits * 3.0)


# ---------------------------------------------------------------------------
# Combined scorer
# ---------------------------------------------------------------------------

def score_job(job: dict) -> dict:
    """
    Add score fields to a job dict and return it.
    Modifies the dict in place and also returns it.
    """
    title = job.get("title", "")
    desc = job.get("description", "")
    location = job.get("location", "")

    skill_score, matched_skills = score_skills(title, desc)
    title_score = score_title(title)
    location_score = score_location(location)
    exp_score = score_experience(desc)
    penalty = score_penalty(title, desc)

    total = skill_score + title_score + location_score + exp_score - penalty
    total = max(0.0, min(100.0, total))

    job["score"] = round(total, 1)
    job["matched_skills"] = matched_skills[:10]  # top 10 for display
    job["score_breakdown"] = {
        "skills": skill_score,
        "title": title_score,
        "location": location_score,
        "experience": exp_score,
        "penalty": -penalty,
    }
    return job


def rank_jobs(jobs: list[dict]) -> list[dict]:
    """
    Score all jobs, filter by MIN_SCORE_TO_INCLUDE, sort descending.
    Returns top MAX_RESULTS_PER_EMAIL results.
    """
    scored = [score_job(job) for job in jobs]
    filtered = [j for j in scored if j["score"] >= MIN_SCORE_TO_INCLUDE]
    filtered.sort(key=lambda j: j["score"], reverse=True)

    logger.info(
        "Scoring: %d total → %d above threshold (%d) → returning top %d",
        len(scored),
        len(filtered),
        MIN_SCORE_TO_INCLUDE,
        MAX_RESULTS_PER_EMAIL,
    )
    return filtered[:MAX_RESULTS_PER_EMAIL]
