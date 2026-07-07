# ─────────────────────────────────────────────────────────────────

"""
digest_sender.py — Sends a formatted HTML email digest of today's job evaluations.
Uses the Gmail API (same credentials as the reader).
"""

# ─────────────────────────────────────────────────────────────────

import base64
import os
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

YOUR_EMAIL = os.getenv('GMAIL_USER', '')


def build_digest_html(job_results: list, filtered_count: int = 0) -> str:
    """Build a clean HTML email from the list of evaluated jobs."""

    worth_applying = [r for r in job_results if r['evaluation'].get('is_worth_applying')]
    not_worth = [r for r in job_results if not r['evaluation'].get('is_worth_applying')]

    today = date.today().strftime('%B %d, %Y')

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 700px; margin: auto; padding: 20px; color: #1a1a1a;">

    <h2 style="margin-bottom: 4px;">🎯 Daily Job Match Digest — {today}</h2>
    <p style="color: #666; margin-top: 0;">
        <strong>{len(worth_applying)}</strong> roles worth applying to &nbsp;·&nbsp;
        <strong>{len(job_results)}</strong> evaluated &nbsp;·&nbsp;
        <strong>{filtered_count}</strong> filtered before evaluation
    </p>
    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 16px 0;">
    """

    # --- Worth applying ---
    for r in sorted(worth_applying,
                    key=lambda x: x['evaluation'].get('fit_score', 0), reverse=True):
        html += _job_card(r, highlight=True)

    # --- Not worth applying (collapsed summary) ---
    if not_worth:
        html += f"""
        <details style="margin-top: 24px;">
          <summary style="cursor:pointer; color:#666; font-size:14px;">
            {len(not_worth)} role(s) evaluated but not recommended — click to expand
          </summary>
          <div style="margin-top:12px;">
        """
        for r in not_worth:
            html += _job_card(r, highlight=False)
        html += "</div></details>"

    html += """
    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;">
    <p style="font-size:12px; color:#999;">Sent by your Job Alert Pipeline · Powered by Groq / Llama 3.3 70B</p>
    </body></html>
    """
    return html


def _job_card(r: dict, highlight: bool) -> str:
    """Render a single job card as HTML."""
    job = r['job']
    ev  = r['evaluation']

    score = ev.get('fit_score', 0)
    tier  = ev.get('fit_tier', '')
    priority = ev.get('application_priority', '')

    # Score colour
    if score >= 8:
        colour = '#16a34a'   # green
    elif score >= 6:
        colour = '#d97706'   # amber
    else:
        colour = '#dc2626'   # red

    border = f'3px solid {colour}' if highlight else '1px solid #e5e7eb'

    gaps_html = ''
    if ev.get('skill_gaps'):
        gaps_html = (
            '<p style="margin:6px 0;font-size:13px;">'
            f'<strong>⚠️ Gaps:</strong> {", ".join(ev["skill_gaps"])}</p>'
        )

    updates_html = ''
    updates = ev.get('resume_updates_needed', [])
    if updates and highlight:
        items = ''.join(
            f'<li><em>{u.get("section","")}</em>: {u.get("suggestion","")}</li>'
            for u in updates
        )
        updates_html = (
            f'<p style="margin:6px 0;font-size:13px;"><strong>📝 Resume tweaks:</strong></p>'
            f'<ul style="margin:4px 0 0 16px;font-size:13px;">{items}</ul>'
        )

    return f"""
    <div style="border-left:{border}; padding:12px 16px; margin:12px 0;
                background:{'#f9fafb' if highlight else '#fff'}; border-radius:4px;">
      <div style="display:flex; justify-content:space-between; align-items:flex-start;">
        <div>
          <strong style="font-size:15px;">{job.get('title','')}</strong>
          <span style="color:#666; font-size:13px;"> @ {job.get('company','')}</span>
          <span style="color:#999; font-size:12px; margin-left:8px;">{job.get('location','')}</span>
        </div>
        <span style="background:{colour}; color:white; padding:2px 8px; border-radius:12px;
                     font-size:13px; font-weight:bold; white-space:nowrap; margin-left:8px;">
          {score}/10
        </span>
      </div>

      <p style="margin:8px 0 4px 0; font-size:13px; color:#444;">
        <strong>{tier}</strong> &nbsp;·&nbsp; {priority}
      </p>

      <p style="margin:4px 0; font-size:13px;">{ev.get('fit_summary','')}</p>

      {'<p style="margin:6px 0;font-size:13px;"><strong>✅ Strengths:</strong> ' +
        ', '.join(ev.get('matching_strengths',[])) + '</p>' if ev.get('matching_strengths') else ''}

      {gaps_html}
      {updates_html}

      {'<p style="margin:6px 0;font-size:13px;"><strong>💡 Approach:</strong> ' +
        ev.get('recommended_approach','') + '</p>' if ev.get('recommended_approach') else ''}

      <p style="margin:8px 0 0 0;">
        <a href="{job.get('job_url','#')}" style="font-size:13px; color:#2563eb;">View Job →</a>
      </p>
    </div>
    """


def send_digest(service, html: str, retries: int = 3):
    """Send the HTML digest email to yourself via the Gmail API.
    Retries up to 3 times on transient SSL/network errors."""
    import time as _time
 
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"🎯 Job Digest — {date.today().strftime('%b %d')}"
    msg['From']    = YOUR_EMAIL
    msg['To']      = YOUR_EMAIL
    msg.attach(MIMEText(html, 'html'))
 
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
 
    for attempt in range(1, retries + 1):
        try:
            service.users().messages().send(
                userId='me', body={'raw': raw}
            ).execute()
            print(f'   ✅ Digest sent to {YOUR_EMAIL}')
            return
        except Exception as e:
            print(f'   ⚠️  Send attempt {attempt}/{retries} failed: {e}')
            if attempt < retries:
                _time.sleep(10)
 
    print('   ❌ All send attempts failed — digest not delivered but pipeline completed.')
