"""
Format and send the daily GIS job digest via Gmail SMTP.
Uses inline CSS throughout — email clients strip <style> tags.
"""

import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import EMAIL_SUBJECT_PREFIX

logger = logging.getLogger(__name__)


def _score_color(score: float) -> str:
    if score >= 80:
        return "#2e7d32"   # green
    if score >= 60:
        return "#f57f17"   # amber
    return "#e65100"       # orange


def _score_bg(score: float) -> str:
    if score >= 80:
        return "#e8f5e9"
    if score >= 60:
        return "#fff8e1"
    return "#fbe9e7"


def _skill_tags_html(skills: list[str]) -> str:
    if not skills:
        return ""
    tags = "".join(
        f'<span style="display:inline-block;background:#e3f2fd;color:#1565c0;'
        f'border-radius:12px;padding:2px 10px;margin:2px 3px 2px 0;font-size:12px;'
        f'font-family:Arial,sans-serif;">{s}</span>'
        for s in skills
    )
    return tags


def _job_card_html(job: dict, rank: int) -> str:
    score = job.get("score", 0)
    color = _score_color(score)
    bg = _score_bg(score)
    skills_html = _skill_tags_html(job.get("matched_skills", []))
    source = job.get("source", "")
    location = job.get("location", "")
    company = job.get("company", "")
    url = job.get("url", "#")
    title = job.get("title", "Untitled")

    company_loc = " &bull; ".join(filter(None, [company, location]))

    return f"""
<tr>
  <td style="padding:0 0 16px 0;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0"
           style="border:1px solid #e0e0e0;border-radius:8px;overflow:hidden;
                  font-family:Arial,Helvetica,sans-serif;background:#ffffff;">
      <tr>
        <td style="padding:16px 20px 14px 20px;">

          <!-- rank + score badge row -->
          <table width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr>
              <td style="vertical-align:middle;">
                <span style="color:#9e9e9e;font-size:12px;">#{rank}</span>
              </td>
              <td align="right" style="vertical-align:middle;">
                <span style="background:{bg};color:{color};border-radius:20px;
                             padding:3px 12px;font-size:13px;font-weight:bold;
                             font-family:Arial,sans-serif;">
                  {score:.0f} / 100
                </span>
              </td>
            </tr>
          </table>

          <!-- job title -->
          <h3 style="margin:8px 0 4px 0;font-size:17px;font-weight:bold;color:#212121;">
            <a href="{url}" style="color:#1a73e8;text-decoration:none;">{title}</a>
          </h3>

          <!-- company + location -->
          <p style="margin:0 0 10px 0;font-size:13px;color:#616161;">
            {company_loc}
          </p>

          <!-- skill tags -->
          <div style="margin:0 0 10px 0;">{skills_html}</div>

          <!-- source + apply link -->
          <table width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr>
              <td style="vertical-align:middle;">
                <span style="font-size:11px;color:#9e9e9e;font-style:italic;">via {source}</span>
              </td>
              <td align="right" style="vertical-align:middle;">
                <a href="{url}"
                   style="background:#1a73e8;color:#ffffff;text-decoration:none;
                          border-radius:4px;padding:6px 14px;font-size:13px;
                          font-family:Arial,sans-serif;">
                  View Job &rarr;
                </a>
              </td>
            </tr>
          </table>

        </td>
      </tr>
    </table>
  </td>
</tr>
"""


def build_html(jobs: list[dict], date_str: str) -> str:
    count = len(jobs)
    cards = "".join(_job_card_html(j, i + 1) for i, j in enumerate(jobs))

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,Helvetica,sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f5f5f5;">
<tr><td align="center" style="padding:24px 16px;">

  <!-- Outer container -->
  <table width="600" cellpadding="0" cellspacing="0" border="0"
         style="max-width:600px;width:100%;">

    <!-- Header -->
    <tr>
      <td style="background:#1a73e8;border-radius:8px 8px 0 0;padding:28px 28px 24px 28px;">
        <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:bold;">
          GIS Job Alert
        </h1>
        <p style="margin:6px 0 0 0;color:#bbdefb;font-size:14px;">
          {date_str} &mdash; {count} new match{"es" if count != 1 else ""} in FL &bull; TX &bull; NC
        </p>
      </td>
    </tr>

    <!-- Body -->
    <tr>
      <td style="background:#fafafa;padding:20px 20px 4px 20px;border:1px solid #e0e0e0;
                 border-top:none;">

        {'<p style="margin:0 0 20px 0;color:#757575;font-size:13px;">No jobs scored above the threshold today. Check back tomorrow!</p>' if not jobs else ''}

        <table width="100%" cellpadding="0" cellspacing="0" border="0">
          {cards}
        </table>

      </td>
    </tr>

    <!-- Footer -->
    <tr>
      <td style="background:#eeeeee;border-radius:0 0 8px 8px;border:1px solid #e0e0e0;
                 border-top:none;padding:14px 20px;text-align:center;">
        <p style="margin:0;font-size:11px;color:#9e9e9e;">
          GIS Job Alert System &mdash; Florida &bull; Texas &bull; North Carolina
          &bull; Remote
        </p>
        <p style="margin:4px 0 0 0;font-size:11px;color:#9e9e9e;">
          Matched against Ethan Kalchik's skills &amp; experience.
          Scores &ge;40 shown, ranked highest first.
        </p>
      </td>
    </tr>

  </table>
</td></tr>
</table>

</body>
</html>"""


def build_plain_text(jobs: list[dict], date_str: str) -> str:
    lines = [f"GIS Job Alert — {date_str}", f"{len(jobs)} new matches\n", "=" * 60]
    for i, job in enumerate(jobs, 1):
        lines.append(
            f"\n#{i}  [{job.get('score', 0):.0f}/100]  {job.get('title', '')}"
        )
        lines.append(f"    {job.get('company', '')} — {job.get('location', '')}")
        lines.append(f"    Source: {job.get('source', '')}")
        if job.get("matched_skills"):
            lines.append(f"    Skills: {', '.join(job['matched_skills'])}")
        lines.append(f"    {job.get('url', '')}")
    lines.append("\n" + "=" * 60)
    lines.append("Powered by your GIS Job Alert System")
    return "\n".join(lines)


def send_digest(
    jobs: list[dict],
    sender_email: str,
    sender_password: str,
    recipient_email: str,
) -> bool:
    """
    Build and send the HTML digest.
    Returns True on success, False on failure.
    """
    date_str = datetime.now().strftime("%A, %B %-d, %Y")
    count = len(jobs)
    subject = f"{EMAIL_SUBJECT_PREFIX}: {count} new match{'es' if count != 1 else ''} — {date_str}"

    html_body = build_html(jobs, date_str)
    plain_body = build_plain_text(jobs, date_str)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        logger.info("Email sent to %s (%d jobs)", recipient_email, count)
        return True
    except Exception as e:
        logger.error("Failed to send email: %s", e)
        return False
