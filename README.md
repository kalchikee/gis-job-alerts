# GIS Job Alert System

Automated daily digest of GIS job postings in **Florida**, **Texas**, and **North Carolina**, scored against a resume/portfolio and emailed every morning via GitHub Actions.

## How it works

```
GitHub Actions (7 AM Central daily)
  └── scraper.py   — Indeed RSS, USAJobs API, GISJobs.com, LinkedIn, GovernmentJobs
  └── scorer.py    — Scores each job 0–100 (skills, title, location, experience)
  └── emailer.py   — Sends HTML digest via Gmail SMTP
  └── seen_jobs.json updated and committed back to repo (deduplication)
```

## One-time setup

### 1. Gmail App Password
1. Enable 2FA at https://myaccount.google.com/security
2. Generate an App Password at https://myaccount.google.com/apppasswords
   - App: Mail → Other → "GIS Job Alerts"
3. Copy the 16-character password

### 2. USAJobs API Key (free)
1. Register at https://developer.usajobs.gov/APIRequest/Index
2. Check your email for the key

### 3. GitHub Repository
1. Create repo `gis-job-alerts` (private is fine)
2. Push this code to it
3. Go to **Settings → Secrets and variables → Actions** and add:

| Secret name | Value |
|---|---|
| `GMAIL_ADDRESS` | `kalchikethan@gmail.com` |
| `GMAIL_APP_PASSWORD` | 16-char app password |
| `RECIPIENT_EMAIL` | `kalchikethan@gmail.com` |
| `USAJOBS_API_KEY` | key from step 2 |
| `USAJOBS_EMAIL` | `kalchikethan@gmail.com` |

4. Go to **Settings → Actions → General** → Workflow permissions → select **"Read and write permissions"**

### 4. Test run
Go to **Actions → Daily GIS Job Alerts → Run workflow** to trigger manually before waiting for the cron.

## Local testing

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env from template
cp .env.example .env
# Fill in your values in .env

# Load env vars and run
export $(cat .env | xargs) && python src/main.py
```

## Scoring

| Factor | Max pts | Notes |
|---|---|---|
| Skill keywords | 40 | Weighted hits from config.py |
| Title match | 25 | Word-overlap vs target titles |
| Location | 15 | FL/TX/NC = 15, remote = 12, hybrid = 10 |
| Experience level | 10 | Entry/mid-level favored |
| Negative penalty | −10 | Senior/clearance required/etc. |

Jobs scoring **≥ 40** are included. Top **15** per email.

## Files

```
gis-job-alerts/
├── .github/workflows/daily_job_alert.yml
├── src/
│   ├── config.py    — keywords, weights, constants
│   ├── scraper.py   — multi-source job scraping
│   ├── scorer.py    — 0–100 resume-match scoring
│   ├── emailer.py   — HTML email builder + Gmail SMTP
│   └── main.py      — pipeline orchestrator
├── data/
│   └── seen_jobs.json
├── requirements.txt
└── .env.example
```
